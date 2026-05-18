"""TaxKing AI — Local tax document organizer and helper."""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

import customtkinter as ctk

from storage import (
    load_tax_data, save_tax_data, store_document,
    add_document_entry, delete_document,
    add_manual_entry, remove_manual_entry, get_summary,
)
from parser import parse_document, extract_text_from_pdf, detect_form_type, check_ocr_status
from tax_tips import FORM_TIPS, GENERAL_TIPS, FORM_DISPLAY_NAMES
from config import load_config, save_config, is_plaid_configured
from plaid_integration import (
    create_link_token, exchange_public_token,
    get_accounts, get_transactions, start_plaid_link,
)
from email_scanner import (
    connect as imap_connect, scan_for_tax_emails,
    download_attachment, disconnect as imap_disconnect,
    guess_imap_server,
)
from tax_calculator import calculate_estimated_tax, PROVINCE_NAMES, PROVINCIAL_BRACKETS_2024
from deadlines import get_deadlines, format_deadline_text
from pdf_export import generate_cheat_sheet
from watch_folder import WatchFolder

# ── Theme ───────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COLORS = {
    "bg": "#1a1a2e",
    "card": "#16213e",
    "accent": "#0f3460",
    "highlight": "#e94560",
    "green": "#2ecc71",
    "yellow": "#f1c40f",
    "text": "#ffffff",
    "text_muted": "#a0a0b0",
    "income": "#2ecc71",
    "withheld": "#3498db",
    "deduction": "#e67e22",
    "warning": "#e74c3c",
}


class TaxKingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TaxKing AI — Tax Document Organizer")
        self.geometry("1100x750")
        self.minsize(900, 600)

        self.tax_data = load_tax_data()
        self._watch_folder = None

        self._build_ui()
        self.refresh_all()

        # Start watch folder if configured
        self.after(500, self._restart_watch_folder)

    # ── Layout ──────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color=COLORS["accent"])
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="TaxKing AI",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(side="left", padx=20)

        # Settings button
        settings_frame = ctk.CTkFrame(header, fg_color="transparent")
        settings_frame.pack(side="right", padx=20)

        # Tax year selector
        ctk.CTkLabel(settings_frame, text="Year:").pack(side="left", padx=(0, 4))
        current_year = datetime.now().year
        years = [str(y) for y in range(current_year, current_year - 5, -1)]
        self.year_var = ctk.StringVar(value=str(self.tax_data.get("tax_year", current_year - 1)))
        year_menu = ctk.CTkOptionMenu(
            settings_frame, values=years, variable=self.year_var,
            command=self._on_year_change, width=80,
        )
        year_menu.pack(side="left", padx=(0, 12))

        # Province selector
        config = load_config()
        ctk.CTkLabel(settings_frame, text="Province:").pack(side="left", padx=(0, 4))
        self.province_var = ctk.StringVar(value=config.get("province", "ON"))
        province_menu = ctk.CTkOptionMenu(
            settings_frame, values=list(PROVINCE_NAMES.keys()),
            variable=self.province_var, command=self._on_province_change, width=80,
        )
        province_menu.pack(side="left", padx=(0, 12))

        # Settings gear
        ctk.CTkButton(
            settings_frame, text="Settings", width=80,
            fg_color=COLORS["bg"], hover_color="#0a0a1f",
            command=self._show_app_settings,
        ).pack(side="left")

        # Tabs
        self.tabview = ctk.CTkTabview(self, corner_radius=8)
        self.tabview.pack(fill="both", expand=True, padx=12, pady=(8, 12))

        self.tab_dashboard = self.tabview.add("Dashboard")
        self.tab_documents = self.tabview.add("Documents")
        self.tab_email = self.tabview.add("Email Scanner")
        self.tab_bank = self.tabview.add("Bank Accounts")
        self.tab_manual = self.tabview.add("Manual Entry")
        self.tab_tips = self.tabview.add("Tax Tips")

        self._build_dashboard_tab()
        self._build_documents_tab()
        self._build_email_tab()
        self._build_bank_tab()
        self._build_manual_tab()
        self._build_tips_tab()

    # ── Dashboard Tab ───────────────────────────────────────────
    def _build_dashboard_tab(self):
        self.dashboard_frame = ctk.CTkScrollableFrame(self.tab_dashboard)
        self.dashboard_frame.pack(fill="both", expand=True, padx=4, pady=4)

    def _refresh_dashboard(self):
        for w in self.dashboard_frame.winfo_children():
            w.destroy()

        summary = get_summary(self.tax_data)
        config = load_config()
        province = config.get("province", "ON")
        tax_year = int(self.year_var.get())

        # ── Title with export button ──
        title_row = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        title_row.pack(fill="x", pady=(8, 12))

        ctk.CTkLabel(
            title_row,
            text=f"Tax Year {tax_year} Summary",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left")

        ctk.CTkButton(
            title_row, text="Export Cheat Sheet PDF",
            command=self._export_cheat_sheet, width=200,
            fg_color=COLORS["highlight"], hover_color="#c93653",
        ).pack(side="right")

        # ── Estimated Refund / Owing (BIG, top of dashboard) ──
        try:
            estimate = calculate_estimated_tax(summary, province=province)
            refund = estimate["refund_or_owing"]
            is_refund = estimate["is_refund"]

            label = "Estimated Refund" if is_refund else "Estimated Amount Owing"
            color = COLORS["green"] if is_refund else COLORS["warning"]
            amount = abs(refund)

            refund_frame = ctk.CTkFrame(self.dashboard_frame, fg_color=color, corner_radius=10)
            refund_frame.pack(fill="x", pady=(0, 16))

            ctk.CTkLabel(
                refund_frame, text=label,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="white",
            ).pack(side="left", padx=20, pady=14)

            ctk.CTkLabel(
                refund_frame, text=f"${amount:,.2f}",
                font=ctk.CTkFont(size=32, weight="bold"),
                text_color="white",
            ).pack(side="right", padx=20, pady=10)

            # Subtle estimate caveat
            ctk.CTkLabel(
                self.dashboard_frame,
                text=(
                    f"Estimate using 2024 brackets for {PROVINCE_NAMES.get(province, province)}. "
                    f"Federal tax: ${estimate['federal_tax']:,.2f} | "
                    f"Provincial tax: ${estimate['provincial_tax']:,.2f} | "
                    f"Marginal rate: {(estimate['marginal_rate_federal'] + estimate['marginal_rate_provincial']) * 100:.1f}%"
                ),
                font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"],
                wraplength=900, justify="left",
            ).pack(pady=(0, 12), anchor="w")
        except Exception as e:
            estimate = None
            ctk.CTkLabel(
                self.dashboard_frame,
                text=f"Could not calculate estimate: {e}",
                text_color=COLORS["warning"],
            ).pack(pady=(0, 12), anchor="w")

        # ── Deadlines ──
        deadlines = get_deadlines(tax_year)
        if deadlines:
            self._section_header(self.dashboard_frame, "Important Deadlines")
            dl_frame = ctk.CTkFrame(self.dashboard_frame, fg_color=COLORS["card"])
            dl_frame.pack(fill="x", pady=(0, 12))
            for d in deadlines:
                self._deadline_row(dl_frame, d)

        # Stash estimate for export
        self._last_estimate = estimate
        self._last_deadlines = deadlines

        # Document counts
        counts_frame = ctk.CTkFrame(self.dashboard_frame, fg_color=COLORS["card"])
        counts_frame.pack(fill="x", pady=(0, 12))
        counts_frame.columnconfigure((0, 1, 2, 3), weight=1)

        self._stat_card(counts_frame, "T4 Slips", str(summary["t4_count"]), 0, 0)
        self._stat_card(counts_frame, "T5 Slips", str(summary["t5_count"]), 0, 1)
        self._stat_card(counts_frame, "Other Slips", str(summary["canadian_other_count"] + summary["us_form_count"]), 0, 2)
        self._stat_card(counts_frame, "Bank Accounts", str(summary.get("bank_accounts_connected", 0)), 0, 3)

        # ── Income section ──
        self._section_header(self.dashboard_frame, "Income")
        income_frame = ctk.CTkFrame(self.dashboard_frame, fg_color=COLORS["card"])
        income_frame.pack(fill="x", pady=(0, 12))

        rows = [
            ("Employment Income (T4)", summary["total_employment_income"], COLORS["income"]),
            ("Interest Income (T5)", summary["total_interest_income"], COLORS["income"]),
            ("Eligible Dividends (T5/T3)", summary["total_eligible_dividends"], COLORS["income"]),
            ("Capital Gains (T3)", summary["total_capital_gains"], COLORS["income"]),
            ("Self-Employment (T4A)", summary["total_self_employment"], COLORS["income"]),
            ("Pension Income (T4A)", summary["total_pension_income"], COLORS["income"]),
            ("EI Benefits (T4E)", summary["total_ei_benefits"], COLORS["income"]),
            ("RRSP Withdrawals (T4RSP)", summary["total_rrsp_withdrawals"], COLORS["income"]),
            ("Other Income", summary["total_other_income"], COLORS["income"]),
        ]
        for label, val, color in rows:
            if val > 0:
                self._summary_row(income_frame, label, val, color)

        # US income if any
        if summary["total_us_wages"] > 0 or summary["total_us_freelance"] > 0:
            self._summary_row(income_frame, "US Wages (W-2) — convert to CAD", summary["total_us_wages"], COLORS["yellow"])
            if summary["total_us_freelance"] > 0:
                self._summary_row(income_frame, "US Freelance (1099-NEC) — convert to CAD", summary["total_us_freelance"], COLORS["yellow"])

        # Total income
        total_frame = ctk.CTkFrame(income_frame, fg_color=COLORS["accent"])
        total_frame.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkLabel(
            total_frame, text="Total Income (line 15000)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left", padx=12, pady=8)
        ctk.CTkLabel(
            total_frame, text=f"${summary['total_income']:,.2f}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["income"],
        ).pack(side="right", padx=12, pady=8)

        # ── Deductions at Source ──
        self._section_header(self.dashboard_frame, "Deductions at Source")
        withheld_frame = ctk.CTkFrame(self.dashboard_frame, fg_color=COLORS["card"])
        withheld_frame.pack(fill="x", pady=(0, 12))

        withheld_rows = [
            ("Income Tax Deducted (Box 22)", summary["total_income_tax_deducted"], COLORS["withheld"]),
            ("CPP Contributions (Box 16)", summary["total_cpp_contributions"], COLORS["withheld"]),
            ("EI Premiums (Box 18)", summary["total_ei_premiums"], COLORS["withheld"]),
            ("RPP Contributions (Box 20)", summary["total_rpp_contributions"], COLORS["deduction"]),
            ("Union Dues (Box 44)", summary["total_union_dues"], COLORS["deduction"]),
        ]
        for label, val, color in withheld_rows:
            if val > 0:
                self._summary_row(withheld_frame, label, val, color)

        if summary["total_us_tax_withheld"] > 0:
            self._summary_row(withheld_frame, "US Tax Withheld (foreign tax credit)", summary["total_us_tax_withheld"], COLORS["yellow"])

        total_deducted = summary["total_income_tax_deducted"] + summary["total_cpp_contributions"] + summary["total_ei_premiums"]
        total_w_frame = ctk.CTkFrame(withheld_frame, fg_color=COLORS["accent"])
        total_w_frame.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkLabel(
            total_w_frame, text="Total Tax + CPP + EI Deducted",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left", padx=12, pady=8)
        ctk.CTkLabel(
            total_w_frame, text=f"${total_deducted:,.2f}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["withheld"],
        ).pack(side="right", padx=12, pady=8)

        # ── Deductions & Credits ──
        self._section_header(self.dashboard_frame, "Deductions & Credits")
        ded_frame = ctk.CTkFrame(self.dashboard_frame, fg_color=COLORS["card"])
        ded_frame.pack(fill="x", pady=(0, 12))

        if summary["total_rrsp_contributions"] > 0:
            self._summary_row(ded_frame, "RRSP Contributions (line 20800)", summary["total_rrsp_contributions"], COLORS["deduction"])
        if summary["total_union_dues"] > 0:
            self._summary_row(ded_frame, "Union/Professional Dues (line 21200)", summary["total_union_dues"], COLORS["deduction"])
        if summary["total_deductions"] > 0:
            self._summary_row(ded_frame, "Total Deductions from Income", summary["total_deductions"], COLORS["deduction"])

        # ── Education section ──
        if summary["total_tuition"] > 0 or summary["total_scholarships"] > 0:
            self._section_header(self.dashboard_frame, "Education")
            edu_frame = ctk.CTkFrame(self.dashboard_frame, fg_color=COLORS["card"])
            edu_frame.pack(fill="x", pady=(0, 12))
            if summary["total_tuition"] > 0:
                self._summary_row(edu_frame, "Eligible Tuition (T2202)", summary["total_tuition"], COLORS["deduction"])
                self._summary_row(edu_frame, "Tuition Tax Credit (15%)", summary["tuition_credit"], COLORS["green"])
            if summary["total_scholarships"] > 0:
                self._summary_row(edu_frame, "Scholarships/Bursaries", summary["total_scholarships"], COLORS["yellow"])

        # ── Banking Activity section ──
        if summary.get("bank_txn_count", 0) > 0:
            self._section_header(self.dashboard_frame, "Banking Activity (Plaid)")
            bank_frame = ctk.CTkFrame(self.dashboard_frame, fg_color=COLORS["card"])
            bank_frame.pack(fill="x", pady=(0, 12))
            self._summary_row(bank_frame, "Total Deposits", summary["bank_deposits"], COLORS["income"])
            self._summary_row(bank_frame, "Total Expenses", summary["bank_expenses"], COLORS["warning"])
            self._summary_row(bank_frame, "Transactions Analyzed", summary["bank_txn_count"], COLORS["withheld"])

            ctk.CTkLabel(
                bank_frame,
                text="Note: Bank deposits are for reference — they may overlap with "
                     "T4/T5 income above. Don't double-count.",
                font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"],
                wraplength=650, justify="left",
            ).pack(padx=12, pady=(4, 10), anchor="w")

        # ── Alerts ──
        alerts = []
        if summary["total_self_employment"] > 0:
            alerts.append(
                f"You have ${summary['total_self_employment']:,.2f} in self-employment income. "
                f"You'll owe CPP on this (both employer + employee portions). "
                f"Track business expenses to reduce your net income. File by June 15 "
                f"(but any tax owing is still due April 30)."
            )
        if summary["total_income_tax_deducted"] == 0 and summary["total_income"] > 0:
            alerts.append(
                "No income tax deducted detected. If you owe taxes, CRA may "
                "charge interest. Consider making instalment payments."
            )
        if summary["t4_count"] > 1:
            alerts.append(
                f"You have {summary['t4_count']} T4s. Each employer deducted CPP/EI "
                f"separately — you may have overpaid. CRA will calculate the "
                f"refund automatically when you file."
            )
        if summary["total_ei_benefits"] > 0 and summary["total_income"] > 79000:
            alerts.append(
                "Your income may trigger EI clawback. If net income exceeds "
                "~$79K, you'll repay 30% of EI benefits above the threshold."
            )
        if summary["total_rrsp_contributions"] == 0 and summary["total_employment_income"] > 30000:
            alerts.append(
                "No RRSP contributions detected. Contributing to your RRSP "
                "directly reduces your taxable income. Check your contribution "
                "room on MyCRA or your Notice of Assessment."
            )

        if alerts:
            self._section_header(self.dashboard_frame, "Alerts & Reminders")
            for alert_text in alerts:
                alert_frame = ctk.CTkFrame(self.dashboard_frame, fg_color="#3d1f1f")
                alert_frame.pack(fill="x", pady=(0, 6))
                ctk.CTkLabel(
                    alert_frame, text=f"  {alert_text}",
                    wraplength=700, justify="left", text_color=COLORS["warning"],
                ).pack(padx=12, pady=10, anchor="w")

    def _stat_card(self, parent, label, value, row, col):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=col, padx=16, pady=12, sticky="nsew")
        ctk.CTkLabel(
            frame, text=value,
            font=ctk.CTkFont(size=32, weight="bold"),
        ).pack()
        ctk.CTkLabel(
            frame, text=label,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
        ).pack()

    def _section_header(self, parent, text):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(12, 4), anchor="w")

    def _summary_row(self, parent, label, value, color):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=13)).pack(side="left")
        ctk.CTkLabel(
            row, text=f"${value:,.2f}",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=color,
        ).pack(side="right")

    def _deadline_row(self, parent, deadline):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=4)

        days = deadline["days_until"]
        if days < 0:
            color = COLORS["text_muted"]
            status_text = format_deadline_text(deadline)
        elif days == 0:
            color = COLORS["warning"]
            status_text = "TODAY"
        elif days <= 7:
            color = COLORS["warning"]
            status_text = format_deadline_text(deadline)
        elif days <= 30:
            color = COLORS["yellow"]
            status_text = format_deadline_text(deadline)
        else:
            color = COLORS["text"]
            status_text = format_deadline_text(deadline)

        left_frame = ctk.CTkFrame(row, fg_color="transparent")
        left_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            left_frame, text=deadline["name"],
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            left_frame, text=deadline["description"],
            font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"],
            wraplength=600, justify="left",
        ).pack(anchor="w")

        ctk.CTkLabel(
            row, text=status_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=color,
        ).pack(side="right", padx=8)

    def _on_province_change(self, province):
        config = load_config()
        config["province"] = province
        save_config(config)
        self.refresh_all()

    def _export_cheat_sheet(self):
        if not getattr(self, "_last_estimate", None):
            messagebox.showwarning(
                "No Data",
                "Upload at least one tax slip first so there's something to summarize.",
            )
            return

        tax_year = int(self.year_var.get())
        default_name = f"TaxKing_CheatSheet_{tax_year}.pdf"
        filepath = filedialog.asksaveasfilename(
            title="Save Tax Cheat Sheet",
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF Files", "*.pdf")],
        )
        if not filepath:
            return

        try:
            summary = get_summary(self.tax_data)
            generate_cheat_sheet(
                filepath, tax_year, summary,
                self._last_estimate, self._last_deadlines,
            )

            if messagebox.askyesno(
                "Cheat Sheet Saved!",
                f"Saved to:\n{filepath}\n\nOpen it now?",
            ):
                os.startfile(filepath) if sys.platform == "win32" else None
        except Exception as e:
            messagebox.showerror("Export Error", f"Could not generate PDF:\n{e}")

    def _restart_watch_folder(self):
        """Stop any existing watch folder and start a new one based on config."""
        if self._watch_folder:
            self._watch_folder.stop()
            self._watch_folder = None

        config = load_config()
        folder = config.get("watch_folder", "")
        enabled = config.get("watch_folder_enabled", False)

        if enabled and folder:
            self._watch_folder = WatchFolder(folder, self._on_watch_folder_new_file)
            self._watch_folder.start(self)

    def _on_watch_folder_new_file(self, filepath):
        """Called when watch folder spots a new PDF. Try to import it."""
        try:
            filename = os.path.basename(filepath)
            stored_path = store_document(filepath)
            form_type, parsed_data = parse_document(stored_path)

            # Only auto-import if it's recognizably a tax form
            # If it's "unknown", skip silently — could be any old PDF
            if form_type == "unknown":
                return

            self.tax_data = add_document_entry(
                self.tax_data, form_type, stored_path,
                parsed_data, filename,
            )
            self.refresh_all()

            display = FORM_DISPLAY_NAMES.get(form_type, form_type)
            # Show a brief toast-like notification
            self.title(f"TaxKing AI — Auto-imported {display} from watch folder")
            self.after(5000, lambda: self.title("TaxKing AI — Tax Document Organizer"))
        except Exception:
            pass  # Silent failure for auto-import

    def _show_app_settings(self):
        config = load_config()

        dialog = ctk.CTkToplevel(self)
        dialog.title("App Settings")
        dialog.geometry("560x420")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="App Settings",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(padx=20, pady=(20, 12))

        # ── Watch Folder ──
        ctk.CTkLabel(
            dialog, text="Watch Folder (auto-import)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=20, pady=(8, 2), anchor="w")
        ctk.CTkLabel(
            dialog,
            text="Point at a folder (e.g. Downloads). When PDFs land there, "
                 "TaxKing AI will auto-import them as tax slips.",
            font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"],
            wraplength=500, justify="left",
        ).pack(padx=20, pady=(0, 6), anchor="w")

        wf_row = ctk.CTkFrame(dialog, fg_color="transparent")
        wf_row.pack(fill="x", padx=20, pady=(0, 4))
        wf_entry = ctk.CTkEntry(wf_row, width=380, placeholder_text="C:\\Users\\you\\Downloads")
        wf_entry.pack(side="left", padx=(0, 4))
        if config.get("watch_folder"):
            wf_entry.insert(0, config["watch_folder"])

        def browse_folder():
            from tkinter import filedialog as fd
            folder = fd.askdirectory(title="Select folder to watch")
            if folder:
                wf_entry.delete(0, "end")
                wf_entry.insert(0, folder)

        ctk.CTkButton(
            wf_row, text="Browse", width=80, command=browse_folder,
        ).pack(side="left")

        enabled_var = ctk.BooleanVar(value=config.get("watch_folder_enabled", False))
        ctk.CTkCheckBox(
            dialog, text="Enable watch folder", variable=enabled_var,
        ).pack(padx=20, pady=(4, 12), anchor="w")

        # ── Province ──
        ctk.CTkLabel(
            dialog, text="Province / Territory",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=20, pady=(8, 4), anchor="w")

        prov_var = ctk.StringVar(value=config.get("province", "ON"))
        prov_menu = ctk.CTkOptionMenu(
            dialog, values=list(PROVINCE_NAMES.keys()), variable=prov_var, width=200,
        )
        prov_menu.pack(padx=20, pady=(0, 12), anchor="w")

        def save_settings():
            config["watch_folder"] = wf_entry.get().strip()
            config["watch_folder_enabled"] = enabled_var.get()
            config["province"] = prov_var.get()
            save_config(config)
            self.province_var.set(prov_var.get())
            self._restart_watch_folder()
            self.refresh_all()
            dialog.destroy()

        ctk.CTkButton(
            dialog, text="Save", command=save_settings,
            width=140, fg_color=COLORS["green"], hover_color="#27ae60",
        ).pack(pady=(8, 16))

    # ── Documents Tab ───────────────────────────────────────────
    def _build_documents_tab(self):
        # Toolbar
        toolbar = ctk.CTkFrame(self.tab_documents, fg_color="transparent")
        toolbar.pack(fill="x", padx=4, pady=(4, 8))

        ctk.CTkButton(
            toolbar, text="Upload PDF", command=self._upload_document,
            width=140, fg_color=COLORS["green"], hover_color="#27ae60",
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            toolbar,
            text="Upload T4, T5, T3, T2202, RRSP receipts, and other tax slip PDFs. "
                 "The app will auto-detect the form type and extract key fields.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
            wraplength=500,
        ).pack(side="left", padx=8)

        # OCR status indicator
        ocr_status = check_ocr_status()
        if ocr_status["ocr_ready"]:
            ocr_text = "OCR: Ready"
            ocr_color = COLORS["green"]
        else:
            ocr_text = "OCR: Not installed"
            ocr_color = COLORS["yellow"]
        ocr_label = ctk.CTkLabel(
            toolbar, text=ocr_text,
            font=ctk.CTkFont(size=11),
            text_color=ocr_color, cursor="hand2",
        )
        ocr_label.pack(side="right", padx=8)
        ocr_label.bind("<Button-1>", lambda e: self._show_ocr_info())

        # Document list
        self.doc_list_frame = ctk.CTkScrollableFrame(self.tab_documents)
        self.doc_list_frame.pack(fill="both", expand=True, padx=4, pady=4)

    def _refresh_documents(self):
        for w in self.doc_list_frame.winfo_children():
            w.destroy()

        docs = self.tax_data.get("documents", [])
        if not docs:
            ctk.CTkLabel(
                self.doc_list_frame,
                text="No documents uploaded yet.\nClick 'Upload PDF' to get started.",
                font=ctk.CTkFont(size=14),
                text_color=COLORS["text_muted"],
            ).pack(pady=40)
            return

        for doc in docs:
            self._document_card(doc)

    def _document_card(self, doc):
        form_type = doc.get("form_type", "unknown")
        display_name = FORM_DISPLAY_NAMES.get(form_type, form_type.upper())
        parsed = doc.get("parsed_data", {})

        card = ctk.CTkFrame(self.doc_list_frame, fg_color=COLORS["card"], corner_radius=8)
        card.pack(fill="x", pady=(0, 8))

        # Header row
        header = ctk.CTkFrame(card, fg_color=COLORS["accent"], corner_radius=6)
        header.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(
            header, text=display_name,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["highlight"],
        ).pack(side="left", padx=12, pady=6)

        ctk.CTkLabel(
            header, text=doc.get("original_name", ""),
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
        ).pack(side="left", padx=8, pady=6)

        # Delete button
        doc_id = doc.get("id")
        ctk.CTkButton(
            header, text="Delete", width=70,
            fg_color=COLORS["warning"], hover_color="#c0392b",
            command=lambda d=doc_id: self._delete_document(d),
        ).pack(side="right", padx=8, pady=6)

        # Info button
        if form_type in FORM_TIPS:
            ctk.CTkButton(
                header, text="Info", width=60,
                fg_color="#2980b9", hover_color="#2471a3",
                command=lambda ft=form_type: self._show_form_info(ft),
            ).pack(side="right", padx=(0, 4), pady=6)

        # OCR warning
        if parsed.get("_ocr_warning"):
            warn_frame = ctk.CTkFrame(card, fg_color="#3d2f1f", corner_radius=6)
            warn_frame.pack(fill="x", padx=12, pady=(4, 8))
            ctk.CTkLabel(
                warn_frame, text=parsed["_ocr_warning"],
                font=ctk.CTkFont(size=12),
                text_color=COLORS["yellow"],
                wraplength=650, justify="left",
            ).pack(padx=12, pady=8, anchor="w")
            ctk.CTkButton(
                warn_frame, text="OCR Setup Guide", width=130,
                fg_color="#2980b9", hover_color="#2471a3",
                command=self._show_ocr_info,
            ).pack(padx=12, pady=(0, 8), anchor="w")

        # Parsed data grid
        if parsed and not parsed.get("raw_text") and not parsed.get("_ocr_warning"):
            data_frame = ctk.CTkFrame(card, fg_color="transparent")
            data_frame.pack(fill="x", padx=16, pady=(4, 10))

            tips = FORM_TIPS.get(form_type, {})

            col = 0
            row_num = 0
            data_frame.columnconfigure((0, 1, 2, 3), weight=1)

            for key, value in parsed.items():
                if not value or key.startswith("_"):
                    continue

                # Format label
                label_text = key.replace("_", " ").title()
                tip_data = tips.get(key)

                field_frame = ctk.CTkFrame(data_frame, fg_color="transparent")
                field_frame.grid(row=row_num, column=col, padx=8, pady=4, sticky="w")

                label_widget = ctk.CTkLabel(
                    field_frame, text=label_text,
                    font=ctk.CTkFont(size=11),
                    text_color=COLORS["text_muted"],
                )
                label_widget.pack(anchor="w")

                # Format value
                display_val = value
                try:
                    num = float(str(value).replace(",", ""))
                    display_val = f"${num:,.2f}"
                except (ValueError, TypeError):
                    pass

                val_widget = ctk.CTkLabel(
                    field_frame, text=str(display_val),
                    font=ctk.CTkFont(size=13, weight="bold"),
                )
                val_widget.pack(anchor="w")

                # Add tip icon if available
                if tip_data:
                    tip_btn = ctk.CTkButton(
                        field_frame, text="?", width=20, height=20,
                        font=ctk.CTkFont(size=10),
                        fg_color="#555", hover_color="#777",
                        command=lambda t=tip_data: self._show_tip(t[0], t[1]),
                    )
                    tip_btn.pack(anchor="w", pady=(2, 0))

                col += 1
                if col >= 4:
                    col = 0
                    row_num += 1

        elif parsed.get("raw_text"):
            ctk.CTkLabel(
                card,
                text="Could not auto-parse fields. Raw text preview:",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["yellow"],
            ).pack(padx=16, pady=(4, 2), anchor="w")
            raw_text = parsed["raw_text"][:500] + ("..." if len(parsed["raw_text"]) > 500 else "")
            ctk.CTkLabel(
                card, text=raw_text,
                font=ctk.CTkFont(size=11),
                text_color=COLORS["text_muted"],
                wraplength=700, justify="left",
            ).pack(padx=16, pady=(0, 10), anchor="w")

    def _upload_document(self):
        filepaths = filedialog.askopenfilenames(
            title="Select Tax Document PDFs",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
        )
        if not filepaths:
            return

        for fp in filepaths:
            try:
                stored_path = store_document(fp)
                form_type, parsed_data = parse_document(stored_path)

                if form_type == "unknown":
                    form_type = self._ask_form_type(os.path.basename(fp))
                    if form_type and form_type != "unknown":
                        _, parsed_data = parse_document(stored_path, form_type)

                self.tax_data = add_document_entry(
                    self.tax_data, form_type, stored_path,
                    parsed_data, os.path.basename(fp),
                )
            except Exception as e:
                messagebox.showerror("Upload Error", f"Error processing {os.path.basename(fp)}:\n{e}")

        self.refresh_all()

    def _ask_form_type(self, filename: str) -> str:
        """Show a dialog to let the user pick the form type."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Select Form Type")
        dialog.geometry("350x520")
        dialog.transient(self)
        dialog.grab_set()

        result = {"value": "unknown"}

        ctk.CTkLabel(
            dialog,
            text=f"Could not auto-detect the form type for:\n{filename}\n\nPlease select the form type:",
            wraplength=300, justify="left",
        ).pack(padx=16, pady=(16, 8))

        form_types = list(FORM_DISPLAY_NAMES.items())
        for key, display in form_types:
            ctk.CTkButton(
                dialog, text=display, width=200,
                command=lambda k=key: (result.update({"value": k}), dialog.destroy()),
            ).pack(pady=3)

        ctk.CTkButton(
            dialog, text="Skip / Unknown", width=200,
            fg_color="gray", hover_color="#555",
            command=dialog.destroy,
        ).pack(pady=(8, 16))

        self.wait_window(dialog)
        return result["value"]

    def _delete_document(self, doc_id):
        if messagebox.askyesno("Confirm Delete", "Remove this document from your tax records?"):
            self.tax_data = delete_document(doc_id, self.tax_data)
            self.refresh_all()

    def _show_form_info(self, form_type):
        tips = FORM_TIPS.get(form_type, {})
        form_info = tips.get("_form")
        if form_info:
            self._show_tip(form_info[0], form_info[1])

    def _show_ocr_info(self):
        status = check_ocr_status()
        if status["ocr_ready"]:
            msg = (
                "OCR is fully set up!\n\n"
                "Scanned PDFs and image-based documents will be processed "
                "using Tesseract OCR automatically when pdfplumber can't "
                "extract text directly."
            )
        else:
            parts = ["OCR is not fully set up. To enable scanned PDF support:\n"]
            if not status["tesseract_binary"]:
                parts.append(
                    "1. Install Tesseract OCR:\n"
                    "   - Windows: Download from\n"
                    "     github.com/UB-Mannheim/tesseract/wiki\n"
                    "     and add it to your PATH\n"
                    "   - Mac: brew install tesseract\n"
                    "   - Linux: sudo apt install tesseract-ocr"
                )
            if not status["pytesseract"]:
                parts.append("2. Run: pip install pytesseract")
            parts.append(
                "\nWithout OCR, only digitally-generated PDFs (with a text "
                "layer) can be parsed. Scanned or photographed documents "
                "need OCR."
            )
            msg = "\n".join(parts)

        self._show_tip("OCR Status", msg)

    def _show_tip(self, title, message):
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("500x250")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(padx=20, pady=(20, 8))

        ctk.CTkLabel(
            dialog, text=message,
            font=ctk.CTkFont(size=13),
            wraplength=460, justify="left",
        ).pack(padx=20, pady=(0, 16), fill="both", expand=True)

        ctk.CTkButton(dialog, text="Got it", command=dialog.destroy, width=100).pack(pady=(0, 16))

    # ── Email Scanner Tab ──────────────────────────────────────
    def _build_email_tab(self):
        # Config section
        config_frame = ctk.CTkFrame(self.tab_email, fg_color=COLORS["card"])
        config_frame.pack(fill="x", padx=4, pady=(4, 8))

        ctk.CTkLabel(
            config_frame,
            text="Scan your email for tax slips (T4, T5, T2202, etc.) sent as PDF attachments.",
            font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"],
        ).pack(padx=16, pady=(10, 4), anchor="w")

        ctk.CTkLabel(
            config_frame,
            text="For Gmail: use an App Password (Google Account > Security > App Passwords). "
                 "Your credentials are only used for this scan and are not stored.",
            font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"],
            wraplength=700, justify="left",
        ).pack(padx=16, pady=(0, 8), anchor="w")

        # Email field
        row1 = ctk.CTkFrame(config_frame, fg_color="transparent")
        row1.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row1, text="Email:", width=120).pack(side="left")
        self.email_addr_entry = ctk.CTkEntry(row1, width=300, placeholder_text="you@gmail.com")
        self.email_addr_entry.pack(side="left", padx=8)

        # Password field
        row2 = ctk.CTkFrame(config_frame, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row2, text="App Password:", width=120).pack(side="left")
        self.email_pass_entry = ctk.CTkEntry(row2, width=300, placeholder_text="App password (not your regular password)", show="*")
        self.email_pass_entry.pack(side="left", padx=8)

        # IMAP server (auto-detected)
        row3 = ctk.CTkFrame(config_frame, fg_color="transparent")
        row3.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row3, text="IMAP Server:", width=120).pack(side="left")
        self.imap_server_entry = ctk.CTkEntry(row3, width=300, placeholder_text="Auto-detected from email")
        self.imap_server_entry.pack(side="left", padx=8)

        # Scan button
        btn_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(8, 12))
        ctk.CTkButton(
            btn_frame, text="Scan for Tax Slips", command=self._scan_email,
            width=180, fg_color=COLORS["green"], hover_color="#27ae60",
        ).pack(side="left")
        self.email_status_label = ctk.CTkLabel(
            btn_frame, text="", font=ctk.CTkFont(size=12),
        )
        self.email_status_label.pack(side="left", padx=12)

        # Results section
        ctk.CTkLabel(
            self.tab_email, text="Found Tax Emails",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=8, pady=(4, 4), anchor="w")

        self.email_results_frame = ctk.CTkScrollableFrame(self.tab_email)
        self.email_results_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # Store connection for reuse during import
        self._imap_conn = None
        self._email_results = []

    def _scan_email(self):
        email_addr = self.email_addr_entry.get().strip()
        password = self.email_pass_entry.get().strip()

        if not email_addr or not password:
            messagebox.showwarning("Missing Credentials", "Enter your email and app password.")
            return

        imap_server = self.imap_server_entry.get().strip()
        if not imap_server:
            imap_server = guess_imap_server(email_addr)
            self.imap_server_entry.delete(0, "end")
            self.imap_server_entry.insert(0, imap_server)

        self.email_status_label.configure(text="Connecting...", text_color=COLORS["yellow"])
        self.update_idletasks()

        try:
            if self._imap_conn:
                imap_disconnect(self._imap_conn)
            self._imap_conn = imap_connect(email_addr, password, imap_server)
        except Exception as e:
            self.email_status_label.configure(text="Connection failed", text_color=COLORS["warning"])
            messagebox.showerror("Connection Error", f"Could not connect:\n{e}")
            return

        self.email_status_label.configure(text="Scanning...", text_color=COLORS["yellow"])
        self.update_idletasks()

        try:
            tax_year = int(self.year_var.get())
            results = scan_for_tax_emails(self._imap_conn, year=tax_year)
            self._email_results = results
        except Exception as e:
            self.email_status_label.configure(text="Scan failed", text_color=COLORS["warning"])
            messagebox.showerror("Scan Error", f"Error scanning emails:\n{e}")
            return

        self.email_status_label.configure(
            text=f"Found {len(results)} emails with PDF attachments",
            text_color=COLORS["green"],
        )
        self._refresh_email_results()

    def _refresh_email_results(self):
        for w in self.email_results_frame.winfo_children():
            w.destroy()

        if not self._email_results:
            ctk.CTkLabel(
                self.email_results_frame,
                text="No tax-related emails found yet. Click 'Scan for Tax Slips' to search.",
                font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"],
            ).pack(pady=20)
            return

        for result in self._email_results:
            card = ctk.CTkFrame(self.email_results_frame, fg_color=COLORS["card"], corner_radius=8)
            card.pack(fill="x", pady=(0, 6))

            # Email info
            header = ctk.CTkFrame(card, fg_color=COLORS["accent"], corner_radius=6)
            header.pack(fill="x", padx=8, pady=(8, 4))

            subject = result.get("subject", "No Subject")[:80]
            ctk.CTkLabel(
                header, text=subject,
                font=ctk.CTkFont(size=13, weight="bold"),
            ).pack(side="left", padx=12, pady=6)

            date_str = result.get("date", "")[:25]
            ctk.CTkLabel(
                header, text=date_str,
                font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"],
            ).pack(side="right", padx=12, pady=6)

            sender = result.get("sender", "")[:60]
            ctk.CTkLabel(
                card, text=f"From: {sender}",
                font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"],
            ).pack(padx=20, pady=(2, 4), anchor="w")

            # Attachments with import buttons
            for att in result.get("attachments", []):
                att_frame = ctk.CTkFrame(card, fg_color="transparent")
                att_frame.pack(fill="x", padx=20, pady=2)

                filename = att.get("filename", "attachment.pdf")
                size_kb = att.get("size", 0) / 1024
                ctk.CTkLabel(
                    att_frame, text=f"{filename} ({size_kb:.0f} KB)",
                    font=ctk.CTkFont(size=12),
                ).pack(side="left")

                msg_id = result.get("msg_id")
                ctk.CTkButton(
                    att_frame, text="Import", width=80,
                    fg_color=COLORS["green"], hover_color="#27ae60",
                    command=lambda mid=msg_id, fn=filename: self._import_email_attachment(mid, fn),
                ).pack(side="right", padx=4)

            # Bottom padding
            ctk.CTkFrame(card, fg_color="transparent", height=4).pack()

    def _import_email_attachment(self, msg_id, filename):
        if not self._imap_conn:
            messagebox.showwarning("Not Connected", "Please scan your email again.")
            return

        try:
            saved_path = download_attachment(self._imap_conn, msg_id, filename)
            if not saved_path:
                messagebox.showerror("Download Error", f"Could not download {filename}")
                return

            form_type, parsed_data = parse_document(saved_path)

            if form_type == "unknown":
                form_type = self._ask_form_type(filename)
                if form_type and form_type != "unknown":
                    _, parsed_data = parse_document(saved_path, form_type)

            self.tax_data = add_document_entry(
                self.tax_data, form_type, saved_path,
                parsed_data, filename,
            )
            self.refresh_all()
            messagebox.showinfo("Imported", f"{filename} imported as {FORM_DISPLAY_NAMES.get(form_type, form_type)}!")
        except Exception as e:
            messagebox.showerror("Import Error", f"Error importing {filename}:\n{e}")

    # ── Bank Accounts Tab ───────────────────────────────────────
    def _build_bank_tab(self):
        # Toolbar
        toolbar = ctk.CTkFrame(self.tab_bank, fg_color="transparent")
        toolbar.pack(fill="x", padx=4, pady=(4, 8))

        ctk.CTkButton(
            toolbar, text="Connect Bank", command=self._connect_bank,
            width=140, fg_color=COLORS["green"], hover_color="#27ae60",
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            toolbar, text="Pull Transactions", command=self._pull_transactions,
            width=160, fg_color=COLORS["withheld"], hover_color="#2980b9",
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            toolbar, text="Plaid Settings", command=self._show_plaid_settings,
            width=120, fg_color=COLORS["accent"], hover_color="#1a4a8a",
        ).pack(side="left", padx=(0, 8))

        # Status
        config = load_config()
        if is_plaid_configured(config):
            status_text = "Plaid: Configured"
            status_color = COLORS["green"]
        else:
            status_text = "Plaid: Not configured"
            status_color = COLORS["yellow"]
        self.plaid_status_label = ctk.CTkLabel(
            toolbar, text=status_text,
            font=ctk.CTkFont(size=11), text_color=status_color,
        )
        self.plaid_status_label.pack(side="right", padx=8)

        # Connected accounts section
        ctk.CTkLabel(
            self.tab_bank, text="Connected Accounts",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=8, pady=(4, 4), anchor="w")

        self.bank_accounts_frame = ctk.CTkScrollableFrame(self.tab_bank, height=120)
        self.bank_accounts_frame.pack(fill="x", padx=4, pady=(0, 8))

        # Transactions section
        ctk.CTkLabel(
            self.tab_bank, text="Transactions",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=8, pady=(4, 4), anchor="w")

        self.bank_txn_frame = ctk.CTkScrollableFrame(self.tab_bank)
        self.bank_txn_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))

    def _refresh_bank_tab(self):
        # Refresh accounts display
        for w in self.bank_accounts_frame.winfo_children():
            w.destroy()

        connected = self.tax_data.get("plaid_items", [])
        if not connected:
            ctk.CTkLabel(
                self.bank_accounts_frame,
                text="No bank accounts connected. Click 'Connect Bank' to link an account via Plaid.",
                font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"],
            ).pack(pady=12)
        else:
            for item in connected:
                for acct in item.get("accounts", []):
                    row = ctk.CTkFrame(self.bank_accounts_frame, fg_color=COLORS["card"], corner_radius=6)
                    row.pack(fill="x", pady=(0, 4))

                    acct_name = acct.get("name", "Account")
                    mask = acct.get("mask", "")
                    acct_type = acct.get("type", "")
                    balance = acct.get("balance_current", 0)

                    ctk.CTkLabel(
                        row, text=f"{acct_name} (****{mask})",
                        font=ctk.CTkFont(size=13, weight="bold"),
                    ).pack(side="left", padx=12, pady=8)

                    ctk.CTkLabel(
                        row, text=acct_type.title(),
                        font=ctk.CTkFont(size=11),
                        text_color=COLORS["text_muted"],
                    ).pack(side="left", padx=8, pady=8)

                    ctk.CTkLabel(
                        row, text=f"${balance:,.2f}",
                        font=ctk.CTkFont(size=13, weight="bold"),
                        text_color=COLORS["income"],
                    ).pack(side="right", padx=12, pady=8)

                # Disconnect button
                item_id = item.get("item_id")
                ctk.CTkButton(
                    self.bank_accounts_frame, text="Disconnect", width=100,
                    fg_color=COLORS["warning"], hover_color="#c0392b",
                    command=lambda iid=item_id: self._disconnect_bank(iid),
                ).pack(anchor="e", padx=8, pady=(0, 8))

        # Refresh transactions display
        for w in self.bank_txn_frame.winfo_children():
            w.destroy()

        transactions = self.tax_data.get("plaid_transactions", [])
        if not transactions:
            ctk.CTkLabel(
                self.bank_txn_frame,
                text="No transactions loaded. Connect a bank and click 'Pull Transactions'.",
                font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"],
            ).pack(pady=20)
        else:
            # Summary row
            income_txns = [t for t in transactions if t.get("amount", 0) < 0]
            expense_txns = [t for t in transactions if t.get("amount", 0) > 0]
            total_income = sum(abs(t["amount"]) for t in income_txns)
            total_expenses = sum(t["amount"] for t in expense_txns)

            summary_frame = ctk.CTkFrame(self.bank_txn_frame, fg_color=COLORS["card"], corner_radius=6)
            summary_frame.pack(fill="x", pady=(0, 8))
            summary_frame.columnconfigure((0, 1, 2), weight=1)

            self._stat_card(summary_frame, "Transactions", str(len(transactions)), 0, 0)
            self._stat_card(summary_frame, "Income (deposits)", f"${total_income:,.2f}", 0, 1)
            self._stat_card(summary_frame, "Expenses", f"${total_expenses:,.2f}", 0, 2)

            # Transaction list (most recent first)
            sorted_txns = sorted(transactions, key=lambda t: t.get("date", ""), reverse=True)
            for txn in sorted_txns[:200]:  # Show last 200
                txn_row = ctk.CTkFrame(self.bank_txn_frame, fg_color=COLORS["card"], corner_radius=4)
                txn_row.pack(fill="x", pady=(0, 2))

                date_str = txn.get("date", "")
                ctk.CTkLabel(
                    txn_row, text=date_str,
                    font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"], width=90,
                ).pack(side="left", padx=(10, 4), pady=6)

                name = txn.get("merchant_name") or txn.get("name", "Unknown")
                ctk.CTkLabel(
                    txn_row, text=name,
                    font=ctk.CTkFont(size=12),
                ).pack(side="left", padx=4, pady=6)

                categories = txn.get("category", [])
                if categories:
                    cat_text = " > ".join(categories[:2])
                    ctk.CTkLabel(
                        txn_row, text=cat_text,
                        font=ctk.CTkFont(size=10), text_color=COLORS["text_muted"],
                    ).pack(side="left", padx=8, pady=6)

                amount = txn.get("amount", 0)
                # Plaid: positive = money leaving account, negative = money coming in
                if amount < 0:
                    amt_text = f"+${abs(amount):,.2f}"
                    amt_color = COLORS["income"]
                else:
                    amt_text = f"-${amount:,.2f}"
                    amt_color = COLORS["warning"]

                ctk.CTkLabel(
                    txn_row, text=amt_text,
                    font=ctk.CTkFont(size=12, weight="bold"), text_color=amt_color,
                ).pack(side="right", padx=10, pady=6)

    def _connect_bank(self):
        config = load_config()
        if not is_plaid_configured(config):
            messagebox.showinfo(
                "Plaid Not Configured",
                "You need to set up your Plaid API credentials first.\n\n"
                "1. Sign up at dashboard.plaid.com (free)\n"
                "2. Get your client_id and secret from the dashboard\n"
                "3. Click 'Plaid Settings' to enter them here",
            )
            return

        try:
            link_token = create_link_token(config)
        except Exception as e:
            messagebox.showerror("Plaid Error", f"Failed to create link token:\n{e}")
            return

        def on_token_received(public_token):
            try:
                result = exchange_public_token(public_token, config)
                access_token = result["access_token"]
                item_id = result["item_id"]

                accounts = get_accounts(access_token, config)

                # Store in tax_data
                if "plaid_items" not in self.tax_data:
                    self.tax_data["plaid_items"] = []

                # Check if already connected
                existing = [i for i in self.tax_data["plaid_items"] if i["item_id"] == item_id]
                if existing:
                    existing[0]["accounts"] = accounts
                    existing[0]["access_token"] = access_token
                else:
                    self.tax_data["plaid_items"].append({
                        "item_id": item_id,
                        "access_token": access_token,
                        "accounts": accounts,
                        "date_connected": datetime.now().isoformat(),
                    })

                save_tax_data(self.tax_data)
                # Schedule UI refresh on main thread
                self.after(100, self.refresh_all)
            except Exception as e:
                self.after(100, lambda: messagebox.showerror("Plaid Error", f"Failed to connect:\n{e}"))

        start_plaid_link(link_token, on_token_received)

    def _pull_transactions(self):
        items = self.tax_data.get("plaid_items", [])
        if not items:
            messagebox.showinfo("No Accounts", "Connect a bank account first.")
            return

        config = load_config()
        tax_year = self.year_var.get()
        start_date = f"{tax_year}-01-01"
        end_date = f"{tax_year}-12-31"

        all_txns = []
        errors = []

        for item in items:
            access_token = item.get("access_token")
            if not access_token:
                continue
            try:
                txns = get_transactions(access_token, start_date, end_date, config)
                all_txns.extend(txns)

                # Also refresh account balances
                accounts = get_accounts(access_token, config)
                item["accounts"] = accounts
            except Exception as e:
                errors.append(str(e))

        self.tax_data["plaid_transactions"] = all_txns
        save_tax_data(self.tax_data)
        self.refresh_all()

        if errors:
            messagebox.showwarning(
                "Some Errors",
                f"Pulled {len(all_txns)} transactions but encountered errors:\n" + "\n".join(errors),
            )
        else:
            messagebox.showinfo(
                "Transactions Loaded",
                f"Pulled {len(all_txns)} transactions for tax year {tax_year}.",
            )

    def _disconnect_bank(self, item_id):
        if not messagebox.askyesno("Disconnect Bank", "Remove this bank connection?"):
            return
        self.tax_data["plaid_items"] = [
            i for i in self.tax_data.get("plaid_items", []) if i.get("item_id") != item_id
        ]
        save_tax_data(self.tax_data)
        self.refresh_all()

    def _show_plaid_settings(self):
        config = load_config()

        dialog = ctk.CTkToplevel(self)
        dialog.title("Plaid API Settings")
        dialog.geometry("520x380")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="Plaid API Configuration",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(padx=20, pady=(20, 4))

        ctk.CTkLabel(
            dialog,
            text="Sign up for free at dashboard.plaid.com\n"
                 "Use the 'Development' environment for real bank connections (free, up to 100).",
            font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"],
            wraplength=460, justify="left",
        ).pack(padx=20, pady=(0, 12))

        # Client ID
        ctk.CTkLabel(dialog, text="Client ID:", font=ctk.CTkFont(size=13)).pack(padx=20, anchor="w")
        client_id_entry = ctk.CTkEntry(dialog, width=460, placeholder_text="Your Plaid client_id")
        client_id_entry.pack(padx=20, pady=(2, 8))
        if config.get("plaid_client_id"):
            client_id_entry.insert(0, config["plaid_client_id"])

        # Secret
        ctk.CTkLabel(dialog, text="Secret:", font=ctk.CTkFont(size=13)).pack(padx=20, anchor="w")
        secret_entry = ctk.CTkEntry(dialog, width=460, placeholder_text="Your Plaid secret", show="*")
        secret_entry.pack(padx=20, pady=(2, 8))
        if config.get("plaid_secret"):
            secret_entry.insert(0, config["plaid_secret"])

        # Environment
        ctk.CTkLabel(dialog, text="Environment:", font=ctk.CTkFont(size=13)).pack(padx=20, anchor="w")
        env_var = ctk.StringVar(value=config.get("plaid_env", "development"))
        env_menu = ctk.CTkOptionMenu(
            dialog, values=["sandbox", "development"], variable=env_var, width=200,
        )
        env_menu.pack(padx=20, pady=(2, 12), anchor="w")

        def save_settings():
            config["plaid_client_id"] = client_id_entry.get().strip()
            config["plaid_secret"] = secret_entry.get().strip()
            config["plaid_env"] = env_var.get()
            save_config(config)

            # Update status label
            if is_plaid_configured(config):
                self.plaid_status_label.configure(text="Plaid: Configured", text_color=COLORS["green"])
            else:
                self.plaid_status_label.configure(text="Plaid: Not configured", text_color=COLORS["yellow"])

            dialog.destroy()

        ctk.CTkButton(
            dialog, text="Save", command=save_settings,
            width=140, fg_color=COLORS["green"], hover_color="#27ae60",
        ).pack(pady=(4, 16))

    # ── Manual Entry Tab ────────────────────────────────────────
    def _build_manual_tab(self):
        top_frame = ctk.CTkFrame(self.tab_manual, fg_color="transparent")
        top_frame.pack(fill="x", padx=4, pady=(4, 8))

        ctk.CTkLabel(
            top_frame,
            text="Manually enter tax values if you don't have a PDF or want to add corrections.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
        ).pack(anchor="w")

        form_frame = ctk.CTkFrame(self.tab_manual, fg_color=COLORS["card"])
        form_frame.pack(fill="x", padx=4, pady=(0, 8))

        # Form type
        row1 = ctk.CTkFrame(form_frame, fg_color="transparent")
        row1.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(row1, text="Form Type:", width=120).pack(side="left")
        self.manual_form_type = ctk.CTkOptionMenu(
            row1,
            values=list(FORM_DISPLAY_NAMES.values()),
            width=200,
            command=self._on_manual_form_change,
        )
        self.manual_form_type.pack(side="left", padx=8)

        # Field
        row2 = ctk.CTkFrame(form_frame, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(row2, text="Field:", width=120).pack(side="left")
        self.manual_field = ctk.CTkOptionMenu(row2, values=["Select a form type first"], width=300)
        self.manual_field.pack(side="left", padx=8)

        # Value
        row3 = ctk.CTkFrame(form_frame, fg_color="transparent")
        row3.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(row3, text="Amount ($):", width=120).pack(side="left")
        self.manual_value = ctk.CTkEntry(row3, width=200, placeholder_text="e.g. 45000.00")
        self.manual_value.pack(side="left", padx=8)

        # Label / Description
        row4 = ctk.CTkFrame(form_frame, fg_color="transparent")
        row4.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(row4, text="Label (optional):", width=120).pack(side="left")
        self.manual_label = ctk.CTkEntry(row4, width=300, placeholder_text="e.g. Employer name or note")
        self.manual_label.pack(side="left", padx=8)

        # Add button
        ctk.CTkButton(
            form_frame, text="Add Entry", command=self._add_manual_entry,
            fg_color=COLORS["green"], hover_color="#27ae60", width=140,
        ).pack(padx=16, pady=12)

        # Existing manual entries
        ctk.CTkLabel(
            self.tab_manual, text="Manual Entries",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=8, pady=(8, 4), anchor="w")

        self.manual_list_frame = ctk.CTkScrollableFrame(self.tab_manual)
        self.manual_list_frame.pack(fill="both", expand=True, padx=4, pady=4)

    def _on_manual_form_change(self, selected_display_name):
        # Reverse lookup form type key
        form_key = None
        for key, display in FORM_DISPLAY_NAMES.items():
            if display == selected_display_name:
                form_key = key
                break

        if form_key and form_key in FORM_TIPS:
            fields = [
                k.replace("_", " ").title()
                for k in FORM_TIPS[form_key]
                if not k.startswith("_")
            ]
            self.manual_field.configure(values=fields if fields else ["No fields defined"])
            if fields:
                self.manual_field.set(fields[0])
        else:
            self.manual_field.configure(values=["No fields defined"])

    def _add_manual_entry(self):
        value_str = self.manual_value.get().strip().replace(",", "").replace("$", "")
        if not value_str:
            messagebox.showwarning("Missing Value", "Please enter an amount.")
            return

        try:
            value = float(value_str)
        except ValueError:
            messagebox.showwarning("Invalid Amount", "Please enter a valid number.")
            return

        # Reverse lookup form type key
        selected_display = self.manual_form_type.get()
        form_key = "unknown"
        for key, display in FORM_DISPLAY_NAMES.items():
            if display == selected_display:
                form_key = key
                break

        # Convert field display name back to key
        field_display = self.manual_field.get()
        field_key = field_display.lower().replace(" ", "_")

        label = self.manual_label.get().strip() or f"{selected_display} - {field_display}"

        self.tax_data = add_manual_entry(self.tax_data, form_key, field_key, value, label)
        self.manual_value.delete(0, "end")
        self.manual_label.delete(0, "end")
        self.refresh_all()

    def _refresh_manual_entries(self):
        for w in self.manual_list_frame.winfo_children():
            w.destroy()

        entries = self.tax_data.get("manual_entries", [])
        if not entries:
            ctk.CTkLabel(
                self.manual_list_frame,
                text="No manual entries yet.",
                text_color=COLORS["text_muted"],
            ).pack(pady=20)
            return

        for entry in entries:
            row = ctk.CTkFrame(self.manual_list_frame, fg_color=COLORS["card"], corner_radius=6)
            row.pack(fill="x", pady=(0, 4))

            display_type = FORM_DISPLAY_NAMES.get(entry.get("form_type", ""), entry.get("form_type", ""))
            ctk.CTkLabel(
                row, text=display_type,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["highlight"],
            ).pack(side="left", padx=(12, 8), pady=8)

            ctk.CTkLabel(
                row, text=entry.get("label", ""),
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=4, pady=8)

            ctk.CTkLabel(
                row, text=f"${entry.get('value', 0):,.2f}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=COLORS["income"],
            ).pack(side="right", padx=(8, 4), pady=8)

            entry_id = entry.get("id")
            ctk.CTkButton(
                row, text="X", width=30, height=28,
                fg_color=COLORS["warning"], hover_color="#c0392b",
                command=lambda eid=entry_id: self._remove_manual_entry(eid),
            ).pack(side="right", padx=(4, 12), pady=8)

    def _remove_manual_entry(self, entry_id):
        self.tax_data = remove_manual_entry(self.tax_data, entry_id)
        self.refresh_all()

    # ── Tips Tab ────────────────────────────────────────────────
    def _build_tips_tab(self):
        tips_frame = ctk.CTkScrollableFrame(self.tab_tips)
        tips_frame.pack(fill="both", expand=True, padx=4, pady=4)

        ctk.CTkLabel(
            tips_frame, text="Tax Tips & Reminders",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(8, 16), anchor="w")

        for tip in GENERAL_TIPS:
            card = ctk.CTkFrame(tips_frame, fg_color=COLORS["card"], corner_radius=8)
            card.pack(fill="x", pady=(0, 8))

            ctk.CTkLabel(
                card, text=tip["title"],
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=COLORS["yellow"],
            ).pack(padx=16, pady=(12, 4), anchor="w")

            ctk.CTkLabel(
                card, text=tip["tip"],
                font=ctk.CTkFont(size=12),
                wraplength=700, justify="left",
            ).pack(padx=16, pady=(0, 12), anchor="w")

        # Form-specific tips
        ctk.CTkLabel(
            tips_frame, text="Form Reference Guide",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(20, 12), anchor="w")

        for form_key, tips in FORM_TIPS.items():
            form_info = tips.get("_form")
            if not form_info:
                continue

            display_name = FORM_DISPLAY_NAMES.get(form_key, form_key)
            card = ctk.CTkFrame(tips_frame, fg_color=COLORS["card"], corner_radius=8)
            card.pack(fill="x", pady=(0, 6))

            header_frame = ctk.CTkFrame(card, fg_color="transparent")
            header_frame.pack(fill="x", padx=16, pady=(10, 2))

            ctk.CTkLabel(
                header_frame, text=display_name,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=COLORS["highlight"],
            ).pack(side="left")

            ctk.CTkLabel(
                card, text=form_info[1],
                font=ctk.CTkFont(size=12),
                wraplength=700, justify="left",
                text_color=COLORS["text_muted"],
            ).pack(padx=16, pady=(0, 10), anchor="w")

    # ── Year Change ─────────────────────────────────────────────
    def _on_year_change(self, year):
        self.tax_data["tax_year"] = int(year)
        save_tax_data(self.tax_data)

    # ── Refresh ─────────────────────────────────────────────────
    def refresh_all(self):
        self._refresh_dashboard()
        self._refresh_documents()
        self._refresh_bank_tab()
        self._refresh_manual_entries()


def main():
    app = TaxKingApp()
    app.mainloop()


if __name__ == "__main__":
    main()

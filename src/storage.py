"""Local JSON-based storage for tax data."""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
PARSED_DIR = DATA_DIR / "parsed"
TAX_DATA_FILE = DATA_DIR / "tax_data.json"


def ensure_dirs():
    """Create data directories if they don't exist."""
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    PARSED_DIR.mkdir(parents=True, exist_ok=True)


def load_tax_data() -> dict:
    """Load all saved tax data from disk."""
    if TAX_DATA_FILE.exists():
        with open(TAX_DATA_FILE, "r") as f:
            return json.load(f)
    return {"tax_year": datetime.now().year - 1, "documents": [], "manual_entries": []}


def save_tax_data(data: dict):
    """Save tax data to disk."""
    ensure_dirs()
    with open(TAX_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def store_document(filepath: str) -> str:
    """Copy an uploaded document into the data/documents folder. Returns the stored path."""
    ensure_dirs()
    src = Path(filepath)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = DOCUMENTS_DIR / f"{timestamp}_{src.name}"
    shutil.copy2(str(src), str(dest))
    return str(dest)


def delete_document(doc_id: str, tax_data: dict) -> dict:
    """Remove a document entry and its file from storage."""
    tax_data["documents"] = [
        d for d in tax_data["documents"] if d.get("id") != doc_id
    ]
    save_tax_data(tax_data)
    return tax_data


def add_document_entry(tax_data: dict, form_type: str, source_file: str,
                       parsed_data: dict, original_name: str) -> dict:
    """Add a parsed document entry to the tax data."""
    doc_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    entry = {
        "id": doc_id,
        "form_type": form_type,
        "original_name": original_name,
        "stored_path": source_file,
        "parsed_data": parsed_data,
        "date_added": datetime.now().isoformat(),
    }
    tax_data["documents"].append(entry)
    save_tax_data(tax_data)
    return tax_data


def add_manual_entry(tax_data: dict, form_type: str, field: str,
                     value: float, label: str) -> dict:
    """Add a manually entered tax value."""
    entry_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    entry = {
        "id": entry_id,
        "form_type": form_type,
        "field": field,
        "value": value,
        "label": label,
        "date_added": datetime.now().isoformat(),
    }
    tax_data["manual_entries"].append(entry)
    save_tax_data(tax_data)
    return tax_data


def remove_manual_entry(tax_data: dict, entry_id: str) -> dict:
    """Remove a manual entry."""
    tax_data["manual_entries"] = [
        e for e in tax_data["manual_entries"] if e.get("id") != entry_id
    ]
    save_tax_data(tax_data)
    return tax_data


def get_summary(tax_data: dict) -> dict:
    """Compute a summary of all tax data across documents and manual entries."""
    summary = {
        # Canadian totals
        "total_employment_income": 0.0,
        "total_income_tax_deducted": 0.0,
        "total_cpp_contributions": 0.0,
        "total_ei_premiums": 0.0,
        "total_rpp_contributions": 0.0,
        "total_union_dues": 0.0,
        "total_rrsp_contributions": 0.0,
        "total_eligible_dividends": 0.0,
        "total_interest_income": 0.0,
        "total_capital_gains": 0.0,
        "total_other_income": 0.0,
        "total_tuition": 0.0,
        "total_scholarships": 0.0,
        "total_ei_benefits": 0.0,
        "total_rrsp_withdrawals": 0.0,
        "total_pension_income": 0.0,
        "total_self_employment": 0.0,
        # US totals (for cross-border)
        "total_us_wages": 0.0,
        "total_us_tax_withheld": 0.0,
        "total_us_freelance": 0.0,
        # Counts
        "t4_count": 0,
        "t5_count": 0,
        "canadian_other_count": 0,
        "us_form_count": 0,
    }

    for doc in tax_data.get("documents", []):
        data = doc.get("parsed_data", {})
        form_type = doc.get("form_type", "")

        # ── Canadian Forms ──
        if form_type == "t4":
            summary["t4_count"] += 1
            summary["total_employment_income"] += _to_float(data.get("employment_income", 0))
            summary["total_income_tax_deducted"] += _to_float(data.get("income_tax_deducted", 0))
            summary["total_cpp_contributions"] += _to_float(data.get("cpp_contributions", 0))
            summary["total_cpp_contributions"] += _to_float(data.get("cpp2_contributions", 0))
            summary["total_ei_premiums"] += _to_float(data.get("ei_premiums", 0))
            summary["total_rpp_contributions"] += _to_float(data.get("rpp_contributions", 0))
            summary["total_union_dues"] += _to_float(data.get("union_dues", 0))

        elif form_type == "t4a":
            summary["canadian_other_count"] += 1
            summary["total_pension_income"] += _to_float(data.get("pension_income", 0))
            summary["total_self_employment"] += _to_float(data.get("self_employed_commissions", 0))
            summary["total_self_employment"] += _to_float(data.get("fees_for_services", 0))
            summary["total_scholarships"] += _to_float(data.get("scholarships", 0))
            summary["total_other_income"] += _to_float(data.get("resp_educational", 0))
            summary["total_income_tax_deducted"] += _to_float(data.get("income_tax_deducted", 0))

        elif form_type == "t5":
            summary["t5_count"] += 1
            summary["total_eligible_dividends"] += _to_float(data.get("actual_dividends", 0))
            summary["total_interest_income"] += _to_float(data.get("interest_income", 0))
            summary["total_other_income"] += _to_float(data.get("foreign_income", 0))

        elif form_type == "t3":
            summary["canadian_other_count"] += 1
            summary["total_eligible_dividends"] += _to_float(data.get("actual_dividends", 0))
            summary["total_capital_gains"] += _to_float(data.get("capital_gains", 0))
            summary["total_other_income"] += _to_float(data.get("foreign_income", 0))
            summary["total_other_income"] += _to_float(data.get("other_income", 0))

        elif form_type == "t2202":
            summary["canadian_other_count"] += 1
            summary["total_tuition"] += _to_float(data.get("eligible_tuition", 0))

        elif form_type == "rrsp_receipt":
            summary["canadian_other_count"] += 1
            summary["total_rrsp_contributions"] += _to_float(data.get("contribution_amount", 0))

        elif form_type == "t4e":
            summary["canadian_other_count"] += 1
            summary["total_ei_benefits"] += _to_float(data.get("ei_benefits", 0))
            summary["total_income_tax_deducted"] += _to_float(data.get("income_tax_deducted", 0))

        elif form_type == "t4rsp":
            summary["canadian_other_count"] += 1
            summary["total_rrsp_withdrawals"] += _to_float(data.get("withdrawal_amount", 0))
            summary["total_income_tax_deducted"] += _to_float(data.get("income_tax_deducted", 0))

        # ── US Forms ──
        elif form_type == "w2":
            summary["us_form_count"] += 1
            summary["total_us_wages"] += _to_float(data.get("wages_tips", 0))
            summary["total_us_tax_withheld"] += _to_float(data.get("federal_tax_withheld", 0))

        elif form_type in ("1099_int", "1099_div", "1099_nec", "1099_misc"):
            summary["us_form_count"] += 1
            if form_type == "1099_int":
                summary["total_interest_income"] += _to_float(data.get("interest_income", 0))
            elif form_type == "1099_div":
                summary["total_eligible_dividends"] += _to_float(data.get("ordinary_dividends", 0))
            elif form_type == "1099_nec":
                summary["total_us_freelance"] += _to_float(data.get("nonemployee_compensation", 0))
            elif form_type == "1099_misc":
                summary["total_other_income"] += _to_float(data.get("rents", 0))
                summary["total_other_income"] += _to_float(data.get("other_income", 0))
            summary["total_us_tax_withheld"] += _to_float(data.get("federal_tax_withheld", 0))

        elif form_type in ("1098", "1098_t", "1098_e"):
            summary["us_form_count"] += 1

    # Include manual entries
    MANUAL_FIELD_MAP = {
        "employment_income": "total_employment_income",
        "income_tax_deducted": "total_income_tax_deducted",
        "cpp_contributions": "total_cpp_contributions",
        "ei_premiums": "total_ei_premiums",
        "interest_income": "total_interest_income",
        "actual_dividends": "total_eligible_dividends",
        "eligible_tuition": "total_tuition",
        "contribution_amount": "total_rrsp_contributions",
        "self_employed_commissions": "total_self_employment",
        "fees_for_services": "total_self_employment",
        "pension_income": "total_pension_income",
        "ei_benefits": "total_ei_benefits",
        # US fields
        "wages_tips": "total_us_wages",
        "nonemployee_compensation": "total_us_freelance",
    }
    for entry in tax_data.get("manual_entries", []):
        val = _to_float(entry.get("value", 0))
        field = entry.get("field", "")
        target = MANUAL_FIELD_MAP.get(field)
        if target and target in summary:
            summary[target] += val

    # Include bank transaction data
    bank_deposits = 0.0
    bank_expenses = 0.0
    bank_txn_count = 0
    for txn in tax_data.get("plaid_transactions", []):
        amount = _to_float(txn.get("amount", 0))
        bank_txn_count += 1
        if amount < 0:
            bank_deposits += abs(amount)
        else:
            bank_expenses += amount

    summary["bank_deposits"] = bank_deposits
    summary["bank_expenses"] = bank_expenses
    summary["bank_txn_count"] = bank_txn_count
    summary["bank_accounts_connected"] = len(tax_data.get("plaid_items", []))

    # Computed fields
    summary["total_income"] = (
        summary["total_employment_income"]
        + summary["total_interest_income"]
        + summary["total_eligible_dividends"]
        + summary["total_self_employment"]
        + summary["total_pension_income"]
        + summary["total_ei_benefits"]
        + summary["total_rrsp_withdrawals"]
        + summary["total_capital_gains"]
        + summary["total_other_income"]
        + summary["total_us_wages"]
        + summary["total_us_freelance"]
    )
    summary["total_deductions"] = (
        summary["total_rrsp_contributions"]
        + summary["total_union_dues"]
    )
    # Tuition credit (15% federal)
    summary["tuition_credit"] = summary["total_tuition"] * 0.15

    return summary


def _to_float(val) -> float:
    """Safely convert a value to float."""
    if val is None:
        return 0.0
    try:
        if isinstance(val, str):
            val = val.replace(",", "").replace("$", "").strip()
        return float(val)
    except (ValueError, TypeError):
        return 0.0

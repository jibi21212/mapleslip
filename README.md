# mapleslip

> A Canada-first local desktop app that gathers your tax slips, estimates your refund, and spits out a cheat sheet for filing — all on your machine, no cloud, no subscriptions.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

---

## What it does

mapleslip ingests Canadian tax slips (T4, T5, T3, T4A, T2202, RRSP receipts, etc.) from PDFs, emails, or your Downloads folder, parses the boxes automatically, and gives you a live estimate of your refund — including a one-click T1 line-by-line cheat sheet PDF you take into Wealthsimple Tax / TurboTax / etc. when it's time to actually file.

**The "braindead" loop:**

1. Slips land in your Downloads folder (from email, your bank's portal, your school, whatever)
2. The app's **watch folder** detects them and auto-imports + auto-parses
3. The **dashboard** updates with a live refund estimate (2024 brackets, all provinces)
4. When April comes around → click **Export Cheat Sheet PDF** → type the numbers into your filing software → done

---

## Features

### 📄 Document handling
- **Auto-detection + parsing** of T4, T4A, T4E, T4RSP, T5, T3, T2202, RRSP receipts
- US forms also supported (W-2, 1099-INT/DIV/NEC/MISC, 1098/T/E) for cross-border scenarios
- **OCR fallback** via Tesseract for scanned/photographed PDFs
- **Watch folder** — point at Downloads, new PDFs auto-import

### 📧 Email scanner (Gmail OAuth)
- Browser-based OAuth login — **no passwords required**, just click "Connect Gmail Account"
- **Multiple accounts** supported — connect as many as you need (personal, school, etc.)
- **Tax-year filtered** — only shows slips matching the selected tax year (Gmail's full-text search + date range filter + per-result year verification)
- One-click import of PDF attachments
- Tokens stored locally in your `data/config.json` (gitignored); access can be revoked at any time

### 🏦 Bank integration (Plaid, free tier)
- Connect bank accounts via Plaid Link (OAuth flow, your credentials never touch this app)
- Pull transactions for any tax year
- Auto-categorized deposits and expenses
- **Free** using Plaid's Development environment (up to 100 connections)

### 💰 Tax estimation
- Live refund/owing estimate using 2024 federal + provincial brackets
- All 13 provinces/territories supported (ON, BC, AB, SK, MB, QC, NB, NS, PE, NL, YT, NT, NU)
- Handles dividend gross-up, capital gains inclusion, RRSP deduction, BPA phaseout, self-employment CPP
- Shows your marginal tax rate

### 📋 T1 cheat sheet PDF
- One-click export
- Every value mapped to its T1 line number (Line 10100, 12000, 20800, etc.)
- Slip inventory and important deadlines included
- Drop the numbers straight into Wealthsimple Tax / TurboTax / StudioTax / UFile

### 🗓 Deadline tracking
- RRSP contribution deadline
- Tax filing deadline (April 30)
- Self-employed filing deadline (June 15)
- Color-coded by urgency

### 💡 Tax tips & education
- Plain-English explanations for every form field
- General Canadian tax tips (RRSP vs TFSA, BPA, medical expenses, moving deductions, etc.)
- Form reference guide

---

## Installation

### Prerequisites
- **Python 3.11+**
- **Tesseract OCR** (optional, only needed for scanned PDFs)
  - Windows: `winget install UB-Mannheim.TesseractOCR`
  - macOS: `brew install tesseract`
  - Linux: `sudo apt install tesseract-ocr`

### Setup

```bash
git clone https://github.com/jibi21212/mapleslip.git
cd mapleslip
pip install -r requirements.txt
python run.py
```

That's it. The app creates a `data/` folder on first run to store your tax info locally.

---

## Configuration

### Plaid (optional — for bank account integration)
1. Sign up at [dashboard.plaid.com](https://dashboard.plaid.com) (free)
2. Grab your `client_id` and `secret`
3. In the app → **Bank Accounts** tab → **Plaid Settings** → paste them in
4. Use the **Development** environment (free, real banks, up to 100 connections)

### Gmail (for email scanner)
The app's "Connect Gmail Account" button uses developer-shipped OAuth credentials. If those credentials are bundled with your install, just click the button — browser opens, you log in once, and you can connect multiple Gmail accounts after that.

If you're running mapleslip from a public clone and the Gmail integration shows as **Unavailable**, the developer credentials file (`data/.dev_credentials.json`) is missing. See [HANDOFF.md](HANDOFF.md#dev-side-credentials-datadev_credentialsjson) for how to create your own.

### Watch folder
**Settings** (top right) → enter folder path (e.g. `C:\Users\You\Downloads`) → enable.

---

## Tech stack

| Layer | Tech |
|---|---|
| GUI | CustomTkinter (modern dark theme over Tkinter) |
| PDF parsing | pdfplumber + pypdfium2 |
| OCR fallback | pytesseract + Tesseract |
| Email | Gmail API + OAuth2 (google-auth, google-api-python-client) |
| Bank API | Plaid (free tier) |
| PDF generation | reportlab |
| Storage | Local JSON files |

---

## Project structure

```
mapleslip/
├── run.py                      # Launcher
├── requirements.txt
├── src/
│   ├── app.py                  # Main GUI + tab logic
│   ├── parser.py               # PDF parsing for all form types
│   ├── tax_calculator.py       # 2024 federal + provincial bracket math
│   ├── tax_tips.py             # Field explanations + general tips
│   ├── storage.py              # JSON persistence + summary calculation
│   ├── config.py               # App settings (Plaid keys, province, watch folder)
│   ├── deadlines.py            # Tax deadline calculations
│   ├── pdf_export.py           # T1 cheat-sheet PDF generator
│   ├── watch_folder.py         # Auto-import polling
│   ├── email_scanner.py        # Gmail OAuth + Gmail API scanner
│   ├── plaid_integration.py    # Plaid API client + OAuth flow
│   └── plaid_link.html         # Plaid Link OAuth landing page
└── data/                       # User data (gitignored — your tax info stays local)
```

---

## Privacy

Everything runs **locally** on your machine.

- Tax slips, parsed data, and config live in the `data/` folder on your disk (never synced)
- Plaid and Google (Gmail API) are external services, opt-in only
- Gmail OAuth tokens are stored locally in `data/config.json` — revocable at any time from the app or from your Google Account settings
- The `data/` folder is `.gitignored` — your tax info will never accidentally end up on GitHub

---

## Disclaimer

mapleslip is **not** professional tax advice. The refund estimate is a rough calculation using simplified rules and 2024 brackets — your actual return may differ. Always verify with CRA-certified tax software (Wealthsimple Tax, TurboTax, StudioTax, UFile) or a tax professional before filing.

---

## License

MIT — see [LICENSE](LICENSE).

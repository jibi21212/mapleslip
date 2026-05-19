# HANDOFF — mapleslip

> **Read this first if you're a new Claude Code session picking up this project.**
> It captures the conversation history, design decisions, current state, and pending ideas — everything you need to continue without asking the user to re-explain.

---

## Who the user is

- **Canadian intern** based in Canada
- Building this for **personal use first** but also publishing publicly on GitHub
- Strong preference for **Canada-first** UX (T4 not W-2, CRA not IRS, CAD not USD)
- US forms are supported as a secondary feature for cross-border scenarios
- Wants things to be **"braindead"** — minimal manual work, maximum automation
- GitHub username: `jibi21212`
- Repo URL: `https://github.com/jibi21212/mapleslip` (public, MIT)

## ⚠️ Critical UX preference: developer setup goes in CHAT, not in the app

When a feature requires the developer (= the user) to do a **one-time setup** like registering an OAuth app, getting API keys, etc.:

- **DO** tell them the setup steps in chat
- **DO** bake the credentials into a gitignored dev-credentials file
- **DO** treat the setup work as "already done by the developer" from the app's perspective
- **DO NOT** add setup UI screens to the app where each user is expected to do the dev work
- **DO NOT** make the in-app onboarding ask for client_ids, API keys, etc. that came from the developer's account

The mistake to avoid: building an OAuth Setup dialog where each end user has to register their own Google Cloud project. The app should ship with the credentials baked in (via gitignored dev file) and end users just click "Connect Gmail" → it works.

Note: Plaid is **per-user** credentials (each user uses their OWN Plaid account, since it's a banking integration). Google OAuth is **developer-shipped** credentials (one project, shared across all end users, subject to Google's 100-test-user limit for unverified apps). This distinction matters when building integrations.

---

## What this project is

A local desktop GUI app (CustomTkinter, Python) that:
1. Ingests Canadian tax slips (T4, T5, T3, T4A, T2202, RRSP receipts, T4E, T4RSP) from PDFs
2. Parses the boxes automatically using regex over pdfplumber-extracted text (with Tesseract OCR fallback)
3. Pulls slips from email via IMAP and from Plaid bank API
4. Calculates an estimated refund using 2024 federal + provincial tax brackets (all 13 provinces)
5. Exports a one-page T1 cheat-sheet PDF the user takes into Wealthsimple Tax / TurboTax to actually file
6. Auto-imports PDFs from a configured "watch folder" (e.g. Downloads)
7. Stores everything **locally** in `data/` (gitignored)

It does NOT actually file taxes — submitting a return requires CRA certification which is infeasible for a personal project.

---

## Tech stack

| Layer | Tech | Why |
|---|---|---|
| GUI | CustomTkinter | Modern dark-theme overlay on Tkinter, no Electron overhead |
| PDF text extraction | pdfplumber | Reliable for digitally-generated PDFs |
| PDF → image (for OCR) | pypdfium2 | Bundled with pdfplumber, no extra deps |
| OCR | pytesseract + Tesseract binary | Free, local, no API |
| Email | `imaplib` (stdlib) | No third-party API needed, works with all major providers |
| Bank API | Plaid (Development env, free) | Only realistic option; user has explicitly approved this |
| PDF generation | reportlab | Standard for Python PDF gen |
| Storage | Plain JSON files | No DB needed for personal use |

---

## File structure

```
mapleslip/
├── run.py                       # Entrypoint — adds src/ to path and calls app.main()
├── requirements.txt
├── README.md                    # Public-facing
├── HANDOFF.md                   # ← You are here
├── LICENSE                      # MIT
├── .gitignore                   # Excludes data/, __pycache__, etc.
├── src/
│   ├── app.py                   # Main GUI class TaxKingApp(ctk.CTk)
│   ├── parser.py                # PDF parsing — form detection + per-form regex parsers
│   ├── tax_calculator.py        # 2024 brackets, BPA, credits, refund calc
│   ├── tax_tips.py              # FORM_TIPS (per-field tooltips) + GENERAL_TIPS
│   ├── storage.py               # load/save tax_data.json + get_summary()
│   ├── config.py                # load/save config.json (Plaid keys, province, watch folder)
│   ├── deadlines.py             # RRSP/filing/SE deadlines for a given tax year
│   ├── pdf_export.py            # T1 cheat-sheet PDF generator (reportlab)
│   ├── watch_folder.py          # Polls a folder every 5s for new PDFs
│   ├── email_scanner.py         # IMAP scanner for tax slips
│   ├── plaid_integration.py     # Plaid API client + local OAuth HTTP server
│   └── plaid_link.html          # Plaid Link OAuth landing page
└── data/                        # GITIGNORED — user data lives here
    ├── tax_data.json            # All parsed slips, manual entries, Plaid items + access tokens
    ├── config.json              # Plaid client_id/secret, province, watch folder path
    ├── documents/               # Copies of uploaded/auto-imported PDFs
    └── parsed/                  # Reserved (currently unused)
```

---

## Key design decisions

### Why CustomTkinter over Electron/web
User explicitly wanted "a local GUI type app" — not a webapp. CustomTkinter gives a modern dark UI with no browser runtime overhead.

### Why local JSON over a database
Personal use, one user, no concurrency. JSON is human-readable and trivially debuggable.

### Why Plaid Development (not Sandbox or Production)
- Sandbox uses fake test banks — useless for real personal use
- Production costs money and requires Plaid approval
- Development is free, supports real banks, capped at 100 connections — perfect for personal use

### Why Plaid Link is served from a local HTTP server
Plaid Link is a web widget. For a desktop app, the cleanest flow is:
1. App spawns a tiny `HTTPServer` on a random port
2. App opens user's browser to `http://127.0.0.1:<port>/`
3. The page (`plaid_link.html`) initializes Plaid Link with the link_token
4. On success, the page redirects to `/callback?public_token=...`
5. The server captures the token, calls a callback, and shuts down

This avoids embedding a webview in Tkinter (painful) or requiring an external browser auth flow.

### Why Gmail API + OAuth (current — replaced IMAP)
- **User feedback**: didn't want to type passwords/IMAP servers, wanted a "log in via browser" flow like Plaid
- Gmail's `q` search parameter is much more powerful than IMAP search (proper date filtering, full-text)
- Tokens are persistent (refresh token), so the user authenticates once and the app uses it forever
- Tradeoff: **Gmail-only** for now (Outlook would need a separate Microsoft Graph OAuth integration)
- Tradeoff: **user must do a one-time Google Cloud Console setup** (~5 min) to get their own OAuth client_id/secret. This is unavoidable for a desktop OAuth app — Google requires app registration. The app provides step-by-step instructions in the OAuth Setup dialog.

The previous IMAP+password code is gone. If we ever want to support non-Gmail providers, we should add separate OAuth integrations (Microsoft Graph for Outlook, Yahoo's OAuth, etc.) — NOT bring IMAP back.

### Why we don't actually file taxes
Filing via NETFILE requires being a CRA-certified tax software vendor. Not feasible for a personal project. The cheat-sheet PDF is the closest substitute — the user types those numbers into Wealthsimple Tax (which is CRA-certified and free) to file.

---

## Current state (what's done)

All of these are working and tested:

- [x] PDF upload with auto-detection of form type
- [x] Parsers for: T4, T4A, T4E, T4RSP, T5, T3, T2202, RRSP receipts, W-2, 1099-INT/DIV/NEC/MISC, 1098, 1098-T, 1098-E
- [x] Tesseract OCR fallback for scanned PDFs (auto-detects Tesseract on Windows at default install path)
- [x] Gmail email scanner via OAuth2 (browser-based auth, no passwords). Supports multiple accounts. Filters slips by tax year using Gmail's `q` search parameter + per-result year verification.
- [x] Plaid integration — Connect Bank flow, pull transactions, view accounts
- [x] Manual entry for any form/field
- [x] Tax tips: 11 general + per-form-field tooltips
- [x] Dashboard with sectioned summary (Income, Deductions at Source, Deductions & Credits, Education, Banking, Alerts)
- [x] **Refund/owing estimate** with 2024 brackets for all 13 provinces
- [x] **T1 cheat-sheet PDF export** — line-by-line by T1 number
- [x] **Deadline reminders** (RRSP, filing, SE filing) — color-coded by urgency
- [x] **Watch folder** auto-import (polls every 5s)
- [x] Province selector in header
- [x] Settings dialog for Plaid keys, province, and watch folder

---

## How `tax_data.json` is structured

```json
{
  "tax_year": 2024,
  "documents": [
    {
      "id": "20250318143022123456",
      "form_type": "t4",
      "original_name": "T4_Shopify_2024.pdf",
      "stored_path": "data/documents/20250318_143022_T4_Shopify_2024.pdf",
      "parsed_data": {
        "employer_name": "Shopify Inc.",
        "employment_income": "65000.00",
        "income_tax_deducted": "12000.00",
        "cpp_contributions": "3500.00",
        "ei_premiums": "1000.00"
      },
      "date_added": "2025-03-18T14:30:22"
    }
  ],
  "manual_entries": [
    { "id": "...", "form_type": "t4", "field": "employment_income", "value": 5000, "label": "Side gig" }
  ],
  "plaid_items": [
    {
      "item_id": "...",
      "access_token": "access-development-...",
      "accounts": [ { "account_id": "...", "name": "Chequing", "mask": "0123", "balance_current": 1234.56 } ],
      "date_connected": "..."
    }
  ],
  "plaid_transactions": [
    { "transaction_id": "...", "date": "2024-06-15", "name": "...", "amount": -2500.00, "category": [...] }
  ]
}
```

**The `parsed_data` values are strings from regex extraction.** `storage._to_float()` handles conversion.

---

## How form parsing works

1. `parser.extract_text_from_pdf(filepath)` — tries pdfplumber first; if it gets < 50 chars, falls back to OCR (pypdfium2 renders pages at 300 DPI → pytesseract)
2. `parser.detect_form_type(text)` — keyword matching to identify form type (e.g. "T4" + "STATEMENT OF REMUNERATION" → "t4"). Canadian forms checked first.
3. `parser.PARSERS[form_type](text)` — form-specific function that uses `_find_dollar_amount()` and `_find_text_field()` regex helpers to extract each box

The regex patterns are forgiving — they accept variations like "Box 14", "box 14", "14 Employment", and the French equivalents where applicable.

---

## How the refund estimate works (`tax_calculator.py`)

1. Start with `total_income` from the summary
2. Gross up eligible dividends by 38% (T5 Box 25 conversion)
3. Apply 50% inclusion to capital gains
4. Subtract deductions (RRSP, RPP, union dues)
5. Apply 2024 federal brackets → federal tax
6. Apply federal non-refundable credits (BPA, CPP, EI, tuition at 15%) and dividend tax credit
7. Apply provincial brackets (province from `config.province`) → provincial tax
8. Apply provincial credits at the province's lowest bracket rate
9. Add self-employment CPP (11.9% on net SE income > $3,500)
10. Compare total tax to `total_income_tax_deducted` (Box 22 of T4s)
11. Difference = refund (positive) or owing (negative)

**Limitations** (documented as "estimate" in the UI):
- Doesn't handle complex situations (spousal transfers, foreign tax credits, AMT, etc.)
- Provincial dividend tax credit is a rough average across provinces (10%)
- Capital gains uses pre-June-25-2024 rules (50% inclusion across the board)
- BPA is the only deduction credit modeled (no medical expenses, donations, age amount, etc.)
- 2024 brackets only — no historical years

---

## Pending ideas (not yet built)

Ranked by impact / effort:

### Easy + high impact
- **Drag-and-drop PDF upload** — drag a PDF onto the window instead of clicking Upload (not done yet)
- **Year-over-year comparison** — side-by-side 2023 vs 2024; catches missing slips
- **Slip expectation checklist** — based on last year's slips, show what's expected this year
- **Receipt scanner for medical/charitable** — OCR on receipts → auto-categorize for deduction
- **Drag-and-drop on Documents tab** — same as above scoped to one tab

### Medium effort
- **Auto-categorize bank transactions** — tag Plaid txns as charitable, medical, etc. for deduction surfacing
- **Quebec Relevé support** — RL-1, RL-3, RL-31 parsers
- **Spouse/family mode** — add a partner, optimize who claims medical/donations
- **Local AI chat assistant** — "How much did I make?" via Ollama or Claude API (user already has Claude available)
- **2023 / 2025 brackets** — generalize `tax_calculator.py` to multi-year

### Hard / has catches
- **CRA Auto-fill My Return** — the holy grail; not feasible without CRA certification
- **NETFILE filing** — same problem
- **Browser automation for issuer portals** — fragile, breaks on 2FA, against TOS

---

## Known issues / things to watch

1. **T4 parser is brittle on weird layouts** — Some employer payroll systems output T4s with non-standard layouts that confuse the regex. Look at `parse_t4()` in `parser.py` if extraction fails. Test by uploading + manually checking the values.

2. **OCR is slow on multi-page scans** — 300 DPI rendering + Tesseract takes a few seconds per page. Not a bug but worth knowing.

3. **Plaid Development tokens don't expire automatically** but they CAN be invalidated if Plaid pushes account-link-update events. If a token errors out, user has to reconnect that bank.

4. **Watch folder polls every 5 seconds** — uses `tk.after()`, not OS file system events. Could be faster but more dependencies. Fine for current use.

5. **Email scanner is keyword-based** — won't catch slips whose subjects don't include obvious keywords (T4, T5, tax, etc.). Could be improved by adding sender heuristics (banks, employers).

6. **Tax data file isn't encrypted** — Plaid access tokens are in plaintext JSON. Acceptable for personal use on a personal machine but worth noting.

---

## How to set this up on a fresh machine

```bash
git clone https://github.com/jibkh21212/mapleslip.git
cd mapleslip
pip install -r requirements.txt

# Optional: install Tesseract for OCR support
# Windows: winget install UB-Mannheim.TesseractOCR
# macOS: brew install tesseract

python run.py
```

On first run, the app creates a `data/` folder. The user enters Plaid keys in **Bank Accounts > Plaid Settings** (if they want bank integration) and sets their province + watch folder in **Settings** (top right of header).

## Dev-side credentials (`data/.dev_credentials.json`)

This file is **developer-shipped** and gitignored. Its purpose is to hold OAuth client credentials for services the developer registered ONCE (not per-user). End users never touch this file or see anything about it in the app — they just click "Connect Gmail" and it works.

**File location**: `data/.dev_credentials.json`

**Schema**:
```json
{
  "google_client_id": "xxxxx.apps.googleusercontent.com",
  "google_client_secret": "GOCSPX-xxxxx"
}
```

**How to create it** (one-time, ~5 minutes):

1. Sign in to https://console.cloud.google.com with your Google account
2. Top bar → "Select a project" → "New Project" → name it (e.g. `mapleslip`) → Create
3. Top search bar → "Gmail API" → click it → **Enable**
4. Left menu → **APIs & Services** → **OAuth consent screen**
   - User type: **External** → Create
   - App name: `mapleslip`, user support email: your email
   - Developer contact: your email
   - Skip the Scopes screen (Save and Continue)
   - On "Test users" screen, click **+ Add Users** and add the Gmail addresses of anyone who will use the app (up to 100). **Including your own.**
   - Save and Continue, then Back to Dashboard
5. Left menu → **APIs & Services** → **Credentials**
   - **+ Create Credentials** → **OAuth client ID**
   - Application type: **Desktop app**
   - Name: `mapleslip-desktop`
   - Click Create → a popup shows the client ID and client secret
6. Copy both into `data/.dev_credentials.json` using the schema above

**After this is done**, the "Connect Gmail Account" button in the app just works. End users will see Google's "This app isn't verified" warning during the OAuth consent step — they click "Advanced" → "Go to mapleslip (unsafe)" → proceed normally. This is unavoidable for unverified apps. To remove the warning, the developer would need to go through Google's verification process (sensitive scopes like Gmail readonly require a CASA security assessment — not feasible for a personal project).

**For the public GitHub repo**: this file is gitignored, so neither the developer's credentials nor end-user data ends up on GitHub. Anyone who clones the public repo would need to either:
- Get the `.dev_credentials.json` file from the developer privately, OR
- Create their own Google Cloud project and credentials following the steps above

The app silently shows "Gmail integration: Unavailable" if the file is missing — no setup screens, no nagging.

---

## Conversation history summary (chronological)

1. User asked for a local tax helper app
2. Built the MVP: CustomTkinter GUI with Dashboard, Documents, Manual Entry, Tax Tips tabs. PDF upload + parsing via pdfplumber. Originally US-focused (W-2, 1099, etc.)
3. User asked about OCR for scanned PDFs → added pytesseract + pypdfium2 fallback; installed Tesseract via winget
4. User asked about bank API → explained Plaid; user approved free tier; implemented Plaid integration with local OAuth server, Connect Bank flow, transaction pulling
5. User asked about email integration for T4s → revealed user is **Canadian**; added IMAP email scanner + **completely rebuilt the app for Canadian tax context** (T4, T5, T3, T4A, T2202, RRSP, etc.); kept US forms as secondary
6. User asked "what could make this more braindead" → built the four-feature package:
   - Refund estimator (2024 brackets, all 13 provinces)
   - T1 cheat-sheet PDF export
   - Deadline reminders on dashboard
   - Watch folder for auto-import from Downloads
7. User said "push to GitHub" → repo created at github.com/jibi21212/mapleslip (public, MIT)
8. User tried the app and gave feedback:
   - "Why do we need to give our email password and imap server?" → **dropped IMAP entirely, replaced with Gmail OAuth** (browser-based flow like Plaid)
   - "Do we double check the slips are from the correct tax year?" → **fixed broken filter**, now uses Gmail's `q` search with `after:`/`before:` date range + per-result year verification from subject + email date
   - "Can we attach more than 1 email?" → **multiple Gmail accounts** now supported. Config stores a list. UI shows each connected account with individual Scan and Remove buttons, plus a top-level Scan All.

The user's overall vision: an app that turns "doing your taxes" into "open the app in April, click one button, copy the numbers."

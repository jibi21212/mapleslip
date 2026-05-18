"""PDF parsing for common tax forms using pdfplumber with OCR fallback."""

import re
import shutil
import sys
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import pytesseract
    from PIL import Image
    HAS_OCR = True

    # On Windows, Tesseract is often installed here but not on PATH
    _default_win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if sys.platform == "win32" and shutil.which("tesseract") is None:
        if Path(_default_win_path).exists():
            pytesseract.pytesseract.tesseract_cmd = _default_win_path
except ImportError:
    HAS_OCR = False

# pypdfium2 ships with pdfplumber — used to render PDF pages to images for OCR
try:
    import pypdfium2 as pdfium
    HAS_PDFIUM = True
except ImportError:
    HAS_PDFIUM = False


def _tesseract_available() -> bool:
    """Check if the Tesseract binary is installed and reachable."""
    if not HAS_OCR:
        return False
    # Check if pytesseract has a custom path set that exists
    cmd = getattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")
    if cmd != "tesseract" and Path(cmd).exists():
        return True
    return shutil.which("tesseract") is not None


def _ocr_pdf(filepath: str) -> str:
    """Convert PDF pages to images via pypdfium2, then OCR with Tesseract."""
    if not HAS_PDFIUM or not _tesseract_available():
        return ""

    text = ""
    pdf = pdfium.PdfDocument(filepath)
    for i in range(len(pdf)):
        page = pdf[i]
        # Render at 300 DPI for good OCR accuracy
        bitmap = page.render(scale=300 / 72)
        pil_image = bitmap.to_pil()
        page_text = pytesseract.image_to_string(pil_image)
        if page_text:
            text += page_text + "\n"
    pdf.close()
    return text


def extract_text_from_pdf(filepath: str) -> str:
    """Extract text from a PDF file.

    Strategy:
      1. Try pdfplumber (fast, accurate for digital/text-based PDFs).
      2. If pdfplumber returns little or no text, fall back to OCR
         (pypdfium2 renders pages to images, pytesseract runs Tesseract).
    """
    text = ""

    # Step 1: Try pdfplumber for text-layer extraction
    if pdfplumber is not None:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

    # Step 2: If we got very little text, try OCR
    if len(text.strip()) < 50:
        ocr_text = _ocr_pdf(filepath)
        if len(ocr_text.strip()) > len(text.strip()):
            text = ocr_text

    return text


def detect_form_type(text: str) -> str:
    """Detect the tax form type from extracted text."""
    text_upper = text.upper()

    # ── Canadian forms (check first — primary user is Canadian) ──
    if "T2202" in text_upper or "TUITION AND ENROLMENT" in text_upper:
        return "t2202"
    if "T4RSP" in text_upper or ("RRSP" in text_upper and "INCOME" in text_upper and "T4" in text_upper):
        return "t4rsp"
    if "T4E" in text_upper and ("EMPLOYMENT INSURANCE" in text_upper or "EI BENEFITS" in text_upper):
        return "t4e"
    if "T4A" in text_upper or ("PENSION" in text_upper and "RETIREMENT" in text_upper and "ANNUITY" in text_upper):
        return "t4a"
    if ("T4" in text_upper and "STATEMENT OF REMUNERATION" in text_upper) or \
       ("T4" in text_upper and "EMPLOYMENT INCOME" in text_upper and "CPP" in text_upper):
        return "t4"
    if "T5" in text_upper and ("INVESTMENT INCOME" in text_upper or "DIVIDENDS" in text_upper and "INTEREST" in text_upper):
        return "t5"
    if "T3" in text_upper and ("TRUST" in text_upper or "MUTUAL FUND" in text_upper):
        return "t3"
    if "RRSP" in text_upper and ("CONTRIBUTION" in text_upper or "RECEIPT" in text_upper):
        return "rrsp_receipt"

    # ── US forms ──
    if "1098-T" in text_upper or "TUITION STATEMENT" in text_upper:
        return "1098_t"
    if "1098-E" in text_upper or "STUDENT LOAN INTEREST" in text_upper:
        return "1098_e"
    if "1098" in text_upper and "MORTGAGE" in text_upper:
        return "1098"
    if "1099-NEC" in text_upper or "NONEMPLOYEE COMPENSATION" in text_upper:
        return "1099_nec"
    if "1099-INT" in text_upper or ("1099" in text_upper and "INTEREST INCOME" in text_upper):
        return "1099_int"
    if "1099-DIV" in text_upper or ("1099" in text_upper and "DIVIDENDS" in text_upper):
        return "1099_div"
    if "1099-MISC" in text_upper or "MISCELLANEOUS INCOME" in text_upper:
        return "1099_misc"
    if "W-2" in text_upper or "WAGE AND TAX STATEMENT" in text_upper:
        return "w2"

    return "unknown"


def _find_dollar_amount(text: str, patterns: list[str]) -> str:
    """Find a dollar amount near a label pattern in text."""
    for pattern in patterns:
        # Look for the pattern followed by a dollar amount
        regex = pattern + r"[\s:]*\$?([\d,]+\.?\d*)"
        match = re.search(regex, text, re.IGNORECASE)
        if match:
            return match.group(1).replace(",", "")
    return ""


def _find_text_field(text: str, patterns: list[str]) -> str:
    """Find a text field near a label pattern."""
    for pattern in patterns:
        regex = pattern + r"[\s:]*([A-Za-z0-9\s\.,&'-]+?)(?:\n|$)"
        match = re.search(regex, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def parse_w2(text: str) -> dict:
    """Parse W-2 fields from extracted text."""
    return {
        "employer_name": _find_text_field(text, [
            r"employer.?s?\s+name",
            r"c\s+employer",
        ]),
        "wages_tips": _find_dollar_amount(text, [
            r"wages,?\s*tips",
            r"box\s*1\b",
            r"1\s+wages",
        ]),
        "federal_tax_withheld": _find_dollar_amount(text, [
            r"federal\s+income\s+tax\s+withheld",
            r"box\s*2\b",
            r"2\s+federal",
        ]),
        "social_security_wages": _find_dollar_amount(text, [
            r"social\s+security\s+wages",
            r"box\s*3\b",
            r"3\s+social",
        ]),
        "social_security_tax": _find_dollar_amount(text, [
            r"social\s+security\s+tax\s+withheld",
            r"box\s*4\b",
            r"4\s+social",
        ]),
        "medicare_wages": _find_dollar_amount(text, [
            r"medicare\s+wages",
            r"box\s*5\b",
            r"5\s+medicare",
        ]),
        "medicare_tax": _find_dollar_amount(text, [
            r"medicare\s+tax\s+withheld",
            r"box\s*6\b",
            r"6\s+medicare",
        ]),
        "state_wages": _find_dollar_amount(text, [
            r"state\s+wages",
            r"box\s*16\b",
            r"16\s+state",
        ]),
        "state_tax_withheld": _find_dollar_amount(text, [
            r"state\s+income\s+tax",
            r"box\s*17\b",
            r"17\s+state",
        ]),
    }


def parse_1099_int(text: str) -> dict:
    """Parse 1099-INT fields from extracted text."""
    return {
        "payer_name": _find_text_field(text, [r"payer.?s?\s+name", r"name\s+of\s+payer"]),
        "interest_income": _find_dollar_amount(text, [
            r"interest\s+income",
            r"box\s*1\b",
            r"1\s+interest",
        ]),
        "early_withdrawal_penalty": _find_dollar_amount(text, [
            r"early\s+withdrawal\s+penalty",
            r"box\s*2\b",
        ]),
        "federal_tax_withheld": _find_dollar_amount(text, [
            r"federal\s+income\s+tax\s+withheld",
            r"box\s*4\b",
        ]),
    }


def parse_1099_div(text: str) -> dict:
    """Parse 1099-DIV fields from extracted text."""
    return {
        "payer_name": _find_text_field(text, [r"payer.?s?\s+name", r"name\s+of\s+payer"]),
        "ordinary_dividends": _find_dollar_amount(text, [
            r"total\s+ordinary\s+dividends",
            r"box\s*1a\b",
            r"1a\s+total",
        ]),
        "qualified_dividends": _find_dollar_amount(text, [
            r"qualified\s+dividends",
            r"box\s*1b\b",
            r"1b\s+qualified",
        ]),
        "capital_gains": _find_dollar_amount(text, [
            r"total\s+capital\s+gain",
            r"box\s*2a\b",
        ]),
        "federal_tax_withheld": _find_dollar_amount(text, [
            r"federal\s+income\s+tax\s+withheld",
            r"box\s*4\b",
        ]),
    }


def parse_1099_nec(text: str) -> dict:
    """Parse 1099-NEC fields from extracted text."""
    return {
        "payer_name": _find_text_field(text, [r"payer.?s?\s+name", r"name\s+of\s+payer"]),
        "nonemployee_compensation": _find_dollar_amount(text, [
            r"nonemployee\s+compensation",
            r"box\s*1\b",
            r"1\s+nonemployee",
        ]),
        "federal_tax_withheld": _find_dollar_amount(text, [
            r"federal\s+income\s+tax\s+withheld",
            r"box\s*4\b",
        ]),
    }


def parse_1099_misc(text: str) -> dict:
    """Parse 1099-MISC fields from extracted text."""
    return {
        "payer_name": _find_text_field(text, [r"payer.?s?\s+name", r"name\s+of\s+payer"]),
        "rents": _find_dollar_amount(text, [r"rents", r"box\s*1\b"]),
        "royalties": _find_dollar_amount(text, [r"royalties", r"box\s*2\b"]),
        "other_income": _find_dollar_amount(text, [r"other\s+income", r"box\s*3\b"]),
        "federal_tax_withheld": _find_dollar_amount(text, [
            r"federal\s+income\s+tax\s+withheld",
            r"box\s*4\b",
        ]),
    }


def parse_1098(text: str) -> dict:
    """Parse 1098 (mortgage) fields from extracted text."""
    return {
        "lender_name": _find_text_field(text, [r"recipient.?s?\s+name", r"lender"]),
        "mortgage_interest": _find_dollar_amount(text, [
            r"mortgage\s+interest\s+received",
            r"box\s*1\b",
        ]),
        "points_paid": _find_dollar_amount(text, [
            r"points\s+paid",
            r"box\s*6\b",
        ]),
    }


def parse_1098_t(text: str) -> dict:
    """Parse 1098-T (tuition) fields from extracted text."""
    return {
        "school_name": _find_text_field(text, [r"filer.?s?\s+name", r"institution"]),
        "tuition_paid": _find_dollar_amount(text, [
            r"payments\s+received",
            r"qualified\s+tuition",
            r"box\s*1\b",
        ]),
        "scholarships": _find_dollar_amount(text, [
            r"scholarships\s+or\s+grants",
            r"box\s*5\b",
        ]),
    }


def parse_1098_e(text: str) -> dict:
    """Parse 1098-E (student loan interest) fields from extracted text."""
    return {
        "lender_name": _find_text_field(text, [r"recipient.?s?\s+name", r"lender"]),
        "interest_paid": _find_dollar_amount(text, [
            r"student\s+loan\s+interest\s+received",
            r"box\s*1\b",
        ]),
    }


# ═══════════════════════════════════════════════════════════════════
#  CANADIAN FORM PARSERS
# ═══════════════════════════════════════════════════════════════════

def parse_t4(text: str) -> dict:
    """Parse T4 — Statement of Remuneration Paid."""
    return {
        "employer_name": _find_text_field(text, [
            r"employer.?s?\s+name", r"name\s+of\s+employer", r"nom\s+de\s+l.?employeur",
        ]),
        "employment_income": _find_dollar_amount(text, [
            r"employment\s+income", r"box\s*14\b", r"14\s+employment",
            r"revenus?\s+d.?emploi",
        ]),
        "income_tax_deducted": _find_dollar_amount(text, [
            r"income\s+tax\s+deducted", r"box\s*22\b", r"22\s+income\s+tax",
            r"imp.t\s+sur\s+le\s+revenu\s+retenu",
        ]),
        "cpp_contributions": _find_dollar_amount(text, [
            r"employee.?s?\s+cpp\s+contributions?", r"box\s*16\b",
            r"cotisations?\s+de\s+l.?employ.\s+au\s+rpc",
        ]),
        "cpp2_contributions": _find_dollar_amount(text, [
            r"second\s+cpp\s+contributions?", r"box\s*16a\b", r"cpp2",
        ]),
        "ei_premiums": _find_dollar_amount(text, [
            r"employee.?s?\s+ei\s+premiums?", r"box\s*18\b",
            r"cotisations?\s+de\s+l.?employ.\s+.?\s+l.?ae",
        ]),
        "rpp_contributions": _find_dollar_amount(text, [
            r"rpp\s+contributions?", r"box\s*20\b",
            r"cotisations?\s+.?\s+un\s+rpa",
        ]),
        "union_dues": _find_dollar_amount(text, [
            r"union\s+dues", r"box\s*44\b", r"cotisations?\s+syndicales?",
        ]),
    }


def parse_t4a(text: str) -> dict:
    """Parse T4A — Pension, Retirement, Annuity, and Other Income."""
    return {
        "payer_name": _find_text_field(text, [
            r"payer.?s?\s+name", r"name\s+of\s+payer",
        ]),
        "pension_income": _find_dollar_amount(text, [
            r"pension\s+or\s+superannuation", r"box\s*016\b", r"box\s*16\b",
        ]),
        "self_employed_commissions": _find_dollar_amount(text, [
            r"self.?employed\s+commissions?", r"box\s*020\b", r"box\s*20\b",
        ]),
        "fees_for_services": _find_dollar_amount(text, [
            r"fees\s+for\s+services", r"box\s*048\b", r"box\s*48\b",
        ]),
        "scholarships": _find_dollar_amount(text, [
            r"scholarships?", r"bursari", r"fellowships?", r"box\s*105\b",
        ]),
        "resp_educational": _find_dollar_amount(text, [
            r"resp\s+educational", r"box\s*042\b", r"box\s*42\b",
        ]),
        "income_tax_deducted": _find_dollar_amount(text, [
            r"income\s+tax\s+deducted", r"box\s*022\b", r"box\s*22\b",
        ]),
    }


def parse_t5(text: str) -> dict:
    """Parse T5 — Statement of Investment Income."""
    return {
        "payer_name": _find_text_field(text, [
            r"payer.?s?\s+name", r"name\s+of\s+payer",
        ]),
        "actual_dividends": _find_dollar_amount(text, [
            r"actual\s+amount\s+of\s+eligible\s+dividends?", r"box\s*10\b",
        ]),
        "taxable_dividends": _find_dollar_amount(text, [
            r"taxable\s+amount\s+of\s+eligible\s+dividends?", r"box\s*25\b",
        ]),
        "dividend_tax_credit": _find_dollar_amount(text, [
            r"dividend\s+tax\s+credit", r"box\s*26\b",
        ]),
        "interest_income": _find_dollar_amount(text, [
            r"interest\s+from\s+canadian\s+sources?", r"box\s*13\b",
        ]),
        "other_dividends": _find_dollar_amount(text, [
            r"actual\s+amount\s+of\s+other\s+dividends?",
            r"other\s+than\s+eligible\s+dividends?", r"box\s*11\b",
        ]),
        "foreign_income": _find_dollar_amount(text, [
            r"foreign\s+income", r"box\s*15\b",
        ]),
    }


def parse_t3(text: str) -> dict:
    """Parse T3 — Statement of Trust Income."""
    return {
        "trust_name": _find_text_field(text, [
            r"name\s+of\s+trust", r"trust\s+name",
        ]),
        "actual_dividends": _find_dollar_amount(text, [
            r"actual\s+eligible\s+dividends?", r"box\s*23\b",
        ]),
        "capital_gains": _find_dollar_amount(text, [
            r"capital\s+gains?", r"box\s*21\b",
        ]),
        "foreign_income": _find_dollar_amount(text, [
            r"foreign\s+non.?business\s+income", r"box\s*25\b",
        ]),
        "other_income": _find_dollar_amount(text, [
            r"other\s+income", r"box\s*26\b",
        ]),
        "return_of_capital": _find_dollar_amount(text, [
            r"return\s+of\s+capital", r"box\s*42\b",
        ]),
    }


def parse_t2202(text: str) -> dict:
    """Parse T2202 — Tuition and Enrolment Certificate."""
    return {
        "school_name": _find_text_field(text, [
            r"name\s+of\s+.*institution", r"designated\s+educational",
        ]),
        "eligible_tuition": _find_dollar_amount(text, [
            r"eligible\s+tuition\s+fees?", r"box\s*a\b",
        ]),
        "months_part_time": _find_dollar_amount(text, [
            r"part.?time\s+months?", r"box\s*b\b",
        ]),
        "months_full_time": _find_dollar_amount(text, [
            r"full.?time\s+months?", r"box\s*c\b",
        ]),
    }


def parse_rrsp_receipt(text: str) -> dict:
    """Parse RRSP Contribution Receipt."""
    return {
        "issuer_name": _find_text_field(text, [
            r"issuer", r"financial\s+institution", r"name\s+of",
        ]),
        "contribution_amount": _find_dollar_amount(text, [
            r"contribution\s+amount", r"amount\s+of\s+contribution",
            r"rrsp\s+contribution", r"montant\s+de\s+la\s+cotisation",
        ]),
    }


def parse_t4e(text: str) -> dict:
    """Parse T4E — Statement of Employment Insurance Benefits."""
    return {
        "ei_benefits": _find_dollar_amount(text, [
            r"total\s+ei\s+benefits?\s+paid", r"box\s*14\b",
            r"total\s+des\s+prestations?\s+d.?ae",
        ]),
        "income_tax_deducted": _find_dollar_amount(text, [
            r"income\s+tax\s+deducted", r"box\s*22\b",
        ]),
    }


def parse_t4rsp(text: str) -> dict:
    """Parse T4RSP — Statement of RRSP Income."""
    return {
        "withdrawal_amount": _find_dollar_amount(text, [
            r"withdrawal", r"annuity", r"box\s*22\b",
        ]),
        "income_tax_deducted": _find_dollar_amount(text, [
            r"income\s+tax\s+deducted", r"box\s*30\b",
        ]),
    }


# Map form types to their parsers
PARSERS = {
    # Canadian
    "t4": parse_t4,
    "t4a": parse_t4a,
    "t5": parse_t5,
    "t3": parse_t3,
    "t2202": parse_t2202,
    "rrsp_receipt": parse_rrsp_receipt,
    "t4e": parse_t4e,
    "t4rsp": parse_t4rsp,
    # US
    "w2": parse_w2,
    "1099_int": parse_1099_int,
    "1099_div": parse_1099_div,
    "1099_nec": parse_1099_nec,
    "1099_misc": parse_1099_misc,
    "1098": parse_1098,
    "1098_t": parse_1098_t,
    "1098_e": parse_1098_e,
}


def check_ocr_status() -> dict:
    """Check whether OCR dependencies are available."""
    tesseract_installed = _tesseract_available()
    return {
        "pytesseract": HAS_OCR,
        "pypdfium2": HAS_PDFIUM,
        "tesseract_binary": tesseract_installed,
        "ocr_ready": HAS_OCR and HAS_PDFIUM and tesseract_installed,
    }


def parse_document(filepath: str, form_type: str = None) -> tuple[str, dict]:
    """Parse a tax document. Returns (form_type, parsed_data).

    If form_type is not provided, auto-detection is attempted.
    Uses pdfplumber first, falls back to OCR for scanned documents.
    """
    text = extract_text_from_pdf(filepath)
    if not text.strip():
        status = check_ocr_status()
        if not status["ocr_ready"]:
            return (form_type or "unknown", {
                "_ocr_warning": (
                    "No text could be extracted. This may be a scanned document. "
                    "Install Tesseract OCR to enable scanned PDF support. "
                    "See the README for instructions."
                )
            })
        return (form_type or "unknown", {})

    if not form_type or form_type == "unknown":
        form_type = detect_form_type(text)

    parser = PARSERS.get(form_type)
    if parser:
        return (form_type, parser(text))

    return (form_type, {"raw_text": text[:2000]})

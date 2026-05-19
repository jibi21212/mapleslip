"""Gmail email scanner — OAuth2 only, no passwords.

Uses the Gmail API with user-granted OAuth2 access. The user authenticates
once via their browser (Plaid-Link style flow). Refresh tokens are stored
locally so the user doesn't have to re-authenticate every session.
"""

import base64
import json
import re
import threading
import webbrowser
from datetime import datetime, timedelta
from functools import partial
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode, parse_qs, urlparse

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

DATA_DIR = Path(__file__).parent.parent / "data" / "documents"

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
GMAIL_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Keywords used in the Gmail search query
TAX_KEYWORDS = [
    "T4", "T4A", "T4E", "T4RSP", "T5", "T3", "T2202",
    "RRSP",
    "tax slip", "tax form", "tax document", "tax receipt",
    "relevé", "releve",  # Quebec
    "statement of remuneration", "investment income",
    "tuition certificate",
]


# ════════════════════════════════════════════════════════════════
#  OAUTH FLOW (browser-based, Plaid Link style)
# ════════════════════════════════════════════════════════════════

class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Local HTTP server handler that catches Google's OAuth redirect."""

    def __init__(self, *args, result_holder=None, **kwargs):
        self.result_holder = result_holder
        super().__init__(*args, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            self.result_holder["code"] = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
                <html><body style="background:#1a1a2e;color:white;font-family:sans-serif;
                display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
                <div style="text-align:center;padding:40px">
                <h1>Gmail connected!</h1>
                <p style="color:#a0a0b0;font-size:16px">
                You can close this tab and return to mapleslip.</p>
                </div></body></html>
            """)
        elif "error" in params:
            self.result_holder["error"] = params["error"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
                <html><body style="background:#1a1a2e;color:white;font-family:sans-serif;
                display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
                <div style="text-align:center;padding:40px">
                <h1>Connection cancelled</h1>
                <p>You can close this tab and try again from the app.</p>
                </div></body></html>
            """)
        else:
            self.send_error(404)

        # Shut down the server after handling
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format, *args):
        pass  # suppress console output


def start_oauth_flow(client_id: str, client_secret: str,
                     on_complete) -> dict:
    """Open the user's browser to Google's OAuth consent screen and capture the result.

    Runs a local HTTP server on a random port to catch the redirect.
    Calls on_complete(credentials_dict) when done, or on_complete(None) on failure.
    """
    # Start the local callback server first so we know the port
    result_holder = {}
    handler = partial(_OAuthCallbackHandler, result_holder=result_holder)
    server = HTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    redirect_uri = f"http://127.0.0.1:{port}"

    # Build the auth URL
    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(GMAIL_SCOPES),
        "access_type": "offline",  # so we get a refresh_token
        "prompt": "consent",  # force consent to ensure refresh_token
    }
    auth_url = f"{GMAIL_AUTH_URL}?{urlencode(auth_params)}"

    # Run server in background and open browser
    def run_server():
        try:
            server.serve_forever()
        except Exception:
            pass

        if "error" in result_holder:
            on_complete(None)
            return

        code = result_holder.get("code")
        if not code:
            on_complete(None)
            return

        # Exchange code for tokens
        try:
            creds = _exchange_code_for_token(code, client_id, client_secret, redirect_uri)
            on_complete(creds)
        except Exception as e:
            on_complete(None)

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    webbrowser.open(auth_url)
    return {"port": port, "redirect_uri": redirect_uri}


def _exchange_code_for_token(code: str, client_id: str,
                              client_secret: str, redirect_uri: str) -> dict:
    """Trade the auth code for access and refresh tokens."""
    import urllib.request
    import urllib.parse

    data = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode("utf-8")

    req = urllib.request.Request(GMAIL_TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    return {
        "access_token": result.get("access_token"),
        "refresh_token": result.get("refresh_token"),
        "token_uri": GMAIL_TOKEN_URL,
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": GMAIL_SCOPES,
        "expiry": (datetime.now() + timedelta(seconds=result.get("expires_in", 3600))).isoformat(),
    }


def get_user_email(credentials_dict: dict) -> str:
    """Fetch the authenticated user's email address from Gmail API."""
    creds = _build_credentials(credentials_dict)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "")


def _build_credentials(credentials_dict: dict) -> Credentials:
    """Build a google.oauth2.credentials.Credentials object from a stored dict."""
    creds = Credentials(
        token=credentials_dict.get("access_token"),
        refresh_token=credentials_dict.get("refresh_token"),
        token_uri=credentials_dict.get("token_uri", GMAIL_TOKEN_URL),
        client_id=credentials_dict.get("client_id"),
        client_secret=credentials_dict.get("client_secret"),
        scopes=credentials_dict.get("scopes", GMAIL_SCOPES),
    )
    # Refresh if needed
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


# ════════════════════════════════════════════════════════════════
#  EMAIL SCANNING (Gmail API)
# ════════════════════════════════════════════════════════════════

def build_tax_year_query(tax_year: int) -> str:
    """Build a Gmail search query for tax slips of a given tax year.

    Tax slips for year X are typically sent between Dec X and April X+1.
    We add some buffer on both sides.
    """
    # Date window: Dec 1 of tax_year to May 1 of tax_year+1
    after_date = f"{tax_year}/12/01"
    before_date = f"{tax_year + 1}/05/01"

    # Keyword OR-group
    keyword_query = " OR ".join(f'"{kw}"' for kw in TAX_KEYWORDS)

    # Full query
    query = (
        f"(subject:({keyword_query}) OR {keyword_query}) "
        f"has:attachment filename:pdf "
        f"after:{after_date} before:{before_date}"
    )
    return query


def scan_for_tax_slips(credentials_dict: dict, tax_year: int,
                       max_results: int = 50) -> list[dict]:
    """Search a Gmail account for tax slips for a specific tax year.

    Returns a list of dicts with email metadata + attachment info.
    """
    creds = _build_credentials(credentials_dict)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    query = build_tax_year_query(tax_year)

    try:
        response = service.users().messages().list(
            userId="me", q=query, maxResults=max_results,
        ).execute()
    except HttpError as e:
        raise RuntimeError(f"Gmail API error: {e}")

    messages = response.get("messages", [])
    results = []

    for msg_summary in messages:
        try:
            msg = service.users().messages().get(
                userId="me", id=msg_summary["id"],
                format="full",
            ).execute()
        except HttpError:
            continue

        # Extract headers
        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
        subject = headers.get("subject", "(no subject)")
        sender = headers.get("from", "")
        date_str = headers.get("date", "")

        # Find PDF attachments
        attachments = _extract_pdf_attachments(msg["payload"])

        if not attachments:
            continue

        # Try to verify tax year by looking at the date AND any year-numeric patterns
        verified_year = _verify_tax_year(date_str, subject, tax_year)

        results.append({
            "msg_id": msg["id"],
            "subject": subject,
            "sender": sender,
            "date": date_str,
            "attachments": attachments,
            "verified_year": verified_year,
            "tax_year_match": verified_year == tax_year or verified_year is None,
        })

    return results


def _extract_pdf_attachments(payload: dict) -> list[dict]:
    """Recursively walk a Gmail message payload to find PDF attachments."""
    attachments = []

    def walk(part):
        mime_type = part.get("mimeType", "")
        filename = part.get("filename", "")

        if filename and (
            filename.lower().endswith(".pdf") or mime_type == "application/pdf"
        ):
            body = part.get("body", {})
            attachment_id = body.get("attachmentId")
            size = body.get("size", 0)
            if attachment_id:
                attachments.append({
                    "filename": filename,
                    "size": size,
                    "attachment_id": attachment_id,
                })

        # Recurse into multipart bodies
        for sub_part in part.get("parts", []):
            walk(sub_part)

    walk(payload)
    return attachments


def _verify_tax_year(date_str: str, subject: str, expected_year: int) -> Optional[int]:
    """Try to infer the tax year from the email date and subject.

    Returns the most likely tax year, or None if we can't tell.
    """
    # Look for a year in the subject (e.g. "Your 2024 T4 slip")
    year_match = re.search(r"\b(20\d\d)\b", subject)
    if year_match:
        return int(year_match.group(1))

    # Fall back to: tax slips arriving Jan-April of year Y are for year Y-1
    if date_str:
        try:
            from email.utils import parsedate_to_datetime
            email_date = parsedate_to_datetime(date_str)
            if email_date.month <= 4:
                return email_date.year - 1
            elif email_date.month >= 12:
                return email_date.year
        except Exception:
            pass

    return None


def download_attachment(credentials_dict: dict, msg_id: str,
                        attachment_id: str, filename: str) -> Optional[str]:
    """Download a PDF attachment from a Gmail message and save it locally.

    Returns the path to the saved file, or None on failure.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    creds = _build_credentials(credentials_dict)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    try:
        attachment = service.users().messages().attachments().get(
            userId="me", messageId=msg_id, id=attachment_id,
        ).execute()
    except HttpError:
        return None

    data = attachment.get("data", "")
    if not data:
        return None

    # Gmail uses URL-safe base64
    payload = base64.urlsafe_b64decode(data)

    # Save with a safe filename
    safe_name = re.sub(r'[<>:"/\\|?*]', "_", filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = DATA_DIR / f"{timestamp}_{safe_name}"

    with open(dest, "wb") as f:
        f.write(payload)

    return str(dest)


def revoke_credentials(credentials_dict: dict) -> bool:
    """Revoke an OAuth token (best-effort)."""
    import urllib.request
    import urllib.parse

    token = credentials_dict.get("refresh_token") or credentials_dict.get("access_token")
    if not token:
        return False

    try:
        data = urllib.parse.urlencode({"token": token}).encode("utf-8")
        req = urllib.request.Request(
            "https://oauth2.googleapis.com/revoke",
            data=data, method="POST",
        )
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return False

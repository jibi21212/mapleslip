"""IMAP email scanner for tax documents — runs 100% locally."""

import email
import imaplib
import os
import re
import tempfile
from email.header import decode_header
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data" / "documents"

# Keywords to search for in email subjects and sender names
TAX_KEYWORDS = [
    "T4", "T4A", "T4E", "T4RSP", "T5", "T3", "T2202",
    "RRSP", "tax slip", "tax form", "tax document", "tax receipt",
    "relevé", "releve",  # Quebec tax slips
    "statement of remuneration", "investment income",
    "employment income", "tuition",
    # US forms (for cross-border)
    "W-2", "W2", "1099", "1098",
]

# Common IMAP servers
IMAP_SERVERS = {
    "gmail.com": "imap.gmail.com",
    "googlemail.com": "imap.gmail.com",
    "outlook.com": "imap-mail.outlook.com",
    "hotmail.com": "imap-mail.outlook.com",
    "live.com": "imap-mail.outlook.com",
    "yahoo.com": "imap.mail.yahoo.com",
    "yahoo.ca": "imap.mail.yahoo.com",
    "icloud.com": "imap.mail.me.com",
    "me.com": "imap.mail.me.com",
    "aol.com": "imap.aol.com",
    "protonmail.com": "127.0.0.1",  # Requires ProtonMail Bridge
    "shaw.ca": "imap.shaw.ca",
    "bell.net": "imap.bell.net",
    "rogers.com": "imap.rogers.com",
    "telus.net": "imap.telus.net",
    "videotron.ca": "imap.videotron.ca",
    "cogeco.ca": "imap.cogeco.ca",
    "eastlink.ca": "imap.eastlink.ca",
}


def guess_imap_server(email_addr: str) -> str:
    """Guess the IMAP server from an email address."""
    domain = email_addr.split("@")[-1].lower()
    return IMAP_SERVERS.get(domain, f"imap.{domain}")


def _decode_header_value(value) -> str:
    """Decode an email header value."""
    if value is None:
        return ""
    decoded_parts = decode_header(str(value))
    result = ""
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result += part.decode(charset or "utf-8", errors="replace")
        else:
            result += str(part)
    return result


def connect(email_addr: str, password: str,
            imap_server: str = None, port: int = 993) -> imaplib.IMAP4_SSL:
    """Connect and authenticate to an IMAP server."""
    if not imap_server:
        imap_server = guess_imap_server(email_addr)

    conn = imaplib.IMAP4_SSL(imap_server, port)
    conn.login(email_addr, password)
    return conn


def scan_for_tax_emails(conn: imaplib.IMAP4_SSL,
                        year: int = None,
                        folder: str = "INBOX") -> list[dict]:
    """Scan the mailbox for emails that likely contain tax documents.

    Returns a list of dicts with email metadata and attachment info.
    """
    conn.select(folder, readonly=True)

    # Build IMAP search query
    # Search for emails with tax-related subjects from the relevant period
    # Tax slips for year X are typically sent between Jan-March of year X+1
    results = []
    seen_ids = set()

    for keyword in TAX_KEYWORDS:
        # Search by subject
        try:
            _, msg_ids = conn.search(None, f'(SUBJECT "{keyword}")')
        except Exception:
            continue

        if not msg_ids[0]:
            continue

        for msg_id in msg_ids[0].split():
            if msg_id in seen_ids:
                continue
            seen_ids.add(msg_id)

            try:
                _, msg_data = conn.fetch(msg_id, "(RFC822.SIZE BODY[HEADER])")
            except Exception:
                continue

            if not msg_data or not msg_data[0]:
                continue

            # Parse header
            header_data = msg_data[0]
            if isinstance(header_data, tuple) and len(header_data) > 1:
                raw_header = header_data[1]
            else:
                continue

            msg = email.message_from_bytes(raw_header)
            subject = _decode_header_value(msg.get("Subject", ""))
            sender = _decode_header_value(msg.get("From", ""))
            date_str = _decode_header_value(msg.get("Date", ""))

            # Filter by year if provided
            if year and str(year) not in date_str and str(year + 1) not in date_str:
                # Tax slips for 2024 arrive in early 2025
                pass  # Still include — date filtering is loose

            # Check if it has PDF attachments by fetching full message
            try:
                _, full_data = conn.fetch(msg_id, "(RFC822)")
            except Exception:
                continue

            if not full_data or not full_data[0]:
                continue

            full_msg = email.message_from_bytes(full_data[0][1])
            attachments = _get_pdf_attachments(full_msg)

            if attachments:
                results.append({
                    "msg_id": msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                    "subject": subject,
                    "sender": sender,
                    "date": date_str,
                    "attachments": attachments,
                    "keyword_matched": keyword,
                })

    return results


def _get_pdf_attachments(msg: email.message.Message) -> list[dict]:
    """Extract PDF attachment info from an email message."""
    attachments = []

    for part in msg.walk():
        content_type = part.get_content_type()
        content_disp = str(part.get("Content-Disposition", ""))

        if "attachment" in content_disp or content_type == "application/pdf":
            filename = part.get_filename()
            if filename:
                filename = _decode_header_value(filename)
            else:
                filename = "attachment.pdf"

            # Only include PDF files
            if filename.lower().endswith(".pdf") or content_type == "application/pdf":
                attachments.append({
                    "filename": filename,
                    "content_type": content_type,
                    "size": len(part.get_payload(decode=True) or b""),
                })

    return attachments


def download_attachment(conn: imaplib.IMAP4_SSL, msg_id: str,
                        attachment_filename: str) -> Optional[str]:
    """Download a specific PDF attachment and save it to the documents folder.

    Returns the path to the saved file, or None on failure.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        _, full_data = conn.fetch(
            msg_id.encode() if isinstance(msg_id, str) else msg_id,
            "(RFC822)",
        )
    except Exception:
        return None

    if not full_data or not full_data[0]:
        return None

    msg = email.message_from_bytes(full_data[0][1])

    for part in msg.walk():
        content_disp = str(part.get("Content-Disposition", ""))
        content_type = part.get_content_type()

        if "attachment" not in content_disp and content_type != "application/pdf":
            continue

        filename = part.get_filename()
        if filename:
            filename = _decode_header_value(filename)
        else:
            filename = "attachment.pdf"

        if filename != attachment_filename:
            continue

        payload = part.get_payload(decode=True)
        if not payload:
            continue

        # Save with a safe filename
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = DATA_DIR / f"{timestamp}_{safe_name}"

        with open(dest, "wb") as f:
            f.write(payload)

        return str(dest)

    return None


def disconnect(conn: imaplib.IMAP4_SSL):
    """Close the IMAP connection."""
    try:
        conn.close()
    except Exception:
        pass
    try:
        conn.logout()
    except Exception:
        pass

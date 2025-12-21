from __future__ import annotations

import imaplib
import email
from email.header import decode_header
import email.utils
import smtplib
import time
import uuid
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional, Tuple

from .config import settings


def validate_email_settings():
    if not (settings.smtp_username and settings.smtp_password and settings.from_email):
        raise RuntimeError("SMTP credentials or FROM_EMAIL missing. Configure .env")
    if not (settings.imap_username and settings.imap_password):
        raise RuntimeError("IMAP credentials missing. Configure .env")

@dataclass
class EmailMessage:
    subject: str
    html: str
    recipients: List[str]
    token: str

def _sanitize_subject(s: str) -> str:
    # Remove CR/LF and collapse whitespace
    s = (s or "").replace("\r", " ").replace("\n", " ").strip()
    # Strip simple HTML tags if any leaked in
    try:
        import re
        s = re.sub(r"<[^>]+>", "", s)
    except Exception:
        pass
    # Cap length to avoid provider limits
    if len(s) > 180:
        s = s[:177] + "..."
    # Fallback if empty after cleaning
    return s or "Newsletter"


def _smtp_client() -> smtplib.SMTP:
    if not (settings.smtp_username and settings.smtp_password and settings.from_email):
        raise RuntimeError("SMTP credentials or FROM_EMAIL missing. Configure .env")
    
    # If using port 465, use implicit SSL
    if settings.smtp_port == 465:
        server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port)
    else:
        # Default (587 or 25), use STARTTLS
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
        server.starttls()
    
    server.login(settings.smtp_username, settings.smtp_password)
    return server


def _imap_client() -> imaplib.IMAP4_SSL:
    if not (settings.imap_username and settings.imap_password):
        raise RuntimeError("IMAP credentials missing. Configure .env")
    m = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
    m.login(settings.imap_username, settings.imap_password)
    return m


def send_email(subject: str, html_body: str, recipients: List[str], token: Optional[str] = None) -> str:
    token = token or str(uuid.uuid4())
    clean_subj = _sanitize_subject(subject)
    subject_with_token = f"{clean_subj} [ref:{token}]"

    msg = MIMEMultipart('alternative')
    msg['From'] = f"{settings.from_name} <{settings.from_email}>"
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = subject_with_token

    msg.attach(MIMEText(html_body, 'html'))

    with _smtp_client() as server:
        server.sendmail(settings.from_email, recipients, msg.as_string())

    return token


def _decode_subject(raw_subject: str) -> str:
    try:
        parts = decode_header(raw_subject)
        decoded = []
        for text, enc in parts:
            if isinstance(text, bytes):
                try:
                    decoded.append(text.decode(enc or 'utf-8', errors='ignore'))
                except Exception:
                    decoded.append(text.decode('utf-8', errors='ignore'))
            else:
                decoded.append(text)
        return ''.join(decoded)
    except Exception:
        return raw_subject or ''


def _search_mailbox_for_token(m: imaplib.IMAP4_SSL, mailbox: str, token: str, since_ts: Optional[float]) -> Tuple[Optional[str], Optional[str]]:
    try:
        typ, _ = m.select(mailbox)
        if typ != 'OK':
            return None, None
    except Exception:
        return None, None
    typ, data = m.search(None, 'ALL')
    if typ == 'OK' and data and data[0]:
        ids = data[0].split()[-200:]
        for num in reversed(ids):
            typ, msg_data = m.fetch(num, '(RFC822)')
            if typ != 'OK':
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            raw_subj = msg.get('Subject', '')
            subject = _decode_subject(raw_subj)
            if f"[ref:{token}]" in subject:
                # If a since_ts was provided, ignore older messages
                if since_ts is not None:
                    try:
                        dt = email.utils.parsedate_to_datetime(msg.get('Date'))
                        if dt and dt.timestamp() < since_ts:
                            continue
                    except Exception:
                        pass
                # Extract body text
                body_text = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        if ctype == 'text/plain':
                            try:
                                body_text += part.get_payload(decode=True).decode(errors='ignore')
                            except Exception:
                                pass
                        elif ctype == 'text/html' and not body_text:
                            try:
                                body_text = part.get_payload(decode=True).decode(errors='ignore')
                            except Exception:
                                pass
                else:
                    try:
                        body_text = msg.get_payload(decode=True).decode(errors='ignore')
                    except Exception:
                        body_text = str(msg.get_payload())
                return subject, body_text
    return None, None


def poll_feedback(token: str, since_ts: Optional[float] = None, timeout_minutes: int | None = None, poll_interval: int | None = None) -> Tuple[Optional[str], Optional[str]]:
    timeout_minutes = timeout_minutes or settings.poll_timeout_minutes
    poll_interval = poll_interval or settings.poll_interval_seconds
    deadline = time.time() + timeout_minutes * 60

    with _imap_client() as m:
        while time.time() < deadline:
            # 1) Try INBOX
            subject, body = _search_mailbox_for_token(m, 'INBOX', token, since_ts)
            if subject or body:
                return subject, body
            # 2) Gmail fallback: try All Mail when using Gmail IMAP
            if (settings.imap_host or '').endswith('gmail.com'):
                subject, body = _search_mailbox_for_token(m, '[Gmail]/All Mail', token, since_ts)
                if subject or body:
                    return subject, body
            time.sleep(poll_interval)
    return None, None

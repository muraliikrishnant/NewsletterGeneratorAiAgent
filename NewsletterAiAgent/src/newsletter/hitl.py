from __future__ import annotations

from dataclasses import dataclass
import json, os, time as _time
from typing import List, Tuple

from .email_client import send_email, poll_feedback
from .writer import revise_with_feedback
from .config import settings


@dataclass
class ReviewResult:
    approved: bool
    subject: str
    html: str
    feedback: str | None = None


def classify_feedback(text: str) -> bool:
    # Simple heuristic; could be upgraded to LLM classification.
    t = (text or "").lower()
    approved_phrases = ["looks good", "go ahead", "works for me", "approved", "no changes"]
    declined_phrases = [
        "tweak", "needs", "reword", "revise", "adjust", "not quite", "don't",
        "not approved", "declined", "reject", "more detail", "add images", "needs images",
        "too short", "not detailed", "fix", "change"
    ]
    if any(p in t for p in approved_phrases):
        return True
    if any(p in t for p in declined_phrases):
        return False
    # Default: require explicit approval
    return False


def review_loop(initial_subject: str, html: str, recipients: List[str]) -> Tuple[str, str]:
    send_time = __import__('time').time()
    token = send_email(initial_subject + " (Draft)", html, recipients)
    print(f"Draft sent to {', '.join(recipients)} with subject: '{initial_subject} (Draft)'")
    print(f"Tracking token: [ref:{token}] — waiting up to {settings.poll_timeout_minutes} minutes for your reply (poll every {settings.poll_interval_seconds}s)...")
    try:
        status_path = os.path.join(os.getcwd(), "hitl_status.json")
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({
                "status": "waiting",
                "token": token,
                "subject": initial_subject + " (Draft)",
                "recipients": recipients,
                "since_ts": send_time,
                "updated_at": _time.time(),
            }, f, indent=2)
    except Exception:
        pass
    # New behavior: do not auto-revise. Wait for an explicit 'approve' reply.
    while True:
        _, body_text = poll_feedback(token, since_ts=send_time)
        if not body_text:
            # Timeout or no reply; send Unapproved Final
            print("No reply received before timeout. Sending the last version as Unapproved Final.")
            try:
                status_path = os.path.join(os.getcwd(), "hitl_status.json")
                with open(status_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "status": "timeout",
                        "token": token,
                        "subject": initial_subject + " (Unapproved Final)",
                        "recipients": recipients,
                        "since_ts": send_time,
                        "updated_at": _time.time(),
                    }, f, indent=2)
            except Exception:
                pass
            break

        # If we receive any reply text, check for explicit 'approve' keyword
        t = (body_text or "").lower()
        if "approve" in t or "approved" in t or "looks good" in t or "go ahead" in t:
            # Send final
            send_email(initial_subject, html, recipients)
            print("Approval received. Final email sent.")
            try:
                status_path = os.path.join(os.getcwd(), "hitl_status.json")
                with open(status_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "status": "approved",
                        "token": token,
                        "subject": initial_subject,
                        "recipients": recipients,
                        "since_ts": send_time,
                        "updated_at": _time.time(),
                    }, f, indent=2)
            except Exception:
                pass
            return initial_subject, html

        # Received a non-approval reply — decide whether to revise or keep waiting
        print("Received feedback; evaluating whether to revise or wait for explicit 'approve'...")
        t = (body_text or "").lower()
        declined_phrases = [
            "tweak", "needs", "reword", "revise", "adjust", "not quite", "don't",
            "not approved", "declined", "reject", "more detail", "add images", "needs images",
            "too short", "not detailed", "fix", "change"
        ]

        # If negative feedback detected, ask the LLM to revise and resend
        if any(p in t for p in declined_phrases):
            print("Negative feedback detected — asking LLM to revise and resending draft.")
            try:
                revised_subject, revised_html = revise_with_feedback(html, body_text)
                html = revised_html
                initial_subject = revised_subject or initial_subject
            except Exception as e:
                print("Revision failed:", e)

            # Resend revised draft
            send_time = __import__('time').time()
            token = send_email(initial_subject + " (Draft)", html, recipients)
            print(f"Revised draft sent. New subject: '{initial_subject} (Draft)'. New token: [ref:{token}] — awaiting reply...")
            try:
                status_path = os.path.join(os.getcwd(), "hitl_status.json")
                with open(status_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "status": "waiting",
                        "token": token,
                        "subject": initial_subject + " (Draft)",
                        "recipients": recipients,
                        "since_ts": send_time,
                        "updated_at": _time.time(),
                    }, f, indent=2)
            except Exception:
                pass
            # continue waiting loop
            continue

        # Otherwise, record feedback and keep waiting for explicit approval
        try:
            status_path = os.path.join(os.getcwd(), "hitl_status.json")
            with open(status_path, "w", encoding="utf-8") as f:
                json.dump({
                    "status": "feedback_received",
                    "token": token,
                    "subject": initial_subject + " (Draft)",
                    "recipients": recipients,
                    "feedback": body_text,
                    "since_ts": send_time,
                    "updated_at": _time.time(),
                }, f, indent=2)
        except Exception:
            pass
    # If loop exits without approval, send last best
    send_email(initial_subject + " (Unapproved Final)", html, recipients)
    print("Unapproved Final sent.")
    try:
        status_path = os.path.join(os.getcwd(), "hitl_status.json")
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({
                "status": "sent_unapproved",
                "token": token,
                "subject": initial_subject + " (Unapproved Final)",
                "recipients": recipients,
                "since_ts": send_time,
                "updated_at": _time.time(),
            }, f, indent=2)
    except Exception:
        pass
    return initial_subject, html

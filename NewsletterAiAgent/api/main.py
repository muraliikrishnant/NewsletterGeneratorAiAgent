from __future__ import annotations

import os
import json
import tempfile
import time
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from newsletter.run import build_newsletter
from newsletter.hitl import review_loop
from newsletter.email_client import validate_email_settings

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Newsletter AI Agent API is running", "docs": "/docs"}


@app.get("/models")
def list_models():
    try:
        from NewsletterAiAgent.src.newsletter.llm import _get_gemini_client
        client = _get_gemini_client()
        models = []
        for m in client.models.list():
            # Just return the name (or display_name if available)
            # The SDK object likely has 'name', 'display_name'.
            # To be safe, we'll try to get name, or fallback to str(m)
            name = getattr(m, 'name', str(m))
            models.append(name)
        return {"models": models}
    except Exception as e:
        return {"error": str(e)}


# Allow local development frontend (http://localhost:3000) to make requests.
# In production, set a stricter set of allowed origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://muralii-rutgersstudent.github.io"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BuildReq(BaseModel):
    prompt: str
    words: Optional[int] = None


class SendReq(BaseModel):
    prompt: str
    words: Optional[int] = None


class PublishReq(BaseModel):
    token: str


def _review_loop_background(subject: str, html: str, recipients: list[str]):
    try:
        review_loop(subject, html, recipients)
    except Exception as exc:
        # Surface background errors in logs and hitl_status.json so the frontend/user can see the failure reason
        print(f"[hitl] review_loop failed: {exc}")
        try:
            status_path = os.path.join(os.getcwd(), 'hitl_status.json')
            with open(status_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'status': 'error',
                    'error': str(exc),
                    'subject': subject,
                    'recipients': recipients,
                    'updated_at': time.time(),
                }, f, indent=2)
        except Exception:
            pass


@app.get('/diag/email')
def diag_email(send_test: bool = False):
    """Email diagnostic.
    - SMTP: NOOP ping after auth; send_test=1 sends a short plain text email.
    - Resend: send_test=1 performs a minimal API send; otherwise returns status.
    """
    from newsletter.config import settings
    try:
        if settings.email_sender == 'resend' and settings.resend_api_key:
            # Resend path
            if not send_test:
                return {"status": "ok", "sender": "resend"}
            # Perform a small test send via Resend
            to_addr = settings.smtp_username or settings.from_email
            if not to_addr:
                raise RuntimeError("No SMTP_USERNAME or FROM_EMAIL configured for test send")
            import requests
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "from": f"{settings.from_name} <{settings.from_email}>",
                "to": [to_addr],
                "subject": "NewsletterAiAgent Resend test",
                "text": f"Resend test at {int(time.time())}",
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code >= 400:
                raise RuntimeError(f"Resend error {resp.status_code}: {resp.text}")
            return {"status": "ok", "sender": "resend", "test_send": {"to": to_addr, "accepted": True}}
        else:
            # SMTP path
            validate_email_settings()
            from newsletter.email_client import _smtp_client
            from email.mime.text import MIMEText
            import email.utils as eut

            with _smtp_client() as server:
                # Lightweight ping
                code, resp = server.noop()
                result = {"status": "ok", "noop": int(code), "server": str(resp), "sender": "smtp"}

                if send_test:
                    to_addr = settings.smtp_username or settings.from_email
                    if not to_addr:
                        raise RuntimeError("No SMTP_USERNAME or FROM_EMAIL configured for test send")
                    subj = "NewsletterAiAgent SMTP test"
                    body = f"SMTP test from /diag/email?send_test=1 at {int(time.time())}."
                    msg = MIMEText(body, 'plain', 'utf-8')
                    msg['From'] = f"{settings.from_name} <{settings.from_email or settings.smtp_username}>"
                    msg['To'] = to_addr
                    msg['Subject'] = subj
                    msg['Date'] = eut.formatdate(localtime=True)
                    msg['Reply-To'] = settings.from_email or settings.smtp_username or ""

                    envelope_from = settings.smtp_username or settings.from_email
                    refused = server.sendmail(envelope_from, [to_addr], msg.as_string())
                    if refused:
                        refused_codes = {k: int(v[0]) for k, v in refused.items()}
                        result["test_send"] = {"to": to_addr, "accepted": False, "refused": refused_codes}
                    else:
                        result["test_send"] = {"to": to_addr, "accepted": True}

                return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/diag/config')
def diag_config():
    """Show loaded SMTP/IMAP config (redacted, no secrets exposed)."""
    from newsletter.config import settings
    return {
        "smtp_host": settings.smtp_host or "(not set)",
        "smtp_port": settings.smtp_port,
        "smtp_username": settings.smtp_username or "(not set)",
        "smtp_password": "***" if settings.smtp_password else "(not set)",
        "from_email": settings.from_email or "(not set)",
        "from_name": settings.from_name,
        "imap_host": settings.imap_host or "(not set)",
        "imap_port": settings.imap_port,
        "imap_username": settings.imap_username or "(not set)",
        "imap_password": "***" if settings.imap_password else "(not set)",
        "recipients": settings.default_recipients or "(not set)",
    }


@app.post('/build')
def build(req: BuildReq):
    try:
        subject, html = build_newsletter(req.prompt, words_limit=req.words)
        return {'subject': subject, 'html': html}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/send')
def send(req: SendReq, background_tasks: BackgroundTasks):
    try:
        # Fail fast if SMTP is not configured so the frontend sees an error instead of a silent background failure
        validate_email_settings()

        # 1. Generate the newsletter logic synchronously to catch basic errors immediately
        subject, html = build_newsletter(req.prompt, words_limit=req.words)
        
        # 2. Start the Blocking HITL review loop in the background
        recipients = os.getenv('RECIPIENTS', '').split(',') if os.getenv('RECIPIENTS') else [os.getenv('SMTP_USERNAME')]
        
        background_tasks.add_task(_review_loop_background, subject, html, recipients)
        
        # 3. Return immediate success so frontend doesn't timeout
        return {
            'status': 'background_process_started',
            'subject': subject,
            'html': html,
            'message': 'Review loop started in background. Check your email.'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/status')
def status():
    path = os.path.join(os.getcwd(), 'hitl_status.json')
    if not os.path.exists(path):
        return {'status': 'none'}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/publish')
def publish(req: PublishReq):
    # Simple WordPress publishing: post to /wp-json/wp/v2/posts with HTML content
    wp_url = os.getenv('WORDPRESS_URL')
    wp_user = os.getenv('WP_USER')
    wp_app_password = os.getenv('WP_APP_PASSWORD')
    if not (wp_url and wp_user and wp_app_password):
        raise HTTPException(status_code=400, detail='WordPress credentials not configured in env')
    # Load last hitl_status to get subject and html
    path = os.path.join(os.getcwd(), 'hitl_status.json')
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail='No hitl_status.json found')
    with open(path, 'r', encoding='utf-8') as f:
        st = json.load(f)
    # In a simple setup we assume the final HTML exists in generated_no_source.html or similar
    html_path = os.path.join(os.getcwd(), 'generated_from_prompt.html')
    if not os.path.exists(html_path):
        # fallback to draft_run_output.html
        alt = os.path.join(os.getcwd(), 'draft_run_output.html')
        if os.path.exists(alt):
            html_path = alt
        else:
            raise HTTPException(status_code=404, detail='No generated HTML found to publish')
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    import requests
    post_url = wp_url.rstrip('/') + '/wp-json/wp/v2/posts'
    data = {'title': st.get('subject', 'Newsletter'), 'content': html, 'status': 'publish'}
    try:
        resp = requests.post(post_url, json=data, auth=(wp_user, wp_app_password), timeout=30)
        resp.raise_for_status()
        return {'url': resp.json().get('link')}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from __future__ import annotations

import os
import json
import tempfile
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from newsletter.run import build_newsletter
from newsletter.hitl import review_loop

app = FastAPI()

# Allow local development frontend (http://localhost:3000) to make requests.
# In production, set a stricter set of allowed origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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


@app.post('/build')
def build(req: BuildReq):
    try:
        subject, html = build_newsletter(req.prompt, words_limit=req.words)
        return {'subject': subject, 'html': html}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/send')
def send(req: SendReq):
    try:
        subject, html = build_newsletter(req.prompt, words_limit=req.words)
        # write temp html for send-existing path
        tf = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
        tf.write(html.encode('utf-8'))
        tf.flush()
        tf.close()
        # review_loop will send and block until approved or final
        final_subject, final_html = review_loop(subject, html, os.getenv('RECIPIENTS', '').split(',') if os.getenv('RECIPIENTS') else [os.getenv('SMTP_USERNAME')])
        return {'subject': final_subject, 'html': final_html, 'token': None}
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

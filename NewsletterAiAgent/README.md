# Newsletter (Python, Ollama, Tavily, HITL)

An end-to-end Python project that builds a research-backed business newsletter using a local Ollama model as the LLM "brain", performs live web research via Tavily, adds images, and runs a human-in-the-loop (HITL) approval cycle via email before sending the final newsletter.

## What it does
- Takes a prompt/brief
- Uses Tavily for initial research and topic deep-dives (with raw content + images)
- Uses Ollama LLM to plan title + topics, write three sections, and merge to an HTML email
- Adds image links to the email body
- Sends a draft email to reviewers and waits for feedback
- If approved → sends final. If declined → revises with LLM and loops (max N times)

## Prerequisites
- macOS with Homebrew recommended
- Python 3.10+
- Ollama installed and running locally
- Tavily API key
- SMTP/IMAP credentials (example: Gmail with App Passwords)

### Install Ollama and pull a model
```
brew install ollama
ollama serve
ollama pull llama3.1:8b-instruct
```
You can use other models (e.g., mistral, qwen). Update `OLLAMA_MODEL` accordingly.

### Get a Tavily API key
Sign up at https://tavily.com and create an API key.

## Setup
1) Create and activate a virtualenv
```
python3 -m venv .venv
source .venv/bin/activate
```

2) Install dependencies
```
pip install -r requirements.txt
```

3) Configure environment variables
- Copy `.env.example` to `.env` and fill in values
```
cp .env.example .env
```

4) Verify Ollama is running
- Default: http://localhost:11434

### Use Gemini instead of Ollama (optional)
- Install the extra dependency (already in requirements.txt): `pip install google-generativeai`
- In `.env` set:
	- `LLM_PROVIDER=gemini`
	- `GEMINI_API_KEY=your_gemini_key`
	- `GEMINI_MODEL=gemini-2.0-flash` (or another)
- You can switch back anytime by setting `LLM_PROVIDER=ollama`.

## Run it
```
python -m newsletter.run "Write a newsletter about AI agents in business ops"
```
Optional: override recipients
```
python -m newsletter.run "Weekly fintech round-up" --to "alice@example.com,bob@example.com"
```
Control the total words (approximate):
```
python -m newsletter.run "Autonomous vehicle monthly briefing" --words 1500 --dry-run --output av.html
```

This will:
- Research the prompt
- Plan title + topics
- Write three sections and merge into HTML
- Email a Draft to recipients and wait for a reply to the same thread
- If the reply indicates approval, the Final is sent; if not, the system revises and loops

## Human-in-the-loop details
- The subject line includes a token like `[ref:UUID]`; replies must keep the subject for threading
- Approval keywords: "Looks good", "Approved", "Go ahead", etc.
- Decline keywords: "tweak", "reword", "revise", etc.
- If no reply by timeout, the last version is sent as "Unapproved Final"
 - The system now scans recent INBOX messages (read or unread) to avoid missing replies

## Notes and limits
- Ollama tool-calling for live browsing is not used here; instead, we use Tavily for research. This keeps the model local and predictable.
- For images, we insert up to 3 top image links at the top of the email for inbox compatibility; full inline image embedding could be added with attachments or hosted URLs.
- Gmail requires App Passwords when 2FA is on. Ensure IMAP is enabled in Gmail settings.

## Project layout
- `src/newsletter/config.py` – Configuration via env vars
- `src/newsletter/llm.py` – Minimal Ollama client
- `src/newsletter/research.py` – Tavily research helpers
- `src/newsletter/writer.py` – Planning, section writing, HTML merge, revision
- `src/newsletter/email_client.py` – SMTP send + IMAP polling
- `src/newsletter/hitl.py` – Human-in-the-loop review loop
- `src/newsletter/run.py` – CLI entrypoint

## Troubleshooting
- If requests/tavily/bs4 missing, ensure you’re in the virtualenv and ran `pip install -r requirements.txt`
- If IMAP polling never detects replies, check your email provider’s IMAP settings and ensure replies preserve the subject with `[ref:...]`
- If Ollama returns empty content, try another model or lower temperature

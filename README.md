# NewsletterAiAgent

## Quick Start

Run these commands to start the application:

### 1. Start Backend (Terminal 1)
```bash
PYTHONPATH=NewsletterAiAgent/src/ .venv/bin/uvicorn NewsletterAiAgent.api.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Start Frontend (Terminal 2)
```bash
cd NewsletterAiAgent/frontend && python3 -m http.server 3000
```

Then open your browser to `http://localhost:3000`

## CLI Usage (Optional)

### 3. Dry-run (Build Only)
Saves HTML to `draft_run_output.html`:
```bash
PYTHONPATH=NewsletterAiAgent/src/ .venv/bin/python -m newsletter.run "robotaxi operations" --words 50 --dry-run --output draft_run_output.html
```

### 4. CLI Send (HITL Loop)
Send draft and run Human-in-the-Loop approval process:
```bash
PYTHONPATH=NewsletterAiAgent/src/ .venv/bin/python -m newsletter.run "robotaxi operations" --words 50 --to "you@example.com"
```
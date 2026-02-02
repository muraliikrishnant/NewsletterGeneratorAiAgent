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

## Deployment

### Backend Deployment (Render.com)

1. **Sign up for Render**: Go to [render.com](https://render.com) and connect your GitHub account
2. **Create New Web Service**: Click "New +" → "Web Service"
3. **Connect Repository**: Select your `NewsletterAIAgent_Tars` repository
4. **Auto-Deploy**: Render will detect `render.yaml` and configure automatically
5. **Add Environment Variables** in Render Dashboard:
   - `LLM_PROVIDER=ollama`
   - `OLLAMA_HOST=http://your-ollama-host:11434` (must be reachable from Render)
   - `OLLAMA_MODEL=llama3.1:8b-instruct`
   - `TAVILY_API_KEY=your_key`
   - `SMTP_USERNAME=your_gmail`
   - `SMTP_PASSWORD=your_app_password`
   - `IMAP_USERNAME=your_gmail`
   - `IMAP_PASSWORD=your_app_password`
   - `EMAIL_SENDER=your_gmail`
   - `RECIPIENTS=["recipient@example.com"]`
6. **Deploy**: Click "Create Web Service"
7. **Copy URL**: Note your deployed URL (e.g., `https://newsletter-ai-backend.onrender.com`)

### Frontend Deployment (GitHub Pages - Free)

1. **Enable GitHub Pages**: Go to your repo → Settings → Pages
2. **Configure Source**: 
   - Source: "Deploy from a branch"
   - Branch: `main`
   - Folder: `/docs` (root-level docs folder)
3. **Save**: GitHub will deploy automatically (we added `.nojekyll` to skip Jekyll)
4. **Access**: Your site will be at `https://muraliikrishnant.github.io/NewsletterAIAgent_Tars/`

**Note**: The frontend automatically detects production vs local environment and uses the correct API URL.

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

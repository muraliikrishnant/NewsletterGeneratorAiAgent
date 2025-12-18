TARS Newsletter Frontend

This is a minimal static frontend that calls a backend API for building, sending, and publishing newsletters.

Files:

Deploying the frontend (quick):
1) Host static files on Vercel, Netlify, or GitHub Pages. For Vercel, connect the repo and set the output folder to `/frontend`.
2) Set an environment variable `API_BASE` in the frontend hosting (or edit `app.js` to hardcode the backend URL).
3) On Name.com, point your domain to the frontend host (CNAME/A depending on provider). Vercel provides exact DNS instructions.

Publishing to WordPress:

Security:

Local development (quick start)

- Backend (terminal 1):

	PYTHONPATH=NewsletterAiAgent/src/ .venv/bin/uvicorn NewsletterAiAgent.api.main:app --reload --host 127.0.0.1 --port 8000

- Frontend (terminal 2):

	cd NewsletterAiAgent/frontend && python3 -m http.server 3000

Notes about tone and style

- The newsletter voice is controlled by the style assets in `style_guides/bartlett_hormozi.md` and examples in `style_examples/bartlett_hormozi.json`.
- The generator now uses these few-shot assets by default so newsletter sections should reflect the blended Steven Bartlett + Alex Hormozi tone, Tesla master-plan style when relevant, and include TARS Group blurbs only for AV-related content.

*** End ***
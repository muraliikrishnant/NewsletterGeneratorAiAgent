# NewsletterAiAgent

Building

- Run these four commands (terminals 1 & 2 for servers; 3 for a dry-run that saves HTML; 4 to send via CLI/HITL):

1. Start backend (terminal 1)	- PYTHONPATH=NewsletterAiAgent/src/ .venv/bin/uvicorn NewsletterAiAgent.api.main:app --reload --host 127.0.0.1 --port 8000

2. Start frontend (terminal 2)	cd NewsletterAiAgent/frontend && python3 -m http.server 3000

3. 	3	Dry-run (build only; saves HTML to draft_run_output.html)	PYTHONPATH=NewsletterAiAgent/src/ .venv/bin/python -m newsletter.run "robotaxi operations" --words 50 --dry-run --output draft_run_output.html

4. 	4	CLI send (send draft and run HITL loop; replace recipient as needed)	PYTHONPATH=NewsletterAiAgent/src/ .venv/bin/python -m newsletter.run "robotaxi operations" --words 50 --to "you@example.com"

Disregard (Same as above):
- PYTHONPATH=NewsletterAiAgent/src/ .venv/bin/uvicorn NewsletterAiAgent.api.main:app --reload --host 127.0.0.1 --port 8000
- cd NewsletterAiAgent/frontend && python3 -m http.server 3000
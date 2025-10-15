from __future__ import annotations

import argparse
import json
import os
from typing import List, Optional

from dotenv import load_dotenv

from .config import settings
from .llm import OllamaClient, ChatMessage
from .research import initial_research, research_topics
from .writer import plan_title_and_topics, write_section, merge_sections_to_html, add_images_to_html, enforce_on_topic_and_length
from .hitl import review_loop
from .email_client import send_email
from bs4 import BeautifulSoup


def build_newsletter(prompt: str, words_limit: int | None = None) -> tuple[str, str]:
    # Initial research
    init = initial_research(prompt)
    articles_blob = json.dumps(init, indent=2)

    plan = plan_title_and_topics(articles_blob)
    title: str = plan["title"]
    topics: List[str] = plan["topics"]

    sections: List[str] = []
    all_images: List[str] = []
    for topic in topics:
        res = research_topics(topic)
        blob = json.dumps(res, indent=2)
        # collect images if present
        images = []
        for item in res.get("results", []):
            imgs = item.get("images") or []
            if isinstance(imgs, list):
                images.extend([i for i in imgs if isinstance(i, str)])
        all_images.extend(images)
        sect = write_section(topic, blob)
        sections.append(sect)

    subject, html_body = merge_sections_to_html(title, sections, words_limit=words_limit)
    html_body = add_images_to_html(html_body, all_images)
    # Enforce on-topic coverage and length
    required_terms = ["Zoox", "Waymo", "Tesla", "robotaxi", "Washington", "safety", "regulatory", "mobility-as-a-service"]
    html_body = enforce_on_topic_and_length(html_body, prompt, required_terms, target_words=words_limit)
    return subject, html_body


def _derive_subject_from_html(html: str, fallback: str = "Newsletter Draft") -> str:
    try:
        soup = BeautifulSoup(html, "html5lib")
        # Prefer an explicit <title>
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        # Else first <h2>
        h2 = soup.find("h2")
        if h2 and h2.get_text(strip=True):
            return h2.get_text(strip=True)[:120]
        # Else first 80 chars of text
        txt = soup.get_text(" ", strip=True)
        if txt:
            return (txt[:117] + "...") if len(txt) > 120 else txt
    except Exception:
        pass
    return fallback


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Newsletter builder with HITL")
    parser.add_argument("prompt", nargs="?", help="Research prompt/brief for the newsletter")
    parser.add_argument("--to", dest="recipients", help="Comma-separated recipients", default=",".join(settings.default_recipients))
    parser.add_argument("--dry-run", action="store_true", help="Build the newsletter and print/save it without sending emails")
    parser.add_argument("--output", dest="output_path", help="If set with --dry-run, save HTML to this file path")
    parser.add_argument("--no-hitl", action="store_true", help="Send a single email without waiting for replies (no HITL loop)")
    parser.add_argument("--words", type=int, default=None, help="Target total word count for the newsletter (approximate)")
    parser.add_argument("--send-existing", dest="existing_path", help="Path to an existing HTML draft to send (skips building)")
    parser.add_argument("--subject", dest="subject_override", help="Optional subject to use when sending an existing draft")
    args = parser.parse_args()

    recipients = [r.strip() for r in (args.recipients or "").split(",") if r.strip()]
    if not args.dry_run and not recipients:
        raise SystemExit("No recipients specified. Use --to or set RECIPIENTS in .env, or pass --dry-run")

    # If sending an existing draft, bypass building
    if args.existing_path:
        if not os.path.exists(args.existing_path):
            raise SystemExit(f"File not found: {args.existing_path}")
        with open(args.existing_path, "r", encoding="utf-8") as f:
            html_body = f.read()
        subject = args.subject_override or _derive_subject_from_html(html_body)
        if args.dry_run:
            print("Subject:", subject)
            if args.output_path:
                with open(args.output_path, "w", encoding="utf-8") as f:
                    f.write(html_body)
                print("HTML saved to:", args.output_path)
            else:
                preview = html_body[:1000]
                print("\nPreview HTML (first 1000 chars):\n")
                print(preview)
            return
        if args.no_hitl:
            send_email(subject + " (Draft)", html_body, recipients)
            print("Draft sent without HITL. Subject:", subject)
            return
        final_subject, final_html = review_loop(subject, html_body, recipients)
        print("Newsletter sent. Subject:", final_subject)
        return

    # Otherwise, build a fresh newsletter
    if not args.prompt:
        raise SystemExit("Missing prompt. Provide a prompt or use --send-existing to send a saved draft.")
    subject, html_body = build_newsletter(args.prompt, words_limit=args.words)

    if args.dry_run:
        print("Subject:", subject)
        if args.output_path:
            with open(args.output_path, "w", encoding="utf-8") as f:
                f.write(html_body)
            print("HTML saved to:", args.output_path)
        else:
            # Avoid dumping huge HTML; print a short preview
            preview = html_body[:1000]
            print("\nPreview HTML (first 1000 chars):\n")
            print(preview)
        return

    if args.no_hitl:
        send_email(subject + " (Draft)", html_body, recipients)
        print("Draft sent without HITL. Subject:", subject)
        return

    # Human-in-the-loop review cycle (emails will be sent)
    final_subject, final_html = review_loop(subject, html_body, recipients)
    print("Newsletter sent. Subject:", final_subject)


if __name__ == "__main__":
    main()

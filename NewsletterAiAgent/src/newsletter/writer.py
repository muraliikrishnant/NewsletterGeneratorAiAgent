from __future__ import annotations

import datetime as dt
import html
import re
from typing import Any, Dict, List, Tuple, Optional

from bs4 import BeautifulSoup

from .llm import simple_chat, ChatMessage, OllamaClient, generate_with_style
from .email_client import _sanitize_subject


def _remove_source_tokens(text: str) -> str:
    """Remove stray 'Source' tokens that the model sometimes inserts next to sentences or links.

    This performs a simple regex-based removal of the standalone word 'Source' (optionally followed
    by punctuation) and collapses extra whitespace. It avoids touching URLs.
    """
    if not text:
        return text
    # Aggressively remove standalone 'source' or 'sources' (case-insensitive) with optional punctuation
    text = re.sub(r"(?i)\bsource(s)?\b[.:]?", "", text)
    # Collapse runs of whitespace introduced by removals
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _extract_sources(text: str) -> List[str]:
    # Collect all URLs
    urls = re.findall(r"https?://\S+", text)
    # Deduplicate
    return sorted(set(u.rstrip(').,;"\'')) for u in urls)


def plan_title_and_topics(articles_blob: str) -> Dict[str, Any]:
    system = (
        "You are an expert newsletter planner. You will receive three articles from the past week. "
        "Your job is to come up with a creative and fun title as well as exactly three main topics for this newsletter. "
        "The newsletter should flow nicely, feel informative, and holistic. The topics should be 3-5 words. "
        "Return strict JSON with keys: title (string), topics (array of 3 strings)."
    )
    user = articles_blob
    response = simple_chat(system, user)
    # Attempt to parse JSON in the reply; if not JSON, try to extract with regex
    import json
    try:
        data = json.loads(response)
        assert isinstance(data, dict)
        assert isinstance(data.get("title"), str)
        topics = data.get("topics")
        assert isinstance(topics, list) and len(topics) == 3
        return {"title": data["title"], "topics": topics}
    except Exception:
        # Fallback: naive topic extraction
        lines = [l.strip("-: •\t ") for l in response.splitlines() if l.strip()]
        title = lines[0] if lines else "Weekly Business Brief"
        topics = [l for l in lines[1:4]]
        topics += ["Market Trends", "AI Strategy", "Leadership Insights"]
        topics = topics[:3]
        return {"title": title, "topics": topics}



def write_section(topic: str, research_blob: str, force_title: Optional[str] = None) -> str:
    system = (
        "You are writing a business newsletter strictly in the blended style of Steven Bartlett and Alex Hormozi. "
        "Tone constraints (must follow):\n"
        "- Bartlett: start with a personal story or reflective hook; emotionally resonant; human, vulnerable.\n"
        "- Hormozi: convert insight into sharp, tactical lessons with numbers, frameworks, and direct language.\n"
        "- Sentences: mostly short. Rhythm: alternate punchy one-liners with slightly longer, flowing thoughts.\n"
        "- Cut fluff. Speak to a smart but busy operator.\n"
        "Structure constraints:\n"
        "- Always start with a clear <h2> section title.\n"
        "- Then 2–5 short paragraphs (2–4 sentences each).\n"
        "- End the section with 3–5 actionable bullets labeled 'Playbook' (if relevant).\n"
        "Evidence constraints: if citing facts, include real sources as clickable URLs under a final 'Sources' sub-block. No fabricated links.\n"
        "Important: Do NOT output the word 'Source' or 'Sources' anywhere in the text or next to links — strip that token entirely.\n"
        "Output HTML only (no markdown). No overall title or conclusion."
    )
    title_hint = f"Use this exact section title: {force_title}\n\n" if force_title else ""
    user = f"{title_hint}Topic: {topic}\n\nResearch: {research_blob}"
    # Use the style-aware generator so the Bartlett+Hormozi voice and examples are applied
    resp = generate_with_style(user, style_name="bartlett_hormozi")
    return _remove_source_tokens(resp or "")


def merge_sections_to_html(title: str, sections: List[str], words_limit: Optional[int] = None) -> Tuple[str, str]:
    today = dt.date.today().isoformat()
    system = (
        "You are an expert newsletter editor. Merge the provided sections into a cohesive, email-ready HTML body with a holistic introduction and conclusion. "
        "Maintain a professional, concise tone for a business audience and preserve intended meaning. Be as detailed as needed to fully cover the topics; avoid fluff. "
        "Enforce style: blended Steven Bartlett (reflective human hook) + Alex Hormozi (tactical, numbers-first lessons). Keep sentences short; vary rhythm.\n"
        "Structure (HTML only):\n"
        "1) <p> Introduction that frames all topics and their relevance; reference today’s date: "
        f"{today}.\n"
    "2) For each provided section: <h2> Use the given title when present; edited <p> content; NO inline clickable citations. Never give me clickable inline citations using <a href=\"https://...\">Link</a>. Include <img src=\"...\" width=\"600\"> if appropriate.\n"
    "Important: Do NOT output the word 'Source' or 'Sources' anywhere in the text; if you would otherwise include it, omit it.\n"
        "3) <h3>Sources</h3><ul> consolidated list, deduplicated, alphabetized by Publication Name.\n"
        "4) <p> Conclusion tying threads together with implications or next steps.\n"
        "Only use basic HTML tags (<h2>, <h3>, <p>, <ul>, <li>, <a>, <img>). No scripts or external styles.\n"
        "Output format: 'Subject: ...' then blank line, then 'Content:' then HTML body only."
    )
    if words_limit:
        system += (
            f" Aim for approximately {words_limit} words total (+/-10%). If above target, summarize while preserving facts and citations; if below, expand with concrete, cited details."
        )
    user = f"Title: {title}\n\n" + "\n\n".join(sections)
    content = generate_with_style(user, style_name="bartlett_hormozi")
    # Best-effort split
    subject = _sanitize_subject(f"{title} — Weekly Newsletter")
    if content.startswith("Subject:"):
        try:
            head, html_body = content.split("\n\nContent:\n", 1)
            subject = _sanitize_subject(head.replace("Subject:", "").strip())
            return subject, _remove_source_tokens(html_body.strip())
        except ValueError:
            pass
    return subject, _remove_source_tokens(content)


def add_images_to_html(html_body: str, image_urls: List[str]) -> str:
    if not image_urls:
        return html_body
    soup = BeautifulSoup(html_body, "html5lib")
    # Insert up to 3 inline <img> tags near the top of the body for visibility
    insertion_point = soup.body or soup
    for url in image_urls[:3]:
        p = soup.new_tag("p")
        img = soup.new_tag("img", src=url, alt="Newsletter image", width="600")
        p.append(img)
        insertion_point.insert(0, p)
    return str(soup)


def revise_with_feedback(original_email_html: str, feedback: str) -> Tuple[str, str]:
    system = (
        "You are an expert email writer and editor. Revise the provided newsletter HTML based on human feedback. "
        "If the feedback requests more detail or images, expand sections with concise, factual detail and include relevant inline <img src> elements (up to 3) using provided or inferred image URLs where appropriate. "
        "Preserve clean HTML with only <h2>, <h3>, <p>, <ul>, <li>, <a>, <img>. Sign off emails as TARS Group. "
        "Return two fields separated by a line '---SUBJECT---': first the revised subject (<=80 chars), then the revised HTML body."
        "Important: Do NOT include the word 'Source' or 'Sources' anywhere in your reply."
    )
    user = f"Email HTML:\n{original_email_html}\n\nFeedback from human:\n{feedback}"
    reply = simple_chat(system, user)
    if "---SUBJECT---" in reply:
        subject, body = reply.split("---SUBJECT---", 1)
        return _remove_source_tokens(subject.strip()), _remove_source_tokens(body.strip())
    return _sanitize_subject("Revised Newsletter"), reply.strip()


def enforce_on_topic_and_length(html_body: str, prompt: str, required_terms: List[str], target_words: Optional[int] = None) -> str:
    """If content is off-topic (missing required terms) or far from target word count, ask the LLM to revise."""
    # naive checks
    body_text = BeautifulSoup(html_body, "html5lib").get_text(" ")
    missing = [t for t in required_terms if t.lower() not in body_text.lower()]
    words = len(body_text.split())
    need_length_adjust = False
    if target_words:
        lower = int(target_words * 0.8)
        upper = int(target_words * 1.2)
        need_length_adjust = words < lower or words > upper
    if not missing and not need_length_adjust:
        return html_body

    instructions = [
        "Revise the newsletter HTML to strictly align with the user's brief and remain on-topic.",
        "Maintain citations with real clickable URLs and keep HTML tags limited to <h2>, <h3>, <p>, <ul>, <li>, <a>, <img>.",
    ]
    if missing:
        instructions.append(
            "Explicitly incorporate the following terms and relevant content where appropriate: " + ", ".join(missing)
        )
    if target_words:
        instructions.append(
            f"Aim for approximately {target_words} words (+/-10%). Summarize or expand with concrete, cited details as needed."
        )
    system = "You are an expert newsletter editor. Apply the instructions precisely without drifting off-topic. Return only revised HTML body."
    user = (
        "User brief:\n" + prompt + "\n\nCurrent HTML body:\n" + html_body + "\n\nInstructions:\n- " + "\n- ".join(instructions)
    )
    revised = simple_chat(system, user)
    return revised or html_body

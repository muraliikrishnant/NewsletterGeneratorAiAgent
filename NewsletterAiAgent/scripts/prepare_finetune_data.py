#!/usr/bin/env python3
"""Prepare fine-tuning datasets for the newsletter voice.

This script builds a provider-agnostic pairs file and a generic chat-style JSONL
from existing style examples and/or user-provided pairs.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Iterable, List, Dict


def _read_jsonl(path: str) -> List[Dict]:
    items = []
    if not path:
        return items
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def _load_style_examples(path: str) -> List[Dict[str, str]]:
    if not path or not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    examples = payload.get("examples", []) if isinstance(payload, dict) else []
    rows: List[Dict[str, str]] = []
    for ex in examples:
        if not isinstance(ex, dict):
            continue
        prompt = ex.get("prompt")
        output = ex.get("output")
        if prompt and output:
            rows.append({"input": prompt, "output": output})
    return rows


def _normalize_pairs(pairs: Iterable[Dict]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for item in pairs:
        if not isinstance(item, dict):
            continue
        inp = item.get("input") or item.get("prompt")
        outp = item.get("output") or item.get("completion")
        if isinstance(inp, str) and isinstance(outp, str):
            out.append({"input": inp.strip(), "output": outp.strip()})
    return out


def _write_jsonl(path: str, rows: Iterable[Dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare fine-tune datasets for the newsletter voice")
    parser.add_argument("--style-examples", default=None, help="Path to style_examples JSON (optional)")
    parser.add_argument("--pairs", default=None, help="Path to JSONL with {input, output} pairs (optional)")
    parser.add_argument("--out-dir", default="NewsletterAiAgent/training", help="Output directory")
    parser.add_argument("--system", default="Write in a blended Steven Bartlett + Alex Hormozi-inspired voice.", help="System prompt for chat JSONL")
    args = parser.parse_args()

    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)

    rows = []
    rows.extend(_load_style_examples(args.style_examples) if args.style_examples else [])
    rows.extend(_normalize_pairs(_read_jsonl(args.pairs)) if args.pairs else [])

    if not rows:
        raise SystemExit("No examples found. Provide --style-examples and/or --pairs.")

    # Provider-agnostic pairs
    pairs_path = os.path.join(out_dir, "finetune_pairs.jsonl")
    _write_jsonl(pairs_path, rows)

    # Generic chat JSONL (messages format)
    chat_rows = []
    for row in rows:
        chat_rows.append({
            "messages": [
                {"role": "system", "content": args.system},
                {"role": "user", "content": row["input"]},
                {"role": "assistant", "content": row["output"]},
            ]
        })
    chat_path = os.path.join(out_dir, "finetune_chat.jsonl")
    _write_jsonl(chat_path, chat_rows)

    print("Wrote:")
    print("-", pairs_path)
    print("-", chat_path)


if __name__ == "__main__":
    main()

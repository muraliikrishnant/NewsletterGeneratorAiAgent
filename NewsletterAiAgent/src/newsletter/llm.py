from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from .config import settings


@dataclass
class ChatMessage:
    role: str
    content: str


class OllamaClient:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.ollama_host).rstrip("/")
        self.model = model or settings.ollama_model

    def chat(self, messages: List[ChatMessage], temperature: float = 0.3, tools: Optional[List[Dict[str, Any]]] = None, stream: bool = False) -> str:
        url = f"{self.base_url}/api/chat"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [m.__dict__ for m in messages],
            "options": {"temperature": temperature},
            "stream": False,
            # Note: Ollama supports tool calling in newer versions; keep simple for portability
        }
        if tools:
            payload["tools"] = tools
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, data=json.dumps(payload), headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        # When stream=false, Ollama returns the final message under 'message'
        if isinstance(data, dict) and "message" in data and isinstance(data["message"], dict):
            return data["message"].get("content", "").strip()
        # Fallback for different shapes
        if isinstance(data, dict) and "content" in data:
            return str(data["content"]).strip()
        return str(data).strip()


def simple_chat(system: str, user: str) -> str:
    provider = (settings.llm_provider or "ollama").lower()
    if provider == "gemini":
        return _gemini_chat(system, user)
    # default: ollama
    client = OllamaClient()
    return client.chat([
        ChatMessage(role="system", content=system),
        ChatMessage(role="user", content=user),
    ])


# --- Gemini support ---
_gemini_client_cached = None

def _get_gemini_client():
    global _gemini_client_cached
    if _gemini_client_cached is not None:
        return _gemini_client_cached
    try:
        import google.generativeai as genai
    except Exception as e:
        raise RuntimeError("google-generativeai package is not installed. Run 'pip install google-generativeai'.") from e
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in .env")
    genai.configure(api_key=settings.gemini_api_key)
    _gemini_client_cached = genai
    return genai


def _gemini_chat(system: str, user: str) -> str:
    genai = _get_gemini_client()
    model_name = settings.gemini_model
    # Use system + user concatenated; newer SDK supports system instructions via content parts
    prompt = f"System:\n{system}\n\nUser:\n{user}"
    # Simple retry/backoff for transient 429s
    last_err = None
    for attempt in range(4):
        try:
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content(prompt)
            if hasattr(resp, 'text') and resp.text:
                return resp.text.strip()
            # fallback: concatenate parts
            try:
                parts = []
                for c in getattr(resp, 'candidates', []) or []:
                    for p in getattr(getattr(c, 'content', None), 'parts', []) or []:
                        t = getattr(p, 'text', '')
                        if t:
                            parts.append(t)
                return "\n".join(parts).strip()
            except Exception:
                return str(resp)
        except Exception as e:
            last_err = e
            msg = str(e)
            if '429' in msg or 'quota' in msg.lower():
                time.sleep(2 ** attempt)
                continue
            break
    raise RuntimeError(f"Gemini call failed: {last_err}")

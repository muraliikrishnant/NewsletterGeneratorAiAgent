from __future__ import annotations

import base64
import os
import time
from typing import List

import requests

from .config import settings


def _ensure_storage_dir() -> str:
    path = settings.image_storage_dir
    os.makedirs(path, exist_ok=True)
    return path


def _write_image(b64: str) -> str:
    folder = _ensure_storage_dir()
    ts = int(time.time() * 1000)
    name = f"img_{ts}.png"
    filepath = os.path.join(folder, name)
    raw = base64.b64decode(b64)
    with open(filepath, "wb") as f:
        f.write(raw)
    return name


def generate_images(prompt: str, n: int | None = None) -> List[str]:
    """Generate images via local AUTOMATIC1111 WebUI and return hosted URLs."""
    if settings.image_provider.lower() != "auto1111":
        return []
    if not settings.image_base_url:
        # Without a public base URL, email clients won't be able to render the images.
        return []

    count = n or max(1, settings.image_count)
    url = settings.auto1111_url.rstrip("/") + "/sdapi/v1/txt2img"
    payload = {
        "prompt": prompt,
        "steps": settings.image_steps,
        "cfg_scale": settings.image_cfg_scale,
        "sampler_name": settings.image_sampler,
        "width": settings.image_width,
        "height": settings.image_height,
        "batch_size": count,
        "n_iter": 1,
    }

    resp = requests.post(url, json=payload, timeout=180)
    resp.raise_for_status()
    data = resp.json()
    images = data.get("images", []) if isinstance(data, dict) else []

    out: List[str] = []
    for b64 in images:
        if not isinstance(b64, str):
            continue
        filename = _write_image(b64.strip())
        out.append(settings.image_base_url.rstrip("/") + f"/images/{filename}")
    return out

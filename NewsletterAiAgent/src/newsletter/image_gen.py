from __future__ import annotations

import base64
from typing import List

import requests

from .config import settings


def generate_images(prompt: str, n: int | None = None) -> List[str]:
    """Generate images via local AUTOMATIC1111 WebUI and return data-URI strings.

    Note: data-URI images render in the preview but may be blocked by some email clients.
    """
    if settings.image_provider.lower() != "auto1111":
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
        # some A1111 configs return base64 without data-uri header
        # add a PNG data-uri prefix
        out.append("data:image/png;base64," + b64.strip())
    return out

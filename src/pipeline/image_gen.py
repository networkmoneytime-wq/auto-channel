"""Cloudflare Workers AI (free tier: 10,000 Neurons/day, no subscription,
verified directly against Cloudflare's own pricing page before building
this) — real AI image generation for the meme channel's AI-character
brainrot format (Italian-Brainrot-style surreal creature/object art). This
is the one content type in this project that's actually AI-generated rather
than sourced; see feedback_sourced_not_generated_images for why every other
channel deliberately avoids this and script_gen_meme.py for why this format
is the named exception."""

from __future__ import annotations

import base64
from pathlib import Path

import requests

from src.config import env

MODEL = "@cf/black-forest-labs/flux-1-schnell"


def generate_image(prompt: str, dest: Path) -> bool:
    """Renders `prompt` to a 1024x1024 JPEG at `dest`. Returns False instead
    of raising on any failure — one bad generation shouldn't take down the
    whole video."""
    try:
        resp = requests.post(
            f"https://api.cloudflare.com/client/v4/accounts/{env('CLOUDFLARE_ACCOUNT_ID')}/ai/run/{MODEL}",
            headers={"Authorization": f"Bearer {env('CLOUDFLARE_API_TOKEN')}"},
            json={"prompt": prompt},
            timeout=60,
        )
    except requests.RequestException as e:
        print(f"[image_gen] request failed: {e}")
        return False

    if not resp.ok:
        print(f"[image_gen] request failed: {resp.status_code} {resp.text[:300]}")
        return False

    image_b64 = resp.json().get("result", {}).get("image")
    if not image_b64:
        print(f"[image_gen] no image in response: {resp.text[:300]}")
        return False

    dest.write_bytes(base64.b64decode(image_b64))
    return True

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
import subprocess
from pathlib import Path

import requests

from src.config import env

MODEL = "@cf/black-forest-labs/flux-1-schnell"

# Every channel renders 1080x1920; flux-1-schnell rejects custom sizes and
# always returns a 1024x1024 square.
FRAME_W, FRAME_H = 1080, 1920


def _frame_for_portrait(path: Path) -> None:
    """Centers the full square over a blurred, dimmed copy of itself scaled to
    fill the frame. The assembler's default crop-to-fill would keep only the
    middle 56% of a square's width and routinely cuts off the character's head
    or tail (seen on the first dry run: a camel decapitated at the right
    edge); this keeps the whole subject. On any failure the raw square is left
    in place -- worse framing beats losing the video."""
    framed = path.with_name(path.stem + "_framed.jpg")
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
                "-filter_complex",
                f"[0:v]split[a][b];"
                f"[a]scale={FRAME_W}:{FRAME_H}:force_original_aspect_ratio=increase,"
                f"crop={FRAME_W}:{FRAME_H},boxblur=40:10,eq=brightness=-0.1[bg];"
                f"[b]scale={FRAME_W}:{FRAME_W}[fg];"
                f"[bg][fg]overlay=0:(H-h)/2",
                "-frames:v", "1", "-q:v", "2", str(framed),
            ],
            check=True, capture_output=True, text=True, timeout=60,
        )
        framed.replace(path)
    except (subprocess.SubprocessError, OSError) as e:
        print(f"[image_gen] portrait framing failed, keeping the raw square: {(getattr(e, 'stderr', None) or e)!s:.300}")


def generate_image(prompt: str, dest: Path) -> bool:
    """Renders `prompt` to a JPEG at `dest`, framed for a 9:16 video (see
    _frame_for_portrait). Returns False instead of raising on any failure —
    one bad generation shouldn't take down the whole video."""
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
    _frame_for_portrait(dest)
    return True

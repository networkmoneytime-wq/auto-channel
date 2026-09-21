from pathlib import Path

import requests

from src.config import env

GRAPH_VIDEO = "https://graph-video.facebook.com/v19.0"


def upload_short(video_path: Path, metadata: dict, config: dict) -> str:
    token = env("IG_ACCESS_TOKEN")  # same Page-scoped token used for Instagram
    page_id = env("FB_PAGE_ID")
    caption = metadata["description"] + " " + " ".join(metadata["hashtags"])

    with open(video_path, "rb") as f:
        resp = requests.post(
            f"{GRAPH_VIDEO}/{page_id}/videos",
            data={
                "access_token": token,
                "description": caption[:5000],
                "title": metadata["title"][:255],
            },
            files={"source": (video_path.name, f, "video/mp4")},
            timeout=180,
        )
    if not resp.ok:
        print(f"[facebook] upload failed: {resp.status_code} {resp.text}")
    resp.raise_for_status()
    return resp.json()["id"]

import time
from pathlib import Path

import requests

from src.config import env

GRAPH = "https://graph.facebook.com/v19.0"


def upload_short(video_path: Path, metadata: dict, config: dict) -> str:
    token = env("IG_ACCESS_TOKEN")
    ig_user_id = env("IG_USER_ID")
    caption = metadata["description"] + " " + " ".join(metadata["hashtags"])
    video_size = video_path.stat().st_size

    create_resp = requests.post(
        f"{GRAPH}/{ig_user_id}/media",
        data={
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption[:2200],
            "access_token": token,
        },
        timeout=30,
    )
    create_resp.raise_for_status()
    create_data = create_resp.json()
    container_id = create_data["id"]
    upload_uri = create_data["uri"]

    with open(video_path, "rb") as f:
        video_bytes = f.read()
    requests.post(
        upload_uri,
        headers={
            "Authorization": f"OAuth {token}",
            "offset": "0",
            "file_size": str(video_size),
        },
        data=video_bytes,
        timeout=180,
    ).raise_for_status()

    for _ in range(30):
        status = requests.get(
            f"{GRAPH}/{container_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        ).json()
        if status.get("status_code") == "FINISHED":
            break
        if status.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram container processing failed: {status}")
        time.sleep(5)
    else:
        raise TimeoutError("Instagram container did not finish processing in time")

    publish_resp = requests.post(
        f"{GRAPH}/{ig_user_id}/media_publish",
        data={"creation_id": container_id, "access_token": token},
        timeout=30,
    )
    publish_resp.raise_for_status()
    return publish_resp.json()["id"]

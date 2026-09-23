import time
from pathlib import Path

import requests

from src.config import env

GRAPH = "https://graph.facebook.com/v19.0"

# Instagram's resumable-upload step occasionally rejects a perfectly valid
# video with a generic 400 ProcessingFailedError — confirmed intermittent
# (roughly 1 in 3 runs, going back days, independent of anything in this
# pipeline) rather than tied to a specific video. Meta marks it
# "retriable: false", but that describes resubmitting the same container,
# not a fresh one — a new create/upload/publish cycle from scratch has a
# real chance of succeeding where the first attempt didn't.
# At a ~1-in-3 per-attempt failure rate, 3 attempts still means ~1 in 27
# runs sees all of them fail (confirmed happening 2026-09-23, anime channel)
# -- 5 attempts brings that down to roughly 1 in 240.
_RETRY_ATTEMPTS = 5
_RETRY_DELAY = 5


def upload_short(video_path: Path, metadata: dict, config: dict) -> str:
    last_error = None
    for attempt in range(_RETRY_ATTEMPTS):
        if attempt:
            time.sleep(_RETRY_DELAY)
        try:
            return _upload_attempt(video_path, metadata)
        except (requests.exceptions.HTTPError, RuntimeError, TimeoutError) as e:
            last_error = e
            print(f"[instagram] attempt {attempt + 1}/{_RETRY_ATTEMPTS} failed: {e}")
    raise last_error


def _upload_attempt(video_path: Path, metadata: dict) -> str:
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
    if not create_resp.ok:
        print(f"[instagram] media create failed: {create_resp.status_code} {create_resp.text}")
    create_resp.raise_for_status()
    create_data = create_resp.json()
    container_id = create_data["id"]
    upload_uri = create_data["uri"]

    with open(video_path, "rb") as f:
        video_bytes = f.read()
    upload_resp = requests.post(
        upload_uri,
        headers={
            "Authorization": f"OAuth {token}",
            "offset": "0",
            "file_size": str(video_size),
        },
        data=video_bytes,
        timeout=180,
    )
    if not upload_resp.ok:
        print(f"[instagram] video upload failed: {upload_resp.status_code} {upload_resp.text}")
    upload_resp.raise_for_status()

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
    if not publish_resp.ok:
        print(f"[instagram] publish failed: {publish_resp.status_code} {publish_resp.text}")
    publish_resp.raise_for_status()
    return publish_resp.json()["id"]

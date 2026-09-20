from pathlib import Path

import requests

from src.config import env


def _access_token() -> str:
    resp = requests.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": env("TIKTOK_CLIENT_KEY"),
            "client_secret": env("TIKTOK_CLIENT_SECRET"),
            "grant_type": "refresh_token",
            "refresh_token": env("TIKTOK_REFRESH_TOKEN"),
        },
        timeout=30,
    )
    if not resp.ok:
        print(f"[tiktok] token refresh failed: {resp.status_code} {resp.text}")
    resp.raise_for_status()
    return resp.json()["access_token"]


def upload_short(video_path: Path, metadata: dict, config: dict) -> str:
    token = _access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}
    video_size = video_path.stat().st_size
    caption = metadata["description"] + " " + " ".join(metadata["hashtags"])

    init_resp = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers=headers,
        json={
            "post_info": {
                "title": caption[:2200],
                "privacy_level": config["platforms"]["tiktok"]["privacy"],
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size,
                "total_chunk_count": 1,
            },
        },
        timeout=30,
    )
    if not init_resp.ok:
        print(f"[tiktok] publish init failed: {init_resp.status_code} {init_resp.text}")
    init_resp.raise_for_status()
    init_data = init_resp.json()["data"]

    with open(video_path, "rb") as f:
        video_bytes = f.read()
    put_resp = requests.put(
        init_data["upload_url"],
        headers={
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
        },
        data=video_bytes,
        timeout=120,
    )
    if not put_resp.ok:
        print(f"[tiktok] file upload failed: {put_resp.status_code} {put_resp.text}")
    put_resp.raise_for_status()

    return init_data["publish_id"]

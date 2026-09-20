import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# The original channel keeps its files at the old top-level paths and its
# secrets unnamespaced, so setting no CHANNEL env var reproduces the exact
# behavior this pipeline had before multi-channel support existed.
DEFAULT_CHANNEL = "dailyap"

# Only credentials that identify a specific platform account get namespaced
# per channel. Shared API keys (LLM, stock footage) stay global. TikTok's
# client key/secret identify the developer app, not the posting account —
# one app can hold OAuth grants for many accounts — so only its refresh
# token varies per channel; YouTube needs its own OAuth client per channel
# for separate quota, and Instagram's access token is tied to a specific
# Business account, so both vary per channel.
PER_CHANNEL_SECRETS = {
    "YOUTUBE_CLIENT_ID",
    "YOUTUBE_CLIENT_SECRET",
    "YOUTUBE_REFRESH_TOKEN",
    "TIKTOK_REFRESH_TOKEN",
    "IG_ACCESS_TOKEN",
    "IG_USER_ID",
}


def channel() -> str:
    return os.environ.get("CHANNEL", DEFAULT_CHANNEL)


def _channel_dir() -> Path:
    return ROOT / "config" / "channels" / channel()


def load_config() -> dict:
    ch = channel()
    path = ROOT / "config" / "config.yaml" if ch == DEFAULT_CHANNEL else _channel_dir() / "config.yaml"
    with open(path) as f:
        cfg = yaml.safe_load(f)
    cfg["_root"] = str(ROOT)
    return cfg


def env(name: str, required: bool = True) -> str:
    ch = channel()
    lookup = f"{name}_{ch.upper()}" if ch != DEFAULT_CHANNEL and name in PER_CHANNEL_SECRETS else name
    val = os.environ.get(lookup, "")
    if required and not val:
        raise RuntimeError(f"Missing required environment variable: {lookup}")
    return val


def topics_path() -> Path:
    ch = channel()
    return ROOT / "config" / "topics.txt" if ch == DEFAULT_CHANNEL else _channel_dir() / "topics.txt"


def output_dir() -> Path:
    d = ROOT / "output"
    d.mkdir(exist_ok=True)
    return d


def state_path() -> Path:
    ch = channel()
    if ch == DEFAULT_CHANNEL:
        d = ROOT / "state"
        d.mkdir(exist_ok=True)
        return d / "state.json"
    d = ROOT / "state" / ch
    d.mkdir(parents=True, exist_ok=True)
    return d / "state.json"

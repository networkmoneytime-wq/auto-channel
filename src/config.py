import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def load_config() -> dict:
    with open(ROOT / "config" / "config.yaml") as f:
        cfg = yaml.safe_load(f)
    cfg["_root"] = str(ROOT)
    return cfg


def env(name: str, required: bool = True) -> str:
    val = os.environ.get(name, "")
    if required and not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


def topics_path() -> Path:
    return ROOT / "config" / "topics.txt"


def output_dir() -> Path:
    d = ROOT / "output"
    d.mkdir(exist_ok=True)
    return d


def state_path() -> Path:
    d = ROOT / "state"
    d.mkdir(exist_ok=True)
    return d / "state.json"

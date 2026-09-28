"""Turns each channel's own upload history into a small performance digest —
which hook archetype actually gets more views, and which real topics won or
lost — so the pipeline can lean toward what's already working instead of
picking blind every time.

Recomputed fresh from scratch every run rather than updated incrementally:
Facebook view counts change after the fact as a video keeps getting seen, a
handful of Graph API calls is cheap, and recomputing means there's no running
average to drift or "already scored" bookkeeping to get wrong on a retry.

Facebook is the only source (not YouTube): its Graph API works from anywhere,
including GitHub-hosted runners, with the token this pipeline already holds
— YouTube's real view counts need yt-dlp against a residential IP, which
GitHub's runners are blocked from (see reference_auto_channel_ci_ops
memory), so that stays a manual, local enrichment for now, not something the
scheduled workflow can do itself.

Only uploads logged with a `topic`/`hook_id` (see src/state.py's log_upload)
can be attributed — every upload before this shipped has neither, so scoring
starts from whenever this lands, not retroactively."""

from __future__ import annotations

import requests

from src.config import env

# A hook/topic needs to have actually been seen by someone before its view
# count means anything; Facebook's own view counts also aren't reliable in
# the first hour or two after posting. Below this, treat the video as
# "not scored yet" rather than let an early near-zero drag its average down.
MIN_VIEWS_TO_COUNT = 3

# How many of the channel's most recent Facebook uploads to re-check per run.
# Bounds both the API calls and the run's added wall-clock time.
MAX_SCORED = 40

# Module-level cache: set once per process by refresh(), read by
# hooks.pick_hook(). A run_local_server-free, no-signature-change way for a
# deep call (pick_hook, called from inside each channel's own script
# generator) to see this run's digest without threading a new parameter
# through every script_gen_*.py.
_CURRENT: dict = {}


def _fb_views(video_id: str) -> int | None:
    try:
        resp = requests.get(
            f"https://graph.facebook.com/v21.0/{video_id}",
            params={"fields": "views", "access_token": env("IG_ACCESS_TOKEN")},
            timeout=20,
        )
        if not resp.ok:
            return None
        return resp.json().get("views")
    except requests.RequestException:
        return None


def build_digest(state: dict) -> dict:
    """{"hooks": {hook_id: avg_views}, "topic_examples": [{"topic","views"}, ...]}
    from this channel's own Facebook uploads. Never raises — a Graph API
    hiccup here should cost this run a learning signal, not the video."""
    scored = []
    try:
        candidates = [u for u in state.get("uploads", []) if u.get("platform") == "facebook" and u.get("topic")]
        for u in candidates[-MAX_SCORED:]:
            views = _fb_views(u["video_id"])
            if views is not None and views >= MIN_VIEWS_TO_COUNT:
                scored.append({"topic": u["topic"], "hook_id": u.get("hook_id"), "views": views})
    except Exception as e:  # noqa: BLE001 - a learning signal is never worth losing the video over
        print(f"[performance] digest build failed, continuing without one: {e!r}")
        return {"hooks": {}, "topic_examples": []}

    hooks: dict[str, list[int]] = {}
    for s in scored:
        if s["hook_id"]:
            hooks.setdefault(s["hook_id"], []).append(s["views"])
    hook_avgs = {h: sum(v) / len(v) for h, v in hooks.items()}

    ranked = sorted(scored, key=lambda s: -s["views"])
    topic_examples = ranked[:5] + (ranked[-3:] if len(ranked) > 8 else [])

    return {"hooks": hook_avgs, "topic_examples": topic_examples}


def refresh(state: dict) -> dict:
    global _CURRENT
    _CURRENT = build_digest(state)
    if _CURRENT["hooks"] or _CURRENT["topic_examples"]:
        print(f"[performance] {len(_CURRENT['topic_examples'])} scored topic(s), hook averages: {_CURRENT['hooks']}")
    else:
        print("[performance] no scored data yet (needs a facebook upload with a recorded topic)")
    return _CURRENT


def current() -> dict:
    return _CURRENT

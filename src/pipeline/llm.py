import json
import re
import time

import requests

from src.config import env

# Groq's free tier has real, easy-to-hit capacity limits — a 429 is the
# obvious case, but a momentary capacity squeeze has also surfaced as a
# plain 400 in practice. Both are worth a few quiet retries rather than
# failing the whole channel's run outright.
#
# The limit that actually bites is tokens per minute (8,000 for this model on
# the free tier), and it is shared by every run at once: dailyap and the first
# matrix channel start on the same cron tick, and a test run alongside them
# tips it over. The old schedule (2s, then 5s) gave up long before a
# one-minute window could clear, and three test runs failed that way. Groq's
# 429s say how long to wait ("Please try again in 6.1s"), so wait that long.
_RETRY_STATUS = {400, 429, 500, 502, 503, 504}
_RETRY_DELAYS = [2, 5, 15, 30]
_MAX_HINTED_WAIT = 60


def _wait_hint(resp) -> float:
    """Seconds Groq says to wait before retrying, or 0 if it doesn't say."""
    header = resp.headers.get("retry-after", "")
    try:
        return float(header)
    except ValueError:
        pass
    m = re.search(r"try again in ([0-9.]+)\s*(ms|s)\b", resp.text or "")
    if not m:
        return 0.0
    return float(m.group(1)) / (1000 if m.group(2) == "ms" else 1)


def chat_json(system: str, user: str, model: str) -> dict:
    """Call Groq's free-tier chat completions API and parse a JSON object response."""
    last_resp = None
    hinted = 0.0
    for attempt, delay in enumerate([0, *_RETRY_DELAYS]):
        wait = max(delay, min(hinted + 0.5, _MAX_HINTED_WAIT)) if delay else 0
        if wait:
            time.sleep(wait)
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {env('GROQ_API_KEY')}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.8,
            },
            timeout=60,
        )
        if resp.ok:
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        last_resp = resp
        if resp.status_code not in _RETRY_STATUS:
            break
        hinted = _wait_hint(resp)
        print(f"[llm] attempt {attempt + 1} failed: {resp.status_code} {resp.text[:300]}")

    print(f"[llm] chat_json failed: {last_resp.status_code} {last_resp.text[:500]}")
    last_resp.raise_for_status()

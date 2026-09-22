import json
import time

import requests

from src.config import env

# Groq's free tier has real, easy-to-hit capacity limits — a 429 is the
# obvious case, but a momentary capacity squeeze has also surfaced as a
# plain 400 in practice. Both are worth one quiet retry rather than failing
# the whole channel's run outright.
_RETRY_STATUS = {400, 429, 500, 502, 503, 504}
_RETRY_DELAYS = [2, 5]


def chat_json(system: str, user: str, model: str) -> dict:
    """Call Groq's free-tier chat completions API and parse a JSON object response."""
    last_resp = None
    for attempt, delay in enumerate([0, *_RETRY_DELAYS]):
        if delay:
            time.sleep(delay)
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
        print(f"[llm] attempt {attempt + 1} failed: {resp.status_code} {resp.text[:300]}")

    print(f"[llm] chat_json failed: {last_resp.status_code} {last_resp.text[:500]}")
    last_resp.raise_for_status()

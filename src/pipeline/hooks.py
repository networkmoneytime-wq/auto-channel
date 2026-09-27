"""Hook-opening archetypes the script prompt rotates through.

Previously every script used one fixed opening rule (lead with the most
shocking fact). 2026 short-form retention research points to a handful of
hook shapes that all outperform a plain "surprising fact" lead — but any
single shape repeated on every upload reads as a pattern to both viewers and
the algorithm and plateaus faster than an account that varies it. Rotating
the archetype keeps the required discipline (land the hook in sentence one,
no windup) while varying its shape upload to upload.
"""

import random

from src.pipeline import performance

HOOKS = [
    {
        "id": "shocking_fact",
        "instruction": (
            "Open with the single most surprising or shocking part of the topic as "
            'the very first sentence. No slow windups, no "did you know", no '
            "throat-clearing — start mid-punch."
        ),
    },
    {
        "id": "contrarian_claim",
        "instruction": (
            "Open by stating what most people believe about the topic, then "
            "immediately contradict it in the same breath (e.g. \"Everyone thinks "
            "__. They're wrong.\") — the contradiction itself is the first sentence, "
            "not a setup before it."
        ),
    },
    {
        "id": "mistake_warning",
        "instruction": (
            "Open by calling out a common misconception tied to the topic, "
            "directed straight at the viewer (e.g. \"If you think __, you've been "
            'misled"). Land the correction immediately — don\'t explain before '
            "revealing it."
        ),
    },
    {
        "id": "list_tease",
        "instruction": (
            "Open by teasing a count without giving away any item yet (e.g. "
            '"Here are the __ things about this that sound fake but aren\'t"), '
            "promising the most striking one is saved for last."
        ),
    },
    {
        "id": "secret_reveal",
        "instruction": (
            "Open by framing the topic as something hidden or rarely told (e.g. "
            '"Nobody tells you this about __" / "The part they leave out is __"), '
            "then immediately deliver the hidden part — don't just promise it."
        ),
    },
    {
        "id": "question_hook",
        "instruction": (
            "Open with a single provocative question that creates a curiosity gap "
            "the rest of the script closes — the question itself must be the first "
            "sentence, answered only by watching."
        ),
    },
]


def pick_hook(state: dict) -> dict:
    """Avoid repeating either of the last two hooks used on this channel, and
    among what's left, lean toward whichever archetype has actually earned
    more views on this channel (src/pipeline/performance.py) — still
    genuinely random, not just "always the current best", so an
    under-sampled or unlucky-early hook keeps getting real tries instead of
    being written off on thin data."""
    recent = state.get("recent_hooks", [])[-2:]
    candidates = [h for h in HOOKS if h["id"] not in recent] or HOOKS

    hook_avgs = performance.current().get("hooks", {})
    if not hook_avgs:
        return random.choice(candidates)  # no scored data yet: uniform, same as before this existed

    overall = sum(hook_avgs.values()) / len(hook_avgs)
    weights = [max(hook_avgs.get(h["id"], overall), 1.0) for h in candidates]
    return random.choices(candidates, weights=weights, k=1)[0]

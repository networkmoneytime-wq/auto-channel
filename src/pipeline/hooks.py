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
    """Avoid repeating either of the last two hooks used on this channel."""
    recent = state.get("recent_hooks", [])[-2:]
    candidates = [h for h in HOOKS if h["id"] not in recent] or HOOKS
    return random.choice(candidates)

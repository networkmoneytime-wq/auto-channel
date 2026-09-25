"""Decorative "brainrot"-style backdrop for the meme channel's plain-topic
format: hypnotic, high-motion vertical stock footage (neon tunnels, slime,
car drifting, parkour...) cutting under narration and burned captions. The
visual is background texture, never tied to what the script says, so there's
no per-script keyword search -- just a rotation of queries that reliably
return eye-holding footage.

This replaced an earlier design that pulled real gameplay compilations
(Subway Surfers, Minecraft parkour) via yt-dlp. Abandoned 2026-09-25:
YouTube answers GitHub-hosted runners with "Sign in to confirm you're not a
bot" for every video (confirmed by a manual CI run of all five curated
sources, both format strings), and even from a residential IP the stream
URLs get cut off after ~20 MB without a PO token, so there was no reliable
way to fetch the footage at run time or to pre-cut it once. Pexels is
already integrated and its license needs no attribution. If real gameplay is
ever wanted again, the clean path is footage the owner records themselves."""

from __future__ import annotations

import random

# Chosen by eyeballing Pexels' actual portrait results for each query, not by
# guessing: these all came back hypnotic and vertical. Queries that sounded
# right but returned people posing or off-topic clips ("domino", "marble
# run", "video game", "kinetic sand") were dropped.
BACKDROP_QUERIES = [
    "neon tunnel",
    "slime",
    "car drifting",
    "parkour",
    "colorful liquid",
    "arcade",
]


def backdrop_keywords(n: int) -> list[str]:
    """`n` decorative visual keywords, drawn in shuffled passes over the whole
    list so a query doesn't repeat until every other one has been used (and
    never twice in a row, including across the seam between two passes)."""
    keywords: list[str] = []
    while len(keywords) < n:
        cycle = BACKDROP_QUERIES[:]
        random.shuffle(cycle)
        if keywords and cycle[0] == keywords[-1]:
            cycle[0], cycle[-1] = cycle[-1], cycle[0]
        keywords.extend(cycle)
    return keywords[:n]

from src.config import topics_path


def pick_topic(state: dict) -> str:
    lines = [
        line.strip()
        for line in topics_path().read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    # Never-used topics come first, in file order. Once every line has been
    # used, the one used longest ago goes next. (The old fallback was
    # `unused = lines; return unused[0]`, which returned the first line on
    # every run after exhaustion: cars and anime ended up re-posting their
    # first topic three times a day.)
    last_used = {t: i for i, t in enumerate(state.get("used_topics", []))}
    return min(lines, key=lambda t: last_used.get(t, -1))

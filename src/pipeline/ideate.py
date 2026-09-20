from src.config import topics_path


def pick_topic(state: dict) -> str:
    lines = [
        line.strip()
        for line in topics_path().read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    used = set(state.get("used_topics", []))
    unused = [t for t in lines if t not in used]
    if not unused:
        # every seed topic has been used — start the rotation over
        unused = lines
    return unused[0]

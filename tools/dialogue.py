"""Read and validate dialogue text files (see assets/dialogue/greetings.txt)."""

LINE_CHARS = 12
MAX_SCREEN_LINES = 2
ALPHABET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?-$%'/:+")


def parse_greetings(text):
    """Return {section: [[screen line, ...], ...]}; raise ValueError on bad input."""
    sections = {}
    current = None
    for num, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            if current in sections:
                raise ValueError(f"line {num}: duplicate section [{current}]")
            sections[current] = []
            continue
        if current is None:
            raise ValueError(f"line {num}: greeting before any [section]")
        screen_lines = [part.strip() for part in line.split(" / ")]
        if len(screen_lines) > MAX_SCREEN_LINES:
            raise ValueError(f"line {num}: more than {MAX_SCREEN_LINES} screen lines")
        for part in screen_lines:
            if len(part) > LINE_CHARS:
                raise ValueError(f"line {num}: '{part}' is {len(part)} chars (max {LINE_CHARS})")
            bad = set(part) - ALPHABET
            if bad:
                raise ValueError(f"line {num}: unsupported characters {sorted(bad)}")
        sections[current].append(screen_lines)
    return sections

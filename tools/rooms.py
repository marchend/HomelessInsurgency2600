"""Parse and validate the city map (assets/rooms/city.txt)."""

ROWS = COLS = 8


def pattern_cols(mode, half):
    """Full 40-column band from a 20-column half: True = building."""
    left = [ch == "#" for ch in half]
    right = left[::-1] if mode == "M" else left[:]
    return left + right


def parse_city(text):
    patterns, rooms, start = {}, [], None
    section = None
    for num, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip() if raw.lstrip().startswith("#") else raw.rstrip()
        if not line.strip():
            continue
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if section == "patterns":
            parts = line.split()
            if len(parts) != 3:
                raise ValueError(f"line {num}: expected 'name mode half'")
            name, mode, half = parts
            if mode not in ("M", "R"):
                raise ValueError(f"line {num}: mode must be M or R")
            if len(half) != 20 or set(half) - set("#."):
                raise ValueError(f"line {num}: half must be 20 chars of '#' and '.'")
            if half[0] != "#":
                raise ValueError(f"line {num}: column 0 must be a building")
            patterns[name] = (mode, half)
        elif section == "map":
            row = []
            for tok in line.split():
                bands, _, sign = tok.partition(":")
                if len(bands) != 3:
                    raise ValueError(f"line {num}: room '{tok}' needs 3 band patterns")
                if sign not in ("", "S", "F"):
                    raise ValueError(f"line {num}: unknown sign '{sign}'")
                row.append({"bands": list(bands), "sign": sign})
            if len(row) != COLS:
                raise ValueError(f"line {num}: map row needs {COLS} rooms, has {len(row)}")
            rooms.append(row)
        elif section == "start":
            r, c = (int(v) for v in line.split())
            start = (r, c)
        else:
            raise ValueError(f"line {num}: text outside a section")
    if len(rooms) != ROWS:
        raise ValueError(f"map needs {ROWS} rows, has {len(rooms)}")
    for r, row in enumerate(rooms):
        for c, room in enumerate(row):
            for name in room["bands"]:
                if name not in patterns:
                    raise ValueError(f"room {r},{c}: unknown pattern '{name}'")
    for r in range(ROWS - 1):
        for c in range(COLS):
            below = pattern_cols(*patterns[rooms[r][c]["bands"][2]])
            above = pattern_cols(*patterns[rooms[r + 1][c]["bands"][0]])
            if below != above:
                raise ValueError(
                    f"rooms {r},{c} and {r + 1},{c}: bottom band "
                    f"'{rooms[r][c]['bands'][2]}' doesn't line up with top band "
                    f"'{rooms[r + 1][c]['bands'][0]}'")
    if start is None:
        raise ValueError("missing [start]")
    return patterns, rooms, start

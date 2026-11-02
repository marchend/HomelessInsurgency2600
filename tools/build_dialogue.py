"""Turn encounter text into ROM tables.

Every distinct 12-character screen line becomes one string: 12 glyph offsets
(character code * 5) so the encounter kernel can compose a line quickly.
Greetings are grouped by person kind and temperament; choices by kind.
"""
import os

from dialogue import LINE_CHARS, parse_greetings

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

CHARSET = " 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.,!?-$%'/:+"

KINDS = ["homeless", "police", "passerby"]
TEMPERAMENTS = {
    "homeless": ["calm_rational", "calm_irrational", "angry_rational", "angry_irrational"],
    "police": ["calm", "less_calm", "angry", "really_angry"],
    "passerby": ["patient", "less_patient", "impatient", "angry_impatient"],
}
CHOICES = {
    "homeless": ["I'M ONE OF U", "SHARE FOOD", "BIG PLAN...", "WALK AWAY"],
    "police": ["ASK CHANGE", "ASK SHELTER", "YELL AT COP", "ATTACK"],
    "passerby": ["ASK CHANGE", "ROB", "WALK AWAY"],
}
HEADERS = {"homeless": "HOMELESS", "police": "POLICE", "passerby": "PASSERBY"}


class Strings:
    """Interned screen lines. Id 0 is the blank line."""

    def __init__(self):
        self.lines = []
        self.ids = {}
        self.add("", center=True)

    def add(self, text, center):
        assert len(text) <= LINE_CHARS, text
        padded = text.center(LINE_CHARS) if center else text.ljust(LINE_CHARS)
        if padded not in self.ids:
            self.ids[padded] = len(self.lines)
            self.lines.append(padded)
        return self.ids[padded]

    def glyph_offsets(self, sid):
        return [CHARSET.index(ch) * 5 for ch in self.lines[sid]]


def build():
    """Return (strings, greet_tables, choice_ids) for the asset builder."""
    with open(os.path.join(ROOT, "assets", "dialogue", "greetings.txt")) as f:
        greetings = parse_greetings(f.read())
    strings = Strings()
    greet_start, greet_count, line1, line2 = [], [], [], []
    for kind in KINDS:
        for temp in TEMPERAMENTS[kind]:
            pool = greetings[f"{kind}.{temp}"]
            greet_start.append(len(line1))
            greet_count.append(len(pool))
            for g in pool:
                line1.append(strings.add(g[0], center=True))
                line2.append(strings.add(g[1], center=True) if len(g) > 1 else 0)
    choice_ids = {kind: [strings.add(c, center=False) for c in CHOICES[kind]] for kind in KINDS}
    assert len(strings.lines) < 256 and len(line1) < 256
    greet = {"start": greet_start, "count": greet_count, "line1": line1, "line2": line2}
    return strings, greet, choice_ids

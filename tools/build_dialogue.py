"""Turn encounter text and outcome odds into ROM tables.

Every distinct 12-character screen line becomes one string: 12 glyph offsets
(character code * 5) so the encounter kernel can compose a line quickly.
Greetings come from assets/dialogue/greetings.txt; choices, outcomes, food
and fixed messages from assets/outcomes.py.
"""
import os
import sys

from dialogue import LINE_CHARS, parse_greetings

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "assets"))

import outcomes as data  # noqa: E402

CHARSET = " 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.,!?-$%'/:+"

# Encounter kinds in ROM order (ENC_* in ram.h).
KINDS = ["homeless", "police", "passerby"]
SCREEN_KINDS = KINDS + ["food", "jail"]
TEMPERAMENTS = {
    "homeless": ["calm_rational", "calm_irrational", "angry_rational", "angry_irrational"],
    "police": ["calm", "less_calm", "angry", "really_angry"],
    "passerby": ["patient", "less_patient", "impatient", "angry_impatient"],
}
CHOICES = data.CHOICES
HEADERS = {"homeless": "HOMELESS", "police": "POLICE", "passerby": "PASSERBY",
           "food": "FOOD", "jail": "JAIL"}

FLAG_SHELTER, FLAG_OUTSKIRTS, FLAG_COMBAT, FLAG_LEAVE = 1, 2, 4, 8


def bcd(cents):
    dollars, c = divmod(cents, 100)
    assert dollars < 100
    return ((dollars // 10) << 4) | dollars % 10, ((c // 10) << 4) | c % 10


class Strings:
    """Interned screen lines. Id 0 is the blank line."""

    def __init__(self):
        self.lines = []
        self.ids = {}
        self.add("", center=True)

    def add(self, text, center=True):
        assert len(text) <= LINE_CHARS, text
        padded = text.center(LINE_CHARS) if center else text.ljust(LINE_CHARS)
        if padded not in self.ids:
            self.ids[padded] = len(self.lines)
            self.lines.append(padded)
        return self.ids[padded]

    def glyph_offsets(self, sid):
        return [CHARSET.index(ch) * 5 for ch in self.lines[sid]]


def build():
    """Everything the asset builder needs, as a dict of tables."""
    with open(os.path.join(ROOT, "assets", "dialogue", "greetings.txt")) as f:
        greetings = parse_greetings(f.read())
    strings = Strings()
    out = {"strings": strings, "equates": {}}

    # greetings: pool per kind * 4 + temperament
    greet = {"start": [], "count": [], "line1": [], "line2": []}
    for kind in KINDS:
        for temp in TEMPERAMENTS[kind]:
            pool = greetings[f"{kind}.{temp}"]
            greet["start"].append(len(greet["line1"]))
            greet["count"].append(len(pool))
            for g in pool:
                greet["line1"].append(strings.add(g[0]))
                greet["line2"].append(strings.add(g[1]) if len(g) > 1 else 0)
    out["greet"] = greet

    # choices per screen kind (food menu is kind 3)
    choice_ids = {kind: [strings.add(c, center=False) for c in CHOICES[kind]] for kind in KINDS}
    choice_ids["food"] = [strings.add(m["choice"], center=False) for m in data.FOOD_MENU]
    out["choices"] = choice_ids

    # outcomes: one row per kind * 4 + choice
    rows = {"first": [], "count": [], "fshift": [], "heat": []}
    thresholds = []
    outs = {k: [] for k in ("l1", "l2", "money_hi", "money_lo", "energy", "heat", "flags")}
    for kind in KINDS:
        for ci in range(4):
            if ci >= len(CHOICES[kind]):
                spec = {"follower_shift": 0, "heat_shift": False, "outcomes": [data.LEAVE]}
            else:
                spec = data.OUTCOMES[(kind, CHOICES[kind][ci])]
            items = spec["outcomes"]
            assert 1 <= len(items) <= 4 and items[-1]["odds"] is None, (kind, ci)
            rows["first"].append(len(outs["l1"]))
            rows["count"].append(len(items))
            rows["fshift"].append(round(spec["follower_shift"] * 256 / 100) & 0xFF)
            rows["heat"].append(1 if spec["heat_shift"] else 0)
            for t in range(4):
                total, cums = 0, []
                for item in items[:-1]:
                    total += item["odds"][t]
                    cums.append(min(255, round(total * 256 / 100)))
                assert total <= 100, (kind, ci, t)
                thresholds += (cums + [255, 255, 255])[:3]
            for item in items:
                l1, l2 = item["lines"]
                outs["l1"].append(strings.add(l1))
                outs["l2"].append(strings.add(l2))
                cents = energy = heat = flags = 0
                for eff in item["effects"]:
                    if eff[0] == "money":
                        cents += eff[1]
                    elif eff[0] == "energy":
                        energy += -eff[1]
                    elif eff[0] == "heat":
                        heat += eff[1]
                    elif eff[0] == "shelter":
                        flags |= FLAG_SHELTER
                    elif eff[0] == "outskirts":
                        flags |= FLAG_OUTSKIRTS
                    elif eff[0] == "combat":
                        flags |= FLAG_COMBAT
                    elif eff[0] == "leave":
                        flags |= FLAG_LEAVE
                    else:
                        raise ValueError(eff)
                hi, lo = bcd(cents)
                outs["money_hi"].append(hi)
                outs["money_lo"].append(lo)
                outs["energy"].append(energy)
                outs["heat"].append(heat)
                outs["flags"].append(flags)
    out["rows"], out["thresholds"], out["outcomes"] = rows, thresholds, outs

    # food
    food = {"price_hi": [], "price_lo": [], "energy": []}
    for m in data.FOOD_MENU:
        hi, lo = bcd(m["cents"])
        food["price_hi"].append(hi)
        food["price_lo"].append(lo)
        food["energy"].append(m["energy"])
    hi, lo = bcd(data.JAIL_FINE_CENTS)       # the jail fine shares the price table
    food["price_hi"].append(hi)
    food["price_lo"].append(lo)
    food["energy"].append(0)
    out["food"] = food
    eq = out["equates"]
    eq["STR_FOOD_GREET1"] = strings.add(data.FOOD_GREETING[0])
    eq["STR_FOOD_GREET2"] = strings.add(data.FOOD_GREETING[1])
    for name, (l1, l2) in data.FOOD_LINES.items():
        eq[f"STR_{name.upper()}1"] = strings.add(l1)
        eq[f"STR_{name.upper()}2"] = strings.add(l2)
    for name, (l1, l2) in data.MESSAGES.items():
        if l2 is None:
            eq[f"STR_{name.upper()}"] = strings.add(l1, center=False)
        else:
            eq[f"STR_{name.upper()}1"] = strings.add(l1)
            eq[f"STR_{name.upper()}2"] = strings.add(l2)
    for flag in ("SHELTER", "OUTSKIRTS", "COMBAT", "LEAVE"):
        eq[f"OUT_{flag}"] = globals()[f"FLAG_{flag}"]
    rob_hi, rob_lo = bcd(data.ROB_CASH_CENTS)
    eq["ROB_CASH_HI"], eq["ROB_CASH_LO"] = rob_hi, rob_lo
    eq["CALLS_COPS"] = round(data.PASSERBY_CALLS_COPS * 256 / 100)
    eq["FINE_INDEX"] = len(data.FOOD_MENU)
    assert len(strings.lines) < 256 and len(greet["line1"]) < 256
    return out

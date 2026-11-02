#!/usr/bin/env python3
"""Render Atari 2600-accurate concept mockups for Homeless Insurgency.

Each scene is built only from the objects the TIA can draw on a scanline:
background (BK), 40-block playfield (PF), two 8-pixel players (P0/P1), two
missiles (M0/M1) and the ball (BL). The Frame class asserts the hardware
limits (one color per object per scanline, one owner per object per scanline,
repositioning gaps between multiplexed sprites, 12-char text lines) so a
mockup can't promise something the console can't draw.

Usage: python3 tools/mockups/render_mockups.py [out_dir]
"""
import os
import sys

from PIL import Image

W, H = 160, 192
SCALE_X, SCALE_Y = 5, 3  # ~1.67:1 pixel aspect, close to a real TV

# NTSC palette (Stella), 16 hues x 8 luminances.
NTSC = [
    "000000 404040 6c6c6c 909090 b0b0b0 c8c8c8 dcdcdc ececec",
    "444400 646410 848424 a0a034 b8b840 d0d050 e8e85c fcfc68",
    "702800 844414 985c28 ac783c bc8c4c cca05c dcb468 ecc878",
    "841800 983418 ac5030 c06848 d0805c e09470 eca880 fcbc94",
    "880000 9c2020 b03c3c c05858 d07070 e08888 eca0a0 fcb4b4",
    "78005c 8c2074 a03c88 b0589c c070b0 d084c0 dc9cd0 ecb0e0",
    "480078 602090 783ca4 8c58b8 a070cc b484dc c49cec d4b0fc",
    "140084 302098 4c3cac 6858c0 7c70d0 9488e0 a8a0ec bcb4fc",
    "000088 1c209c 3840b0 505cc0 6874d0 7c8ce0 90a4ec a4b8fc",
    "00187c 1c3890 3854a8 5070bc 6888cc 7c9cdc 90b4ec a4c8fc",
    "002c5c 1c4c78 386890 5084ac 689cc0 7cb4d4 90cce8 a4e0fc",
    "003c2c 1c5c48 387c64 509c80 68b494 7cd0ac 90e4c0 a4fcd4",
    "003c00 205c20 407c40 5c9c5c 74b474 8cd08c a4e4a4 b8fcb8",
    "143800 345c1c 507c38 6c9850 84b468 9ccc7c b4e490 c8fca4",
    "2c3000 4c501c 687034 848c4c 9ca864 b4c078 ccd488 e0ec9c",
    "442800 644818 846830 a08444 b89c58 d0b46c e8cc7c fce08c",
]
PALETTE = [tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
           for row in NTSC for h in row.split()]


def c(hue, lum):
    """Palette entry for TIA color byte (hue << 4) | (lum << 1)."""
    return PALETTE[hue * 8 + lum]


BLACK = c(0, 0)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets"))
from font import FONT, PF_WIDE  # noqa: E402


TEXT_CHARS = 12          # 48-pixel kernel, 4-pixel glyph cells
TEXT_X = (W - 48) // 2   # the 48-pixel block sits centered
TEXT_COMPOSE_GAP = 6     # blank lines needed to build the next line's RAM buffer
REPOSITION_GAP = 2       # blank lines needed to move a multiplexed sprite


class Frame:
    def __init__(self, name):
        self.name = name
        self.bg = [BLACK] * H
        self.pf = [[False] * 40 for _ in range(H)]
        self.pfcol = [None] * H
        self.score = [False] * H
        self.pcol = {0: [None] * H, 1: [None] * H}
        self.ppix = {0: [set() for _ in range(H)], 1: [set() for _ in range(H)]}
        self.mpix = {0: [set() for _ in range(H)], 1: [set() for _ in range(H)]}
        self.blpix = [set() for _ in range(H)]
        self.owner = {k: [None] * H for k in ("P0", "P1", "M0", "M1", "BL")}
        self.text_lines = []

    # -- bookkeeping ---------------------------------------------------
    def _claim(self, obj, y, label):
        assert 0 <= y < H, f"{self.name}: {label} off screen at line {y}"
        cur = self.owner[obj][y]
        assert cur in (None, label), \
            f"{self.name}: line {y}: {obj} already used by {cur}, can't also draw {label}"
        self.owner[obj][y] = label

    def _set_pcol(self, n, y, color, label):
        cur = self.pcol[n][y]
        assert cur in (None, color), \
            f"{self.name}: line {y}: COLUP{n} can't be two colors ({label})"
        self.pcol[n][y] = color

    # -- background / playfield ----------------------------------------
    def background(self, y0, y1, color):
        for y in range(y0, y1):
            self.bg[y] = color

    def playfield(self, y0, y1, bits, color, score=False):
        """bits: 40-char string of '#'/'.' (asymmetric playfield)."""
        assert len(bits) == 40, f"{self.name}: playfield row must be 40 blocks"
        for y in range(y0, y1):
            self.pf[y] = [ch == "#" for ch in bits]
            self.pfcol[y] = color
            self.score[y] = score

    # -- players ---------------------------------------------------------
    def sprite(self, n, x, y, art, colors, wide=1, rows=2, reflect=False,
               copies=(0,), label=None):
        """Draw player n. art rows are <=8 chars; each row may use one color key."""
        label = label or f"P{n}"
        for r, row in enumerate(art):
            assert len(row) <= 8, f"{self.name}: {label} row {r} wider than 8 bits"
            row = row.ljust(8, ".")
            if reflect:
                row = row[::-1]
            keys = {ch for ch in row if ch != "."}
            assert len(keys) <= 1, \
                f"{self.name}: {label} row {r} uses {sorted(keys)} — one color per scanline"
            color = colors[keys.pop()] if keys else None
            for dy in range(rows):
                ly = y + r * rows + dy
                self._claim(f"P{n}", ly, label)
                if color:
                    self._set_pcol(n, ly, color, label)
                for off in copies:
                    for i, ch in enumerate(row):
                        if ch != ".":
                            for sx in range(wide):
                                self.ppix[n][ly].add((x + off + i * wide + sx) % W)

    def player_color_only(self, n, y0, y1, color, label):
        """Set COLUPn on lines where the player itself draws nothing (score mode, missiles)."""
        for y in range(y0, y1):
            self._claim(f"P{n}", y, label)
            self._set_pcol(n, y, color, label)

    def missile(self, n, x, y, w, h, label):
        """Missiles are 1/2/4/8 px wide and always use the matching player's color."""
        assert w in (1, 2, 4, 8)
        for ly in range(y, y + h):
            self._claim(f"M{n}", ly, label)
            assert self.pcol[n][ly] is not None, \
                f"{self.name}: line {ly}: M{n} ({label}) has no COLUP{n} set"
            self.mpix[n][ly].update(range(x, x + w))

    def ball(self, x, y, w, h, label):
        """The ball is 1/2/4/8 px wide and always uses the playfield color."""
        assert w in (1, 2, 4, 8)
        for ly in range(y, y + h):
            self._claim("BL", ly, label)
            assert self.pfcol[ly] is not None, \
                f"{self.name}: line {ly}: BL ({label}) has no COLUPF set"
            self.blpix[ly].update(range(x, x + w))

    # -- text kernel -----------------------------------------------------
    def text(self, y, s, color, rows=2, left=False):
        """One 12-character line from the 48-pixel kernel (uses P0 and P1)."""
        assert len(s) <= TEXT_CHARS, f"{self.name}: '{s}' is {len(s)} chars (max 12)"
        s = s.ljust(TEXT_CHARS) if left else s.center(TEXT_CHARS)
        colors = color if isinstance(color, list) else [color] * 5
        for gr in range(5):
            for dy in range(rows):
                ly = y + gr * rows + dy
                for n in (0, 1):
                    self._claim(f"P{n}", ly, "text")
                    self._set_pcol(n, ly, colors[gr], "text")
                for ci, ch in enumerate(s):
                    glyph = FONT[ch][gr]
                    for gx, bit in enumerate(glyph):
                        if bit == "#":
                            # even characters come from P0 copies, odd from P1
                            self.ppix[(ci // 2) % 2][ly].add(TEXT_X + ci * 4 + gx)
        self.text_lines.append((y, y + 5 * rows))

    # -- validation + output ---------------------------------------------
    def validate(self):
        for obj in ("P0", "P1"):
            owners = self.owner[obj]
            # every band change needs REPOSITION_GAP empty lines
            last_label, last_end = None, None
            for y in range(H):
                cur = owners[y]
                if cur and cur != last_label:
                    if last_label is not None:
                        gap = y - last_end - 1
                        need = TEXT_COMPOSE_GAP if cur == "text" and last_label == "text" \
                            else REPOSITION_GAP
                        assert gap >= need, \
                            f"{self.name}: {obj} {last_label}->{cur} at line {y} " \
                            f"has {gap} free lines, needs {need}"
                    last_label = cur
                if cur:
                    last_end = y
        # consecutive text lines need time to compose the next buffer
        tl = sorted(self.text_lines)
        for (a0, a1), (b0, b1) in zip(tl, tl[1:]):
            assert b0 - a1 >= TEXT_COMPOSE_GAP, \
                f"{self.name}: text lines at {a0} and {b0} too close to compose buffer"

    def render(self):
        self.validate()
        img = Image.new("RGB", (W, H))
        px = img.load()
        for y in range(H):
            for x in range(W):
                col = self.bg[y]
                if self.pf[y][x // 4] or x in self.blpix[y]:
                    if self.score[y] and self.pf[y][x // 4]:
                        col = self.pcol[0][y] if x < 80 else self.pcol[1][y]
                    else:
                        col = self.pfcol[y]
                if x in self.ppix[1][y] or x in self.mpix[1][y]:
                    col = self.pcol[1][y]
                if x in self.ppix[0][y] or x in self.mpix[0][y]:
                    col = self.pcol[0][y]
                px[x, y] = col
        return img.resize((W * SCALE_X, H * SCALE_Y), Image.NEAREST)




def pf_text(word, wide=""):
    """Spell a word in 5-row glyphs as playfield rows, centered in 40 blocks."""
    rows = []
    for gr in range(5):
        rows.append(".".join((PF_WIDE[ch] if ch in wide else FONT[ch])[gr]
                             for ch in word))
    width = len(rows[0])
    assert width <= 40, f"'{word}' needs {width} playfield blocks"
    left = (40 - width) // 2
    return ["." * left + r + "." * (40 - width - left) for r in rows]


# ---------------------------------------------------------------------------
# Sprite art lives in assets/sprites.py (shared with the ROM build).
# ---------------------------------------------------------------------------
import sprites as _art  # noqa: E402

PLAYER_TOP = _art.PLAYER_TOP
HOMELESS_TOP = _art.HOMELESS_TOP
POLICE_TOP = _art.POLICE_TOP
PERSON_TOP = _art.PERSON_TOP
FOLLOWER_TOP = _art.FOLLOWER_TOP
SIGN_SHELTER = _art.SIGN_SHELTER
SIGN_FOOD = _art.SIGN_FOOD
PLAYER_SIDE = _art.PLAYER_SIDE
HOMELESS_SIDE = _art.HOMELESS_SIDE
COP_SIDE = _art.COP_SIDE
PASSERBY_SIDE = _art.PASSERBY_SIDE
BARREL = _art.BARREL
BYSTANDER = _art.BYSTANDER
PLAYER_COLORS = {k: c(*v) for k, v in _art.PLAYER_COLORS.items()}
HOMELESS_COLORS = {k: c(*v) for k, v in _art.HOMELESS_COLORS.items()}
POLICE_COLORS = {k: c(*v) for k, v in _art.POLICE_COLORS.items()}
FOLLOWER_COLORS = {k: c(*v) for k, v in _art.FOLLOWER_COLORS.items()}
PASSERBY_COLORS = {k: c(*v) for k, v in _art.PASSERBY_COLORS.items()}
PERSON_COLORS = {k: c(*v) for k, v in _art.PERSON_COLORS.items()}

# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------

def scene_title():
    f = Frame("title")
    for i, row in enumerate(pf_text("HOMELESS", wide="M")):
        for dy in range(6):
            y = 10 + i * 6 + dy
            f.playfield(y, y + 1, row, c(1, 7 - (i * 6 + dy) // 6))
    for i, row in enumerate(pf_text("INSURGENCY")):
        for dy in range(6):
            y = 46 + i * 6 + dy
            f.playfield(y, y + 1, row, c(3, 6 - (i * 6 + dy) // 6))
    f.text(86, "ACT I: RALLY", c(0, 6))
    # night sky gradient behind skyline
    for y in range(100, 170):
        f.background(y, y + 1, c(6, min(2, (y - 100) // 24)))
    skyline = [
        (112, "..........................#####........."),
        (118, "...####.................##########......"),
        (124, "...####.......#####.....##########...###"),
        (132, "######...#######.#####..##########..####"),
        (140, "######..##################################"[:40]),
        (148, "########################################"),
    ]
    for (y0, bits), nxt in zip(skyline, [s[0] for s in skyline[1:]] + [166]):
        f.playfield(y0, nxt, bits, c(0, 0))
    f.playfield(166, 170, "#" * 40, c(0, 2))
    flame = {"F": c(2, 6), "O": c(3, 5), "Y": c(1, 6), "D": c(0, 2), "G": c(0, 3)}
    # flame rows recolored per scanline in the real kernel; here rows 0-2 use F
    f.sprite(0, 72, 142, BARREL, flame, wide=2, rows=2, label="barrel")
    f.sprite(1, 44, 142, BYSTANDER, {"X": c(0, 1)}, rows=2, copies=(0, 64),
             label="crowd")
    f.text(178, "PRESS FIRE", c(1, 6))
    return f


def scene_city():
    f = Frame("city")
    asphalt, sidewalk = c(0, 1), c(0, 3)
    f.background(0, 156, asphalt)
    # 36-line streets: room for the player plus the follower row behind
    for y0, y1 in ((24, 60), (96, 132)):
        f.background(y0, y0 + 4, sidewalk)
        f.background(y1 - 4, y1, sidewalk)
        f.playfield(y0 + 17, y0 + 19, "..##" * 10, c(1, 5))  # lane dashes

    def band(block_cols_open, holes=()):
        bits = ["#"] * 40
        for a, b in block_cols_open:
            for i in range(a, b + 1):
                bits[i] = "."
        for i in holes:
            bits[i] = "."
        return "".join(bits)
    # vertical streets at blocks 9-12 and 26-29
    open_cols = [(9, 12), (26, 29)]
    bands = [
        (0, 24, (3, 3), (3, 2), (3, 1)),       # brick rooftops
        (60, 96, (15, 4), (15, 3), (15, 2)),   # concrete — the shelter block
        (132, 156, (10, 3), (10, 2), (10, 1)),  # teal roofs
    ]
    for y0, y1, edge, body, shadow in bands:
        f.playfield(y0, y0 + 2, band(open_cols), c(*edge))
        for y in range(y0 + 2, y1 - 3):
            vents = (3, 4, 18, 19, 34, 35) if (y - y0) % 10 in (5, 6) else ()
            f.playfield(y, y + 1, band(open_cols, vents), c(*body))
        f.playfield(y1 - 3, y1, band(open_cols), c(*shadow))
    # P0: player, then the follower row (10 recruits = 2 followers, NUSIZ 2 copies close)
    f.sprite(0, 64, 26, PLAYER_TOP, PLAYER_COLORS, label="player")
    f.sprite(0, 56, 48, FOLLOWER_TOP, FOLLOWER_COLORS, copies=(0, 16), label="followers")
    # P1: multiplexed NPC / sign bands
    f.sprite(1, 130, 6, SIGN_FOOD, {"F": c(0, 6), "M": c(2, 5)}, label="food sign")
    f.sprite(1, 108, 30, HOMELESS_TOP, HOMELESS_COLORS, label="homeless A")
    f.sprite(1, 108, 60, POLICE_TOP, POLICE_COLORS, label="police")
    f.sprite(1, 64, 82, SIGN_SHELTER, {"W": c(10, 7)}, label="shelter sign")
    f.sprite(1, 20, 104, PERSON_TOP, PERSON_COLORS, label="passerby")
    f.sprite(1, 40, 134, HOMELESS_TOP, HOMELESS_COLORS, label="homeless B")
    # HUD
    f.text(164, "$0.75  10/??", c(1, 6))
    f.playfield(180, 186, ".." + "#" * 26 + "." * 12, c(12, 4))  # energy
    return f


def encounter_base(name, header, header_color):
    f = Frame(name)
    f.text(1, header, header_color)
    return f


def dialogue_panel(f, speech, choices, selected):
    f.background(86, H, c(0, 0))
    f.text(91, speech[0], c(0, 7))
    f.text(108, speech[1], c(0, 7))
    f.playfield(121, 122, "...." + "#" * 32 + "....", c(0, 2))
    ys = (125, 142, 159, 176)
    for i, (y, choice) in enumerate(zip(ys, choices)):
        f.text(y, choice, c(1, 6) if i == selected else c(0, 3), left=True)
    f.missile(0, TEXT_X - 6, ys[selected] + 3, 4, 4, "cursor")


def scene_encounter_homeless():
    f = encounter_base("encounter_homeless", "HOMELESS", c(0, 4))
    # brick wall: background mortar/brick per line, playfield draws the joints
    for y in range(12, 72):
        course = (y - 12) // 6
        if (y - 12) % 6 == 5:
            f.background(y, y + 1, c(3, 3))
        else:
            f.background(y, y + 1, c(3, 1))
            joints = "#......." * 5 if course % 2 == 0 else "....#..." * 5
            f.playfield(y, y + 1, joints, c(3, 3))
    f.background(72, 84, c(0, 3))
    f.playfield(72, 73, "#" * 40, c(0, 4))
    f.sprite(0, 44, 16, PLAYER_SIDE, PLAYER_COLORS, wide=2, label="player")
    f.sprite(1, 100, 16, HOMELESS_SIDE, HOMELESS_COLORS, wide=2, reflect=True,
             label="homeless")
    dialogue_panel(f, ("WHO SENT YA?", "TALK FAST?"),
                   ("I'M ONE OF U", "SHARE FOOD", "BIG PLAN...", "WALK AWAY"), 2)
    return f


def scene_encounter_police():
    f = encounter_base("encounter_police", "POLICE", c(9, 5))
    for y in range(12, 72):
        f.background(y, y + 1, c(8, 0) if y < 40 else c(0, 1))
    # parked cruiser, right side, drawn with playfield; color changes per line
    car = [
        (44, 46, "................................####....", c(4, 3)),
        (46, 48, "................................####....", c(8, 4)),
        (48, 54, "...............................######...", c(0, 6)),
        (54, 60, "..............................########..", c(9, 1)),
        (60, 64, ".............................##########.", c(0, 6)),
        (64, 66, ".............................##########.", c(8, 3)),
        (66, 70, ".............................##########.", c(0, 6)),
        (70, 72, "..............................##....##..", c(0, 0)),
    ]
    for y0, y1, bits, col in car:
        f.playfield(y0, y1, bits, col)
    f.background(72, 84, c(0, 3))
    f.playfield(72, 73, "#" * 40, c(0, 4))
    f.sprite(0, 44, 16, PLAYER_SIDE, PLAYER_COLORS, wide=2, label="player")
    f.sprite(1, 88, 16, COP_SIDE, POLICE_COLORS, wide=2, reflect=True, label="cop")
    f.missile(1, 86, 52, 2, 14, "baton")
    dialogue_panel(f, ("KEEP MOVING,", "PAL."),
                   ("ASK CHANGE", "ASK SHELTER", "YELL AT COP", "ATTACK"), 1)
    return f


def scene_encounter_passerby():
    f = encounter_base("encounter_passerby", "PASSERBY", c(12, 5))
    # daytime storefront: sky, awning stripes, shop window drawn in playfield
    f.background(12, 30, c(9, 5))
    for y in range(30, 36):
        f.background(y, y + 1, c(4, 3) if (y // 2) % 2 == 0 else c(0, 7))
    f.background(36, 72, c(15, 3))
    f.playfield(40, 66, "#" * 12 + "." * 16 + "#" * 12, c(10, 6))
    f.background(72, 84, c(0, 3))
    f.playfield(72, 73, "#" * 40, c(0, 4))
    f.sprite(0, 44, 16, PLAYER_SIDE, PLAYER_COLORS, wide=2, label="player")
    f.sprite(1, 96, 16, PASSERBY_SIDE, PASSERBY_COLORS, wide=2, reflect=True,
             label="passerby")
    f.missile(1, 92, 50, 4, 8, "briefcase")
    dialogue_panel(f, ("UGH. WHAT? I", "HAVE A TRAIN"),
                   ("ASK CHANGE", "ROB", "WALK AWAY"), 1)
    return f


def scene_combat():
    f = Frame("combat")
    f.text(1, "YOU  VS  COP", c(0, 6))
    # energy bars: playfield score mode takes COLUP0 on the left, COLUP1 on the right
    f.player_color_only(0, 15, 20, c(12, 5), "bar")
    f.player_color_only(1, 15, 20, c(4, 4), "bar")
    you, cop = 13, 18
    bits = ".." + "#" * you + "." * (18 - you) + "." * (18 - cop) + "#" * cop + ".."
    f.playfield(15, 20, bits, c(0, 0), score=True)
    for y in range(22, 168):
        f.background(y, y + 1, c(7, min(3, (y - 22) // 26)) if y < 100 else c(0, 2))
    f.background(100, 104, c(0, 3))  # far sidewalk where the crew stands
    f.player_color_only(1, 34, 42, c(1, 7), "moon")
    f.missile(1, 124, 34, 8, 8, "moon")
    skyline = [
        (70, "...........................##..........."),
        (76, "..........###..............##.........##"),
        (84, "#####.....###.....######..######......##"),
        (92, "#####..########...######..######..######"),
    ]
    for (y0, bits), nxt in zip(skyline, [s[0] for s in skyline[1:]] + [100]):
        f.playfield(y0, nxt, bits, c(7, 0))
    for y in range(100, 168):
        f.pfcol[y] = c(0, 4)  # COLUPF = pipe grey (the ball takes PF color)
    # fed crew: a second P0 band above the fighters, 2 followers via copies
    f.sprite(0, 20, 93, FOLLOWER_TOP, FOLLOWER_COLORS, copies=(0, 16), label="crew")
    f.sprite(0, 50, 108, PLAYER_SIDE, PLAYER_COLORS, wide=2, label="player")
    f.ball(66, 135, 8, 2, "pipe")
    f.sprite(1, 80, 108, COP_SIDE, POLICE_COLORS, wide=2, reflect=True, label="cop")
    f.background(168, H, c(0, 0))
    f.playfield(168, 174, "#" * 40, c(0, 2))
    f.text(181, "PIPE  CREW 2", c(0, 5))
    return f


SCENES = {
    "01_title": scene_title,
    "02_city": scene_city,
    "03_encounter_homeless": scene_encounter_homeless,
    "04_encounter_police": scene_encounter_police,
    "05_encounter_passerby": scene_encounter_passerby,
    "06_combat": scene_combat,
}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "..", "docs", "mockups")
    os.makedirs(out, exist_ok=True)
    for name, build in SCENES.items():
        path = os.path.join(out, f"{name}.png")
        build().render().save(path)
        print(path)


if __name__ == "__main__":
    main()

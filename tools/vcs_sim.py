"""Minimal Atari 2600 simulator for tests: py65 CPU + F4SC cartridge + TIA/RIOT.

Good enough to count scanlines exactly, drive the joystick, read RAM, check
collisions and render frames to PNG. Not cycle-perfect for every TIA quirk:
Stella remains the reference for how a frame really looks.
"""
import os
import sys

from py65.devices.mpu6502 import MPU

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mockups"))
from render_mockups import PALETTE  # noqa: E402

CYCLES_PER_LINE = 76
CLOCKS_PER_LINE = 228
HBLANK = 68

# NUSIZ number/size -> (copy offsets, pixel scale)
NUSIZ = {0: ((0,), 1), 1: ((0, 16), 1), 2: ((0, 32), 1), 3: ((0, 16, 32), 1),
         4: ((0, 64), 1), 5: ((0,), 2), 6: ((0, 32, 64), 1), 7: ((0,), 4)}

# Object position offset after RESxx, calibrated so the standard PosObject
# routine (divide-by-15 + HMOVE) puts an object at exactly the requested x.
RES_OFFSET = {"P": 5, "M": 4, "BL": 4}

# Collision register bit assignments: (register, bit, object a, object b)
COLLISIONS = [
    (0, 7, "M0", "P1"), (0, 6, "M0", "P0"), (1, 7, "M1", "P0"), (1, 6, "M1", "P1"),
    (2, 7, "P0", "PF"), (2, 6, "P0", "BL"), (3, 7, "P1", "PF"), (3, 6, "P1", "BL"),
    (4, 7, "M0", "PF"), (4, 6, "M0", "BL"), (5, 7, "M1", "PF"), (5, 6, "M1", "BL"),
    (6, 7, "BL", "PF"), (7, 7, "P0", "P1"), (7, 6, "M0", "M1"),
]


def signed_nibble(v):
    n = (v >> 4) & 0xF
    return n - 16 if n >= 8 else n


class TIA:
    def __init__(self):
        self.reg = [0] * 64
        self.pos = {"P0": 0, "P1": 0, "M0": 0, "M1": 0, "BL": 0}
        self.grp_new = [0, 0]
        self.grp_old = [0, 0]
        self.enabl_new = 0
        self.enabl_old = 0
        self.collide = [0] * 8
        self.hmove_line = -1

    def pf_bit(self, x):
        col = x // 4
        if col >= 20:
            col = 39 - col if self.reg[0x0A] & 1 else col - 20
        pf0, pf1, pf2 = self.reg[0x0D], self.reg[0x0E], self.reg[0x0F]
        if col < 4:
            return (pf0 >> (4 + col)) & 1
        if col < 12:
            return (pf1 >> (11 - col)) & 1
        return (pf2 >> (col - 12)) & 1

    def player_bit(self, n, x):
        grp = self.grp_old[n] if self.reg[0x25 + n] & 1 else self.grp_new[n]
        if not grp:
            return 0
        copies, scale = NUSIZ[self.reg[0x04 + n] & 7]
        pos = self.pos[f"P{n}"]
        for off in copies:
            d = (x - pos - off) % 160
            if d < 8 * scale:
                bit = d // scale
                if self.reg[0x0B + n] & 8:
                    bit = 7 - bit
                return (grp >> (7 - bit)) & 1
        return 0

    def missile_bit(self, n, x):
        if not self.reg[0x1D + n] & 2:
            return 0
        nus = self.reg[0x04 + n]
        width = 1 << ((nus >> 4) & 3)
        copies = NUSIZ[nus & 7][0] if (nus & 7) not in (5, 7) else (0,)
        pos = self.pos[f"M{n}"]
        return int(any((x - pos - off) % 160 < width for off in copies))

    def ball_bit(self, x):
        en = self.enabl_old if self.reg[0x27] & 1 else self.enabl_new
        if not en & 2:
            return 0
        width = 1 << ((self.reg[0x0A] >> 4) & 3)
        return int((x - self.pos["BL"]) % 160 < width)

    def pixel(self, x, visible):
        on = {
            "PF": self.pf_bit(x), "BL": self.ball_bit(x),
            "P0": self.player_bit(0, x), "M0": self.missile_bit(0, x),
            "P1": self.player_bit(1, x), "M1": self.missile_bit(1, x),
        }
        if visible:
            for reg, bit, a, b in COLLISIONS:
                if on[a] and on[b]:
                    self.collide[reg] |= 1 << bit
        ctrl = self.reg[0x0A]
        if on["PF"] and ctrl & 2 and not ctrl & 4:
            pf_col = self.reg[0x06] if x < 80 else self.reg[0x07]
        else:
            pf_col = self.reg[0x08]
        layers = [
            (on["P0"] or on["M0"], self.reg[0x06]),
            (on["P1"] or on["M1"], self.reg[0x07]),
        ]
        playfield = (on["PF"] or on["BL"], pf_col if on["PF"] else self.reg[0x08])
        layers = [playfield] + layers if ctrl & 4 else layers + [playfield]
        for active, color in layers:
            if active:
                return color
        return self.reg[0x09]

    def write(self, addr, v, clock):
        """Apply a register write; `clock` = color clock within the line."""
        self.reg[addr] = v
        if addr == 0x1B:
            self.grp_new[0] = v
            self.grp_old[1] = self.grp_new[1]
        elif addr == 0x1C:
            self.grp_new[1] = v
            self.grp_old[0] = self.grp_new[0]
            self.enabl_old = self.enabl_new
        elif addr == 0x1F:
            self.enabl_new = v
        elif 0x10 <= addr <= 0x14:
            name = ["P0", "P1", "M0", "M1", "BL"][addr - 0x10]
            kind = name[0] if name != "BL" else "BL"
            x = clock - HBLANK
            self.pos[name] = (max(x, -2) + RES_OFFSET[kind]) % 160
        elif addr == 0x2A:
            for i, name in enumerate(["P0", "P1", "M0", "M1", "BL"]):
                self.pos[name] = (self.pos[name] - signed_nibble(self.reg[0x20 + i])) % 160
        elif addr == 0x2B:
            for i in range(0x20, 0x25):
                self.reg[i] = 0
        elif addr == 0x2C:
            self.collide = [0] * 8


class Atari:
    """Memory map + timing. Use run_frame() to advance one frame."""

    def __init__(self, rom_bytes, start_bank=7):
        assert len(rom_bytes) == 32768, "expected a 32K F4SC image"
        self.rom = rom_bytes
        self.bank = start_bank
        self.ram = bytearray(128)
        self.sc = bytearray(128)
        self.tia = TIA()
        self.swcha = 0xFF
        self.fire = False
        self.timer = (0, 1, 0)          # (value, interval, cycle written)
        self.mpu = MPU(memory=self)
        self.mpu.pc = self.rom[self.bank * 4096 + 0xFFC] | (self.rom[self.bank * 4096 + 0xFFD] << 8)
        self.now = 0                    # cycle at which the current instruction ends
        self.wsync = False
        self.render_pos = 0             # color clock up to which pixels are drawn
        self.lines = {}                 # absolute line -> bytearray(160) of color bytes
        self.vblank_lines = set()
        self.vsync_on = False
        self.frame_starts = []

    # --- memory interface used by py65 ----------------------------------
    def __len__(self):
        return 0x10000

    def __getitem__(self, addr):
        a = addr & 0x1FFF
        if a & 0x1000:
            off = a & 0xFFF
            if 0xFF4 <= off <= 0xFFB:
                self.bank = off - 0xFF4
            if 0x80 <= off < 0x100:
                return self.sc[off - 0x80]
            return self.rom[self.bank * 4096 + off]
        if a & 0x80 and not a & 0x200:
            return self.ram[a & 0x7F]
        if a & 0x280 == 0x280:
            return self._riot_read(a & 0x2FF)
        r = a & 0x0F
        if r <= 7:
            self._render_to(self.now * 3)
            return self.tia.collide[r]
        if r == 0x0C:
            return 0x00 if self.fire else 0x80
        return 0x80

    def __setitem__(self, addr, v):
        a = addr & 0x1FFF
        if a & 0x1000:
            off = a & 0xFFF
            if 0xFF4 <= off <= 0xFFB:
                self.bank = off - 0xFF4
            elif off < 0x80:
                self.sc[off] = v
            return
        if a & 0x80 and not a & 0x200:
            self.ram[a & 0x7F] = v
            return
        if a & 0x280 == 0x280:
            r = a & 0x297
            if r in (0x294, 0x295, 0x296, 0x297):
                self.timer = (v, {0x294: 1, 0x295: 8, 0x296: 64, 0x297: 1024}[r], self.now)
            return
        self._tia_write(a & 0x3F, v)

    def peek(self, addr):
        a = addr & 0x1FFF
        if a & 0x1000:
            return self.rom[self.bank * 4096 + (a & 0xFFF)]
        if a & 0x80 and not a & 0x200:
            return self.ram[a & 0x7F]
        return 0

    # --- RIOT -------------------------------------------------------------
    def _riot_read(self, a):
        if a == 0x280:
            return self.swcha
        if a == 0x282:
            return 0x0B
        if a in (0x284, 0x286):
            v, n, t = self.timer
            elapsed = self.now - t
            d = elapsed // n
            if d <= v:
                return v - d
            return (0xFF - (elapsed - (v + 1) * n)) & 0xFF
        if a in (0x285, 0x287):
            v, n, t = self.timer
            return 0x80 if self.now - t >= (v + 1) * n else 0
        return 0

    # --- TIA timing ---------------------------------------------------------
    def _tia_write(self, r, v):
        clock = self.now * 3
        if r == 0x02:                   # WSYNC
            self.wsync = True
            return
        self._render_to(clock)
        line, in_line = divmod(clock, CLOCKS_PER_LINE)
        if r == 0x00:                   # VSYNC
            on = bool(v & 2)
            if on and not self.vsync_on:
                self.frame_starts.append(line)
            self.vsync_on = on
        if r == 0x2A and in_line < HBLANK:
            self.tia.hmove_line = line
        self.tia.write(r, v, in_line)

    def _render_to(self, clock):
        tia = self.tia
        pos = self.render_pos
        while pos < clock:
            line, cc = divmod(pos, CLOCKS_PER_LINE)
            if cc < HBLANK:
                pos += HBLANK - cc
                continue
            x = cc - HBLANK
            buf = self.lines.get(line)
            if buf is None:
                buf = self.lines[line] = bytearray(160)
            blanked = tia.reg[0x01] & 2
            if blanked:
                self.vblank_lines.add(line)
                buf[x] = 0
            elif line == tia.hmove_line and x < 8:
                buf[x] = 0
                tia.pixel(x, True)
            else:
                buf[x] = tia.pixel(x, True)
            pos += 1
        self.render_pos = max(self.render_pos, clock)

    def step(self):
        mpu = self.mpu
        op = self.peek(mpu.pc)
        self.now = mpu.processorCycles + mpu.cycletime[op]
        mpu.step()
        if self.wsync:
            self.wsync = False
            mpu.processorCycles = ((self.now - 1) // CYCLES_PER_LINE + 1) * CYCLES_PER_LINE

    def run_frame(self, max_cycles=200000):
        """Run until the next VSYNC starts. Returns the finished Frame (or None first time)."""
        starts = len(self.frame_starts)
        limit = self.mpu.processorCycles + max_cycles
        while len(self.frame_starts) == starts:
            self.step()
            if self.mpu.processorCycles > limit:
                raise RuntimeError("no VSYNC: the program is stuck or not making frames")
        self._render_to(self.mpu.processorCycles * 3)
        if len(self.frame_starts) < 2:
            return None
        first, last = self.frame_starts[-2], self.frame_starts[-1]
        frame = Frame(self, first, last)
        for ln in [k for k in self.lines if k < first]:
            del self.lines[ln]
        self.vblank_lines = {ln for ln in self.vblank_lines if ln >= first}
        return frame

    # --- helpers for tests ------------------------------------------------
    def joystick(self, right=False, left=False, down=False, up=False, fire=False):
        v = 0xFF
        for bit, on in ((7, right), (6, left), (5, down), (4, up)):
            if on:
                v &= ~(1 << bit)
        self.swcha = v & 0xFF
        self.fire = fire

    def read_ram(self, addr):
        return self.ram[addr & 0x7F]


class Frame:
    def __init__(self, atari, first, last):
        self.total_lines = last - first
        self.rows = []
        for ln in range(first, last):
            if ln not in atari.vblank_lines and ln in atari.lines:
                self.rows.append(bytes(atari.lines[ln]))
        self.visible_lines = len(self.rows)

    def to_png(self, path, scale_x=5, scale_y=3):
        from PIL import Image
        h = max(1, len(self.rows))
        img = Image.new("RGB", (160, h))
        px = img.load()
        for y, row in enumerate(self.rows):
            for x, cbyte in enumerate(row):
                px[x, y] = PALETTE[(cbyte >> 4) * 8 + ((cbyte >> 1) & 7)]
        img.resize((160 * scale_x, h * scale_y), Image.NEAREST).save(path)


def load_symbols(sym_path):
    syms = {}
    with open(sym_path) as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2 and not line.startswith("---"):
                try:
                    syms[parts[0]] = int(parts[1], 16)
                except ValueError:
                    pass
    return syms

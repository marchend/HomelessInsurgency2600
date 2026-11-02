"""Stage C: outcomes, money, food, fights, jail, weapons."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))

import build_dialogue  # noqa: E402
from test_npcs import NpcTest  # noqa: E402
from test_rom import RomCase, setUpModule  # noqa: E402,F401

D = build_dialogue.build()


def lfsr(v):
    out = v >> 1
    return out ^ 0xB8 if v & 1 else out


def expected_outcome(row, temp, roll, followers, heat):
    """The outcome index the ROM should pick, computed from the tables."""
    rows = D["rows"]
    shift = (followers * rows["fshift"][row]) & 0xFF
    if rows["heat"][row]:
        shift = ((heat >> 2) + shift) & 0xFF
    total = roll + shift
    if shift & 0x80:                    # negative shift: clamp at 0
        total = total - 256 if total >= 256 else 0
    else:
        total = min(total, 255)
    thr = D["thresholds"][(row * 4 + temp) * 3:(row * 4 + temp) * 3 + 3]
    for i in range(rows["count"][row] - 1):
        if total < thr[i]:
            return i
    return rows["count"][row] - 1


def bcd_to_cents(dollars, cents):
    def b(v):
        return (v >> 4) * 10 + (v & 15)
    return b(dollars) * 100 + b(cents)


def cents_to_bcd(c):
    d, cc = divmod(c, 100)
    return ((d // 10) << 4) | d % 10, ((cc // 10) << 4) | cc % 10


class OutcomeRollTest(RomCase):
    """Run the Outcome routine for every random value and compare to the tables."""

    def roll_all(self, kind, choice, temp, followers=0, heat=0):
        a = self.atari
        row = kind * 4 + choice
        first = D["rows"]["first"][row]
        mismatches = []
        for rng in range(1, 256):
            for name, v in (("encKind", kind), ("encTemp", temp), ("cursor", choice),
                            ("followers", followers), ("heat", heat), ("pending", 0),
                            ("rng", rng), ("energy", 200), ("money", 0), ("money+1", 0)):
                if name == "money+1":
                    a.write_ram(self.sym["money"] + 1, v)
                else:
                    a.write_ram(self.sym[name], v)
            a.write_ram(self.sym["encStr"], 0xEE)
            a.call(self.sym["Outcome"], 5)
            want = expected_outcome(row, temp, lfsr(rng), followers, heat)
            o = first + want
            flags = D["outcomes"]["flags"][o]
            if flags & build_dialogue.FLAG_LEAVE:
                got_ok = self.ram("pending") == self.sym["PENDING_RESUME"]
            elif flags & build_dialogue.FLAG_COMBAT:
                got_ok = self.ram("pending") == self.sym["PENDING_FIGHT"]
            else:
                got_ok = (self.ram("encStr") == D["outcomes"]["l1"][o]
                          and self.ram("encStr") != 0xEE)
            cents = bcd_to_cents(D["outcomes"]["money_hi"][o], D["outcomes"]["money_lo"][o])
            got_cents = bcd_to_cents(self.ram("money"), a.read_ram(self.sym["money"] + 1))
            if not got_ok or got_cents != cents:
                mismatches.append((rng, want))
        self.assertEqual(mismatches, [])

    def test_every_choice_and_temperament_matches_the_tables(self):
        kinds = {"homeless": 0, "police": 1, "passerby": 2}
        for kind, k in kinds.items():
            for c in range(len(build_dialogue.CHOICES[kind])):
                for t in range(4):
                    with self.subTest(kind=kind, choice=c, temp=t):
                        self.roll_all(k, c, t)

    def test_followers_and_heat_shift_the_odds(self):
        for followers, heat in ((3, 0), (5, 200), (0, 255)):
            for c in range(4):
                with self.subTest(followers=followers, heat=heat, choice=c):
                    self.roll_all(1, c, 1, followers, heat)          # police
            with self.subTest(followers=followers, rob=True):
                self.roll_all(2, 1, 1, followers, heat)              # rob: negative shift

    def test_one_in_twenty_passersby_give_change(self):
        row = 2 * 4 + 0                                              # passerby, ASK CHANGE
        gives = sum(expected_outcome(row, 1, r, 0, 0) == 0 for r in range(1, 256))
        self.assertAlmostEqual(gives / 255, 0.05, delta=0.01)


class EncounterFlowTest(NpcTest):
    """Whole-game flows through the encounter and fight screens."""

    def choose(self, index):
        for _ in range(index):
            self.frames(1, down=True)
            self.frames(1)
        self.frames(1, fire=True)
        self.frames(2)

    def money(self):
        return bcd_to_cents(self.ram("money"), self.atari.read_ram(self.sym["money"] + 1))

    def set_money(self, cents):
        hi, lo = cents_to_bcd(cents)
        self.atari.write_ram(self.sym["money"], hi)
        self.atari.write_ram(self.sym["money"] + 1, lo)

    def walk_to_food(self):
        self.start_city()                    # the start room has a food place
        self.assertEqual(self.sc("SC_SLOT_KIND", 2), self.sym["KIND_FOOD"])
        self.frames(8, down=True)            # to the bottom of the top street
        self.walk_to_slot(2)
        self.frames(1, fire=True)
        self.frames(1)
        self.assertEqual(self.ram("encKind"), self.sym["ENC_FOOD"])

    # --- food -------------------------------------------------------------------
    def test_no_money_no_food(self):
        self.walk_to_food()
        energy = self.ram("energy")
        self.choose(0)                       # coffee
        self.assertEqual(self.ram("encStr"), D["equates"]["STR_BROKE1"])
        self.assertEqual(self.ram("energy"), energy)

    def test_buying_coffee_costs_50_cents_and_restores_energy(self):
        self.walk_to_food()
        self.set_money(125)
        self.atari.write_ram(self.sym["energy"], 100)
        self.choose(0)
        self.assertEqual(self.ram("encStr"), D["equates"]["STR_BOUGHT1"])
        self.assertEqual(self.money(), 75)
        self.assertEqual(self.ram("energy"), 140)
        self.snapshot(self.frames(1), "food_bought")
        self.frames(1, fire=True)            # CONTINUE: back to the menu
        self.frames(2)
        self.assertEqual(self.ram("encPhase"), self.sym["PHASE_CHOOSE"])

    def test_energy_is_capped_when_eating(self):
        self.walk_to_food()
        self.set_money(500)
        self.atari.write_ram(self.sym["energy"], 200)
        self.choose(1)                       # meal: +120
        self.assertEqual(self.ram("energy"), self.sym["ENERGY_MAX"])
        self.assertEqual(self.money(), 300)

    def test_leave_the_food_place(self):
        self.walk_to_food()
        self.choose(3)
        self.assertEqual(self.ram("screen"), self.sym["SCREEN_CITY"])

    # --- fights -----------------------------------------------------------------
    def start_fight(self, kind):
        self.start_city()
        self.talk_to_slot(1, kind=self.sym[kind])
        self.atari.write_ram(self.sym["encTemp"], 3)     # angry: no easy way out
        self.choose(3 if kind == "KIND_POLICE" else 1)  # ATTACK / ROB
        self.assertEqual(self.ram("screen"), self.sym["SCREEN_FIGHT"])

    def test_losing_to_a_cop_means_jail(self):
        self.start_fight("KIND_POLICE")
        self.snapshot(self.frames(30), "fight_police")
        self.atari.write_ram(self.sym["energy"], 1)
        for _ in range(400):
            self.frames(1)
            if self.ram("screen") != self.sym["SCREEN_FIGHT"]:
                break
        self.assertEqual(self.ram("screen"), self.sym["SCREEN_ENCOUNTER"])
        self.assertEqual(self.ram("encStr"), D["equates"]["STR_ARREST1"])
        self.frames(1, fire=True)
        self.frames(2)
        self.assertEqual(self.ram("encKind"), self.sym["ENC_JAIL"])
        self.snapshot(self.frames(1), "jail")
        self.atari.write_ram(self.sym["weapon"], 1)
        self.set_money(350)
        self.frames(1, fire=True)
        self.frames(2)
        self.assertEqual(self.ram("screen"), self.sym["SCREEN_CITY"])
        self.assertEqual(self.ram("room"), self.sym["START_ROOM"])
        self.assertEqual(self.ram("weapon"), 0)
        self.assertEqual(self.ram("energy"), self.sym["ENERGY_MAX"])
        self.assertEqual(self.money(), 150)

    def test_beating_a_cop_lets_you_get_away(self):
        self.start_fight("KIND_POLICE")
        self.atari.write_ram(self.sym["foeHP"], 1)
        for _ in range(300):
            self.frames(1, right=True)
            self.frames(1, fire=True, right=True)
            if self.ram("screen") != self.sym["SCREEN_FIGHT"]:
                break
        self.assertEqual(self.ram("encStr"), D["equates"]["STR_FLED1"])
        self.frames(1, fire=True)
        self.frames(2)
        self.assertEqual(self.ram("screen"), self.sym["SCREEN_CITY"])

    def test_winning_a_robbery_pays_three_dollars(self):
        self.start_fight("KIND_PASSERBY")
        self.snapshot(self.frames(30), "fight_passerby")
        self.atari.write_ram(self.sym["foeHP"], 1)
        for _ in range(300):
            self.frames(1, right=True)
            self.frames(1, fire=True, right=True)
            if self.ram("screen") != self.sym["SCREEN_FIGHT"]:
                break
        self.assertEqual(self.ram("encStr"), D["equates"]["STR_TOOK_CASH1"])
        self.assertEqual(self.money(), 300)

    def test_blocking_takes_a_quarter_of_the_damage(self):
        self.start_fight("KIND_POLICE")
        energy = self.ram("energy")
        self.atari.write_ram(self.sym["foeAtk"], 9)       # their swing lands next frame
        self.atari.write_ram(self.sym["fx1"], self.ram("fx0") + 22)
        self.frames(1, down=True)
        hit = energy - self.ram("energy")
        self.assertEqual(hit, (24 + 3 * 2) // 4)

    # --- weapons ----------------------------------------------------------------
    def test_picking_up_a_weapon(self):
        self.start_city()
        items = [i for i in range(64) if self.atari.rom_byte(self.sym["RoomItem"] + i, 0)]
        room = items[0]
        self.atari.write_ram(self.sym["room"], room)
        self.atari.write_ram(self.sym["pending"], self.sym["PENDING_TELEPORT"])
        self.frames(3)
        self.assertEqual(self.sc("SC_SLOT_KIND", 2), self.sym["KIND_ITEM"])
        self.atari.write_ram(self.sym["p0x"], self.sc("SC_SLOT_X", 2))
        self.frames(1)
        for _ in range(20):
            self.frames(1, down=True)
        self.frames(1, fire=True)
        self.frames(1)
        self.assertEqual(self.ram("weapon"), self.atari.rom_byte(self.sym["RoomItem"] + room, 0))
        self.assertEqual(self.sc("SC_SLOT_KIND", 2), self.sym["KIND_NONE"])


del NpcTest   # don't re-run the Stage B tests from this module


if __name__ == "__main__":
    unittest.main()

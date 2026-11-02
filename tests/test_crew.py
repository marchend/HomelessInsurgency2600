"""Stage D: recruiting, the crew, collapse, winning Act 1, sound."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_outcomes import D, FlowHelpers  # noqa: E402
from test_rom import setUpModule  # noqa: E402,F401

PERSON_MET, PERSON_RECRUITED = 4, 8


def to_bcd(n):
    return ((n // 10) << 4) | n % 10


class CrewTest(FlowHelpers):
    def person(self, p):
        return self.sc("SC_PEOPLE", p)

    def set_type(self, p, t):
        self.set_sc("SC_PEOPLE", p, (self.person(p) & ~3) | t)

    def talk_to_homeless(self, ptype):
        self.start_city()
        p = self.sc("SC_SLOT_PERSON", 1)
        self.set_type(p, ptype)
        self.talk_to_slot(1)
        self.assertEqual(self.ram("encTemp"), ptype)
        return p

    def recruit(self, ptype, money=500):
        p = self.talk_to_homeless(ptype)
        hi, lo = divmod(money, 100)
        self.atari.write_ram(self.sym["money"], to_bcd(hi))
        self.atari.write_ram(self.sym["money"] + 1, to_bcd(lo))
        self.choose(D["recruit"]["opener"][ptype])
        self.assertEqual(self.ram("encPhase"), self.sym["PHASE_ROUND2"])
        self.assertEqual(self.ram("encStr"), D["recruit"]["q1"][ptype])
        self.choose(D["recruit"]["answer"][ptype])
        return p

    # --- recruiting -------------------------------------------------------------
    def test_each_type_joins_with_the_right_two_answers(self):
        for t in range(4):
            with self.subTest(type=t):
                self.setUp()
                p = self.recruit(t)
                self.assertEqual(self.ram("encStr"), D["equates"]["STR_JOINED1"])
                self.assertTrue(self.person(p) & PERSON_RECRUITED)
                self.assertEqual(self.ram("recruits"), 1)
                self.assertEqual(self.sc("SC_SLOT_KIND", 1), self.sym["KIND_NONE"])

    def test_a_wrong_opener_gets_their_type_s_refusal(self):
        for t in range(4):
            with self.subTest(type=t):
                self.setUp()
                p = self.talk_to_homeless(t)
                self.atari.write_ram(self.sym["money"], 5)
                wrong = (D["recruit"]["opener"][t] + 1) % 3
                self.choose(wrong)
                self.assertEqual(self.ram("encStr"), D["recruit"]["no1"][t])
                self.assertFalse(self.person(p) & PERSON_RECRUITED)

    def test_a_wrong_second_answer_is_also_refused(self):
        p = self.talk_to_homeless(0)
        self.choose(D["recruit"]["opener"][0])
        self.choose((D["recruit"]["answer"][0] + 1) % 3)
        self.assertEqual(self.ram("encStr"), D["recruit"]["no1"][0])
        self.assertFalse(self.person(p) & PERSON_RECRUITED)

    def test_sharing_food_costs_50_cents_or_fails_when_broke(self):
        self.talk_to_homeless(3)                   # angry-irrational wants food
        self.choose(D["equates"]["SHARE_FOOD_CHOICE"])
        self.assertEqual(self.ram("encStr"), D["equates"]["STR_NO_FOOD1"])
        self.setUp()
        self.recruit(3, money=125)
        self.assertEqual(self.money(), 75)
        self.assertEqual(self.ram("encStr"), D["equates"]["STR_JOINED1"])

    def test_recruits_leave_the_street(self):
        p = self.recruit(0)
        self.frames(1, fire=True)                   # CONTINUE
        self.frames(2)
        self.atari.write_ram(self.sym["pending"], self.sym["PENDING_TELEPORT"])
        self.frames(3)                               # reload the room
        self.assertNotEqual(self.sc("SC_SLOT_PERSON", 1), p)

    # --- known count ------------------------------------------------------------
    def test_meeting_someone_new_adds_to_known_once(self):
        self.talk_to_homeless(0)
        self.assertEqual(self.sc("SC_KNOWN"), 1)
        self.choose(3)                              # walk away
        self.talk_to_slot(1)
        self.assertEqual(self.sc("SC_KNOWN"), 1)

    def test_a_shelter_tip_makes_its_residents_known(self):
        self.start_city()
        residents = sum(1 for p in range(40)
                        if self.atari.rom_byte(self.sym["PersonShelter"] + p, 5) == 0)
        self.atari.call(self.sym["LearnShelter"], 5)
        self.assertEqual(self.ram("shelters"), 1)
        self.assertEqual(self.sc("SC_KNOWN"), to_bcd(residents))

    # --- followers --------------------------------------------------------------
    def test_one_follower_per_five_recruits(self):
        self.start_city()
        for n in (0, 4, 5, 9, 10, 24, 25, 26):
            self.atari.write_ram(self.sym["recruits"], to_bcd(n))
            self.atari.call(self.sym["SetFollowers"], 5)
            self.assertEqual(self.ram("followers"), n // 5, n)

    def test_followers_walk_behind_the_player(self):
        self.start_city()
        self.atari.write_ram(self.sym["followers"], 3)
        self.snapshot(self.frames(2), "city_followers")

    # --- the crew's hunger ------------------------------------------------------
    def test_an_unfed_crew_loses_a_recruit(self):
        self.start_city()
        for p in range(5):
            self.set_sc("SC_PEOPLE", p, self.person(p) | PERSON_RECRUITED)
        self.atari.write_ram(self.sym["recruits"], 5)
        self.atari.write_ram(self.sym["followers"], 1)
        self.set_sc("SC_HUNGER", 0, D["equates"]["DESERT_AT"] - 1)
        for _ in range(260):
            self.frames(1)
            if self.ram("screen") != self.sym["SCREEN_CITY"]:
                break
        self.assertEqual(self.ram("encKind"), self.sym["ENC_CREW"])
        self.assertEqual(self.ram("recruits"), 4)
        self.assertEqual(self.ram("followers"), 0)
        self.snapshot(self.frames(1), "crew_left")

    def test_feeding_the_crew_costs_a_dollar_each_and_ends_hunger(self):
        self.walk_to_food()
        self.atari.write_ram(self.sym["followers"], 2)
        self.set_sc("SC_HUNGER", 0, 40)
        self.set_money(500)
        self.choose(2)
        self.assertEqual(self.money(), 300)
        self.assertEqual(self.sc("SC_HUNGER"), 0)

    def test_only_a_fed_crew_fights(self):
        for hunger, expected in ((0, 10 - 3), (D["equates"]["HUNGRY_AT"], 10 - 1)):
            with self.subTest(hunger=hunger):
                self.setUp()
                self.start_fight("KIND_POLICE")
                self.atari.write_ram(self.sym["followers"], 2)
                self.set_sc("SC_HUNGER", 0, hunger)
                self.atari.write_ram(self.sym["foeHP"], 10)
                self.atari.write_ram(self.sym["fx1"], self.ram("fx0") + 22)
                self.atari.write_ram(self.sym["foeCool"], 200)
                self.atari.write_ram(self.sym["plAtk"], 9)
                self.frames(1)
                self.assertEqual(self.ram("foeHP"), expected)

    # --- collapse and winning ---------------------------------------------------
    def test_collapsing_wakes_you_poorer_with_some_energy(self):
        self.start_city()
        self.set_money(150)
        self.atari.write_ram(self.sym["energy"], 0)
        self.frames(2)
        self.assertEqual(self.ram("encKind"), self.sym["ENC_COLLAPSE"])
        self.snapshot(self.frames(1), "collapse")
        self.frames(1, fire=True)
        self.frames(3)
        self.assertEqual(self.ram("screen"), self.sym["SCREEN_CITY"])
        self.assertEqual(self.ram("energy"), D["equates"]["COLLAPSE_ENERGY"])
        self.assertEqual(self.money(), 50)

    def test_the_26th_recruit_wins_act_1(self):
        self.start_city()
        self.atari.write_ram(self.sym["recruits"], to_bcd(25))
        p = self.sc("SC_SLOT_PERSON", 1)
        self.set_type(p, 0)
        self.talk_to_slot(1)
        self.choose(D["recruit"]["opener"][0])
        self.choose(D["recruit"]["answer"][0])
        self.assertEqual(self.ram("encKind"), self.sym["ENC_WON"])
        self.assertEqual(self.ram("recruits"), to_bcd(26))
        self.snapshot(self.frames(1), "won")
        self.frames(1, fire=True)
        self.frames(3)
        self.assertEqual(self.ram("screen"), self.sym["SCREEN_TITLE"])

    # --- sound ------------------------------------------------------------------
    def test_recruiting_plays_a_sound(self):
        self.recruit(0)
        self.assertGreater(self.atari.tia.reg[0x19], 0)     # AUDV0


if __name__ == "__main__":
    unittest.main()

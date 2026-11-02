"""Stage B: city NPCs and encounters."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))

import build_dialogue  # noqa: E402
from test_rom import RomCase, setUpModule  # noqa: E402,F401

SLOT_Y = [67, 50, 34, 16, 1]


def p1_line(slot):
    """A visible line (line B of a pair) in the middle of a slot's sprite."""
    pair = SLOT_Y[slot] + 4
    return (77 - pair) * 2 + 1


class NpcHelpers(RomCase):
    def walk_to_slot(self, slot):
        for _ in range(200):
            dx = self.sc("SC_SLOT_X", slot) - self.ram("p0x")
            if abs(dx) < 6:
                return
            self.frames(1, right=dx > 0, left=dx < 0)
        self.fail("could not reach the NPC")

    def talk_to_slot(self, slot, kind=None):
        if kind is not None:
            self.set_sc("SC_SLOT_KIND", slot, kind)
            self.frames(1)
        self.walk_to_slot(slot)
        self.frames(1, fire=True)
        self.frames(1)
        self.assertEqual(self.ram("screen"), self.sym["SCREEN_ENCOUNTER"])

    def enc_str(self, i):
        return self.atari.read_ram(self.sym["encStr"] + i)


class NpcTest(NpcHelpers):
    # --- city ---------------------------------------------------------------
    def test_start_room_has_a_homeless_person_in_the_top_street(self):
        self.start_city()
        self.assertEqual(self.sc("SC_SLOT_KIND", 1), self.sym["KIND_HOMELESS"])
        self.assertEqual(self.sc("SC_SLOT_PERSON", 1), 0)

    def test_each_section_draws_its_npc_at_its_x(self):
        self.start_city()
        checked = set()
        for _ in range(150):                # street walkers sweep across x
            xs = [self.sc("SC_SLOT_X", s) for s in range(5)]
            kinds = [self.sc("SC_SLOT_KIND", s) for s in range(5)]
            frame = self.frames(1)
            for slot in range(5):
                if kinds[slot]:
                    self.assertEqual(frame.p1_pos[p1_line(slot)], xs[slot], f"slot {slot}")
                    checked.add((slot, xs[slot]))
        self.assertGreater(len({x for s, x in checked if s in (1, 3)}), 20,
                           "walkers should have covered many x positions")

    def test_npcs_follow_the_player_into_new_rooms(self):
        self.start_city()
        self.frames(250, right=True)        # several rooms; timing checked each frame
        self.frames(120, left=True)

    # --- encounters ---------------------------------------------------------
    def test_homeless_greeting_matches_their_type(self):
        self.start_city()
        person = self.sc("SC_SLOT_PERSON", 1)
        ptype = self.sc("SC_PEOPLE", person) & 3
        self.talk_to_slot(1)
        self.assertEqual(self.ram("encKind"), 0)
        self.assertEqual(self.ram("encTemp"), ptype)
        greet = build_dialogue.build()["greet"]
        g = 0 * 4 + ptype
        pool = [(greet["line1"][i], greet["line2"][i])
                for i in range(greet["start"][g], greet["start"][g] + greet["count"][g])]
        self.assertIn((self.enc_str(0), self.enc_str(1)), pool)
        self.snapshot(self.frames(1), "encounter_homeless")

    def test_police_get_the_four_police_choices(self):
        self.start_city()
        self.talk_to_slot(1, kind=self.sym["KIND_POLICE"])
        choices = build_dialogue.build()["choices"]
        self.assertEqual(self.ram("nChoices"), 4)
        self.assertEqual([self.enc_str(2 + i) for i in range(4)], choices["police"])
        self.snapshot(self.frames(1), "encounter_police")

    def test_passersby_have_three_choices_and_a_blank_line(self):
        self.start_city()
        self.talk_to_slot(1, kind=self.sym["KIND_PASSERBY"])
        choices = build_dialogue.build()["choices"]
        self.assertEqual(self.ram("nChoices"), 3)
        self.assertEqual([self.enc_str(2 + i) for i in range(3)], choices["passerby"])
        self.assertEqual(self.enc_str(5), 0)
        self.snapshot(self.frames(1), "encounter_passerby")

    def test_cursor_stays_within_the_choices(self):
        self.start_city()
        self.talk_to_slot(1)
        for _ in range(6):
            self.frames(1, down=True)
            self.frames(1)
        self.assertEqual(self.ram("cursor"), self.ram("nChoices") - 1)
        for _ in range(6):
            self.frames(1, up=True)
            self.frames(1)
        self.assertEqual(self.ram("cursor"), 0)

    def test_continue_after_a_response_returns_to_the_city(self):
        self.start_city()
        self.talk_to_slot(1)
        self.frames(1, fire=True)           # choose: a response screen
        self.frames(1)
        self.assertEqual(self.ram("screen"), self.sym["SCREEN_ENCOUNTER"])
        self.assertEqual(self.ram("encPhase"), self.sym["PHASE_RESPONSE"])
        self.frames(1, fire=True)           # CONTINUE
        self.frames(1)
        self.assertEqual(self.ram("screen"), self.sym["SCREEN_CITY"])
        xs = [self.sc("SC_SLOT_X", s) for s in range(5)]
        kinds = [self.sc("SC_SLOT_KIND", s) for s in range(5)]
        frame = self.frames(1)
        for slot in range(5):
            if kinds[slot]:
                self.assertEqual(frame.p1_pos[p1_line(slot)], xs[slot])

    def test_fire_away_from_people_does_nothing(self):
        self.start_city()
        for slot in range(5):
            self.set_sc("SC_SLOT_KIND", slot, self.sym["KIND_NONE"])
        self.frames(1, fire=True)
        self.frames(1)
        self.assertEqual(self.ram("screen"), self.sym["SCREEN_CITY"])


if __name__ == "__main__":
    unittest.main()

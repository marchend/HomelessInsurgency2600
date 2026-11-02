"""ROM tests: run bin/hi.bin in tools/vcs_sim.py and check timing and gameplay."""
import os
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))

from vcs_sim import Atari, load_symbols  # noqa: E402

ROM = os.path.join(ROOT, "bin", "hi.bin")
SYM = os.path.join(ROOT, "bin", "hi.sym")
SNAP_DIR = os.path.join(ROOT, "build", "snapshots")


def setUpModule():
    if not shutil.which("dasm"):
        raise unittest.SkipTest("dasm not installed")
    subprocess.run(["make", "-s"], cwd=ROOT, check=True)


class RomTest(unittest.TestCase):
    def setUp(self):
        with open(ROM, "rb") as f:
            self.atari = Atari(f.read())
        self.sym = load_symbols(SYM)

    def ram(self, name):
        return self.atari.read_ram(self.sym[name])

    def frames(self, n, **joy):
        """Run n frames with the joystick held; every frame must be 262/192."""
        self.atari.joystick(**joy)
        frame = None
        for _ in range(n):
            frame = self.atari.run_frame()
            if frame is None or len(self.atari.frame_starts) <= 2:
                continue                # power-on frame: startup runs before the first VSYNC
            self.assertEqual(frame.total_lines, 262, "frame must be exactly 262 scanlines")
            self.assertEqual(frame.visible_lines, 192, "frame must show 192 visible lines")
        self.atari.joystick()
        return frame

    def start_city(self):
        self.frames(3)
        self.frames(1, fire=True)
        self.frames(2)
        self.assertEqual(self.ram("screen"), self.sym["SCREEN_CITY"])

    def snapshot(self, frame, name):
        os.makedirs(SNAP_DIR, exist_ok=True)
        frame.to_png(os.path.join(SNAP_DIR, name + ".png"))

    # --- title ----------------------------------------------------------------
    def test_title_holds_steady_timing(self):
        frame = self.frames(70)
        self.snapshot(frame, "title")
        self.assertEqual(self.ram("screen"), self.sym["SCREEN_TITLE"])

    def test_fire_held_at_power_on_does_not_skip_the_title(self):
        self.frames(10, fire=True)
        self.assertEqual(self.ram("screen"), self.sym["SCREEN_TITLE"])
        self.frames(2)                   # release, then a fresh press starts
        self.frames(1, fire=True)
        self.frames(1)
        self.assertEqual(self.ram("screen"), self.sym["SCREEN_CITY"])

    def test_fire_starts_the_city_in_the_start_room(self):
        self.start_city()
        self.assertEqual(self.ram("room"), self.sym["START_ROOM"])
        self.snapshot(self.frames(1), "city_start")

    # --- city -------------------------------------------------------------------
    def test_walking_left_moves_one_pixel_per_frame(self):
        self.start_city()
        x = self.ram("p0x")
        self.frames(10, left=True)
        self.assertEqual(self.ram("p0x"), x - 10)

    def test_buildings_block_the_player(self):
        self.start_city()
        self.frames(36, left=True)      # x = 40: under a building, not a street
        self.frames(30, up=True)
        top_row = self.ram("p0y") + self.sym["PLAYER_H"] - 1
        self.assertLessEqual(top_row, 65, "player walked into the top building band")
        self.assertGreaterEqual(top_row, 63, "player stopped short of the building")

    def test_walking_off_the_right_edge_enters_the_next_room(self):
        self.start_city()
        start = self.ram("room")
        self.frames(90, right=True)
        self.assertEqual(self.ram("room"), start + 1)
        self.snapshot(self.frames(1), "city_room_right")

    def test_vertical_street_leads_to_the_room_above(self):
        self.start_city()                # start room has a centre street at x 72-87
        start = self.ram("room")
        self.frames(30, up=True)
        self.assertEqual(self.ram("room"), start - 8)
        # 16 steps reach the top edge, then the player enters at the bottom
        # of the room above and keeps walking for the remaining 13
        self.assertEqual(self.ram("p0y"), 13)
        self.snapshot(self.frames(1), "city_room_up")

    def test_timing_holds_at_every_x_position(self):
        self.start_city()
        self.frames(80, left=True)       # far left (x = 0)
        self.frames(160, right=True)     # across the room to the far right and beyond

    def test_walking_drains_energy(self):
        self.start_city()
        energy = self.ram("energy")
        self.frames(64, left=True)
        self.assertEqual(self.ram("energy"), energy - 2)

    def test_standing_still_keeps_energy(self):
        self.start_city()
        energy = self.ram("energy")
        self.frames(64)
        self.assertEqual(self.ram("energy"), energy)


if __name__ == "__main__":
    unittest.main()

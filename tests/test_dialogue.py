import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))

from dialogue import parse_greetings  # noqa: E402

TEMPERAMENTS = {
    "homeless": ["calm_rational", "calm_irrational", "angry_rational", "angry_irrational"],
    "police": ["calm", "less_calm", "angry", "really_angry"],
    "passerby": ["patient", "less_patient", "impatient", "angry_impatient"],
}


class GreetingsFileTest(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, "assets", "dialogue", "greetings.txt")) as f:
            self.greetings = parse_greetings(f.read())

    def test_every_temperament_has_at_least_three_greetings(self):
        for kind, temperaments in TEMPERAMENTS.items():
            for t in temperaments:
                section = f"{kind}.{t}"
                self.assertIn(section, self.greetings)
                self.assertGreaterEqual(len(self.greetings[section]), 3, section)

    def test_no_unexpected_sections(self):
        expected = {f"{k}.{t}" for k, ts in TEMPERAMENTS.items() for t in ts}
        self.assertEqual(set(self.greetings), expected)

    def test_greetings_are_unique_across_temperaments(self):
        # a repeated greeting would make the tell ambiguous
        seen = {}
        for section, greetings in self.greetings.items():
            for g in greetings:
                key = " ".join(g)
                self.assertNotIn(key, seen, f"'{key}' in {section} and {seen.get(key)}")
                seen[key] = section


class ParserTest(unittest.TestCase):
    def test_rejects_long_line(self):
        with self.assertRaisesRegex(ValueError, "16 chars"):
            parse_greetings("[a]\nTHIS IS TOO LONG")

    def test_rejects_three_screen_lines(self):
        with self.assertRaisesRegex(ValueError, "more than 2"):
            parse_greetings("[a]\nONE / TWO / THREE")

    def test_rejects_lowercase(self):
        with self.assertRaisesRegex(ValueError, "unsupported"):
            parse_greetings("[a]\nhello")

    def test_parses_one_and_two_line_greetings(self):
        self.assertEqual(parse_greetings("[a]\nHI\nHEY / YOU"),
                         {"a": [["HI"], ["HEY", "YOU"]]})


if __name__ == "__main__":
    unittest.main()

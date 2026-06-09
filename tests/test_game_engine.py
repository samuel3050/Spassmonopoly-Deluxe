import unittest

from engine.game_engine import can_be_purchased, normalize_text


class GameEngineTextTests(unittest.TestCase):
    def test_normalize_text_handles_german_sharp_s(self):
        self.assertEqual(normalize_text("Straße"), "strasse")

    def test_street_fields_are_buyable_with_german_name(self):
        self.assertTrue(can_be_purchased({"typ": "Straße"}))


if __name__ == "__main__":
    unittest.main()

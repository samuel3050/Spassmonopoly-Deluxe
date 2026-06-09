import unittest

from engine.game_engine import apply_field_effect, can_be_purchased, init_game, move_player, normalize_text, roll_dice


FIELDS = [
    {
        "feld_id": 1,
        "name": "Los",
        "typ": "Los",
        "kaufpreis": None,
        "miete": None,
        "farbe": "Dunkelgrau",
        "besitzer": None,
    },
    {
        "feld_id": 2,
        "name": "Teststrasse",
        "typ": "Strasse",
        "kaufpreis": "2 Punkte",
        "miete": "1 Punkt",
        "farbe": "Braun",
        "besitzer": None,
    },
    {
        "feld_id": 3,
        "name": "Steuerfeld",
        "typ": "Steuer",
        "kaufpreis": None,
        "miete": "2 Punkte",
        "farbe": "Rot",
        "besitzer": None,
    },
    {
        "feld_id": 4,
        "name": "Gemeinschaft",
        "typ": "Gemeinschaft",
        "kaufpreis": None,
        "miete": None,
        "farbe": "Blau",
        "besitzer": None,
    },
]


class GameEngineTextTests(unittest.TestCase):
    def test_normalize_text_handles_german_sharp_s(self):
        self.assertEqual(normalize_text("Stra\u00dfe"), "strasse")

    def test_street_fields_are_buyable_with_german_name(self):
        self.assertTrue(can_be_purchased({"typ": "Stra\u00dfe"}))


class GameEngineFlowTests(unittest.TestCase):
    def test_full_turn_creates_structured_events(self):
        state = init_game({"players": ["Samuel", "Lukas"], "fields": FIELDS})

        state = roll_dice(state, dice=[1, 1])
        self.assertEqual(state["game"]["phase"], "move")
        self.assertEqual(state["event_log"][-1]["type"], "dice_roll")

        state = move_player(state)
        self.assertEqual(state["game"]["phase"], "field_action")
        self.assertEqual(state["players"][0]["position"], 2)
        self.assertEqual(state["event_log"][-1]["type"], "movement")

        state = apply_field_effect(state, action="skip")
        self.assertEqual(state["game"]["phase"], "roll")
        self.assertEqual(state["active_player_index"], 1)
        self.assertEqual(state["players"][0]["action_points"], 2)
        self.assertEqual(state["event_log"][-2]["type"], "field_effect")
        self.assertEqual(state["event_log"][-1]["type"], "turn_change")

    def test_community_card_moves_between_deck_drawn_and_discard(self):
        state = init_game({"players": ["Samuel", "Lukas"], "fields": FIELDS})
        before_count = len(state["cards"]["gemeinschaft"]["deck"])

        state = roll_dice(state, dice=[1, 2])
        state = move_player(state)
        state = apply_field_effect(state, action="skip")

        community = state["cards"]["gemeinschaft"]
        self.assertEqual(len(community["deck"]), before_count - 1)
        self.assertEqual(len(community["drawn"]), 1)
        self.assertEqual(len(community["discard"]), 1)
        self.assertEqual(state["event_log"][-2]["type"], "card_event")

    def test_property_purchase_updates_owner_and_points(self):
        state = init_game({"players": ["Samuel", "Lukas"], "fields": FIELDS})
        state = roll_dice(state, dice=[1, 4])
        state = move_player(state)
        state = apply_field_effect(state, action="kaufen")

        field = state["board"]["fields"][1]
        self.assertEqual(field["besitzer"], "Samuel")
        self.assertEqual(field["owner_player_id"], state["players"][0]["id"])
        self.assertEqual(state["players"][0]["action_points"], 2)


if __name__ == "__main__":
    unittest.main()

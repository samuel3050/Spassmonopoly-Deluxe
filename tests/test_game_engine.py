import unittest

from engine.game_engine import (
    START_BONUS,
    STARTING_POINTS,
    apply_field_effect,
    can_be_purchased,
    init_game,
    move_player,
    normalize_text,
    roll_dice,
)


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


# Board with several streets so a single purchase never ends the game on its own.
ECON_FIELDS = [
    {"feld_id": 1, "name": "Los", "typ": "Los", "kaufpreis": None, "miete": None, "farbe": "Dunkelgrau", "besitzer": None},
    {"feld_id": 2, "name": "Park", "typ": "Gemeinschaft", "kaufpreis": None, "miete": None, "farbe": "Blau", "besitzer": None},
    {"feld_id": 3, "name": "Strasse A", "typ": "Strasse", "kaufpreis": "5 Punkte", "miete": "3 Punkte", "farbe": "Braun", "besitzer": None},
    {"feld_id": 4, "name": "Strasse B", "typ": "Strasse", "kaufpreis": "4 Punkte", "miete": "2 Punkte", "farbe": "Gelb", "besitzer": None},
    {"feld_id": 5, "name": "Steuerfeld", "typ": "Steuer", "kaufpreis": None, "miete": "2 Punkte", "farbe": "Rot", "besitzer": None},
    {"feld_id": 6, "name": "Werk", "typ": "Werk", "kaufpreis": "6 Punkte", "miete": "3 Punkte", "farbe": "Lila", "besitzer": None},
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
        # Landed on the tax field: pays 2 points out of the starting capital.
        self.assertEqual(state["players"][0]["action_points"], STARTING_POINTS - 2)
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
        # Rolling 5 on a 4-field board passes Los (+START_BONUS) before buying for 2.
        self.assertEqual(state["players"][0]["action_points"], STARTING_POINTS + START_BONUS - 2)

    def test_money_economy_start_capital_buy_rent_and_los_bonus(self):
        state = init_game({"players": ["Samuel", "Lukas"], "fields": ECON_FIELDS})
        self.assertEqual(state["players"][0]["action_points"], STARTING_POINTS)
        self.assertEqual(state["players"][1]["action_points"], STARTING_POINTS)

        # Samuel rolls 2 -> lands on Strasse A (no Los pass) and buys it for 5.
        state = roll_dice(state, dice=[1, 1])
        state = move_player(state)
        state = apply_field_effect(state, action="kaufen")
        self.assertEqual(state["board"]["fields"][2]["besitzer"], "Samuel")
        self.assertEqual(state["players"][0]["action_points"], STARTING_POINTS - 5)

        # Lukas rolls 2 -> lands on Samuel's Strasse A and pays 3 rent to Samuel.
        samuel_before = state["players"][0]["action_points"]
        state = roll_dice(state, dice=[1, 1])
        state = move_player(state)
        state = apply_field_effect(state, action="miete")
        self.assertEqual(state["players"][1]["action_points"], STARTING_POINTS - 3)
        self.assertEqual(state["players"][0]["action_points"], samuel_before + 3)

        # Samuel rolls 6 from position 2 -> passes Los (+START_BONUS) back onto his own field.
        samuel_before = state["players"][0]["action_points"]
        state = roll_dice(state, dice=[3, 3])
        state = move_player(state)
        state = apply_field_effect(state, action="skip")
        self.assertEqual(state["players"][0]["action_points"], samuel_before + START_BONUS)

    def test_bankrupt_player_is_eliminated_and_last_player_wins(self):
        state = init_game({"players": ["Samuel", "Lukas"], "fields": ECON_FIELDS})

        # Samuel buys Strasse A (index 2, rent 3).
        state = roll_dice(state, dice=[1, 1])
        state = move_player(state)
        state = apply_field_effect(state, action="kaufen")
        self.assertEqual(state["active_player_index"], 1)

        # Lukas is nearly broke and lands on Samuel's field: rent 3 > 1 -> out.
        state["players"][1]["action_points"] = 1
        state = roll_dice(state, dice=[1, 1])
        state = move_player(state)
        state = apply_field_effect(state, action="miete")

        self.assertEqual(state["players"][1]["status"], "bankrupt")
        self.assertEqual(state["players"][1]["action_points"], 0)
        self.assertEqual(state["game"]["status"], "finished")
        self.assertEqual(state["event_log"][-1]["type"], "winner")
        self.assertIn("Samuel", state["event_log"][-1]["message"])


if __name__ == "__main__":
    unittest.main()

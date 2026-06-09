import importlib
import os
import tempfile
import unittest

from sqlalchemy import inspect


class FlaskGameFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DB_ENGINE"] = "sqlite"
        os.environ["DB_FILE"] = os.path.join(cls.temp_dir.name, "test-spassmonopoly.db")
        os.environ["GAME_ROOM_ID"] = "test_room"
        os.environ["FLASK_SECRET_KEY"] = "test-secret"

        cls.game_module = importlib.import_module("game")
        cls.database_module = importlib.import_module("engine.database")
        cls.game_module.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        with cls.game_module.app.app_context():
            cls.database_module.db.session.remove()
            cls.database_module.db.engine.dispose()
        cls.temp_dir.cleanup()

    def setUp(self):
        self.client = self.game_module.app.test_client()

    def test_required_database_tables_exist(self):
        with self.game_module.app.app_context():
            tables = set(inspect(self.database_module.db.engine).get_table_names())

        self.assertTrue({"games", "players", "game_states", "logs", "cards", "settings"}.issubset(tables))

    def test_local_game_http_flow_and_save_list(self):
        response = self.client.post("/", data={"anzahl": "2"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/namen", response.headers["Location"])

        response = self.client.post(
            "/namen",
            data={"spieler1": "Samuel", "spieler2": "Lukas"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/board", response.headers["Location"])

        state_response = self.client.get("/api/state").get_json()
        self.assertTrue(state_response["ok"])
        self.assertEqual(state_response["state"]["phase"], "roll")

        roll_response = self.client.post("/zug_wuerfeln").get_json()
        self.assertTrue(roll_response["ok"])
        self.assertEqual(roll_response["state"]["phase"], "move")

        move_response = self.client.post("/zug_ziehen").get_json()
        self.assertTrue(move_response["ok"])
        self.assertEqual(move_response["state"]["phase"], "field_action")

        pending_field = move_response["state"]["popupFeld"]
        active_name = move_response["state"]["activePlayerName"]
        if pending_field.get("ist_kaufbar") and not pending_field.get("besitzer"):
            action = "kaufen"
        elif pending_field.get("besitzer") and pending_field.get("besitzer") != active_name:
            action = "miete"
        else:
            action = "skip"

        action_response = self.client.post(
            "/feld_aktion",
            json={"aktion": action, "feld": pending_field["feld_id"]},
        ).get_json()
        self.assertTrue(action_response["ok"])
        self.assertEqual(action_response["state"]["phase"], "roll")
        self.assertNotEqual(action_response["state"]["aktiver"], 0)

        saves_response = self.client.get("/api/saves").get_json()
        self.assertTrue(saves_response["ok"])
        self.assertGreaterEqual(len(saves_response["saves"]), 1)

        manual_save = self.client.post("/api/save-current").get_json()
        self.assertTrue(manual_save["ok"])
        self.assertEqual(manual_save["state"]["phase"], "roll")
        self.assertIn("gespeichert", manual_save["message"])

        save_id = self.client.get("/api/saves").get_json()["saves"][0]["id"]
        loaded = self.client.post(f"/api/save/{save_id}/load").get_json()
        self.assertTrue(loaded["ok"])

        restored = self.client.get("/api/state").get_json()
        self.assertTrue(restored["ok"])
        self.assertEqual(restored["state"]["phase"], "roll")
        self.assertEqual(restored["state"]["aktiver"], manual_save["state"]["aktiver"])

        exited = self.client.post("/api/exit-game", json={"mode": "save"}).get_json()
        self.assertTrue(exited["ok"])
        self.assertEqual(exited["redirect_url"], "/")

    def test_invalid_save_state_is_rejected_before_commit(self):
        with self.game_module.app.app_context():
            with self.assertRaises(ValueError):
                self.game_module.GameSaveService.create_save(
                    "broken-save",
                    {"players": [{"id": "p1", "name": "Only one"}], "board": {"fields": []}},
                )


if __name__ == "__main__":
    unittest.main()

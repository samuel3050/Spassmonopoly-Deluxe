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
        cls.models_module = importlib.import_module("engine.models")
        cls.game_module.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        with cls.game_module.app.app_context():
            cls.database_module.db.session.remove()
            cls.database_module.db.engine.dispose()
        cls.temp_dir.cleanup()

    def setUp(self):
        with self.game_module.app.app_context():
            for model in (
                self.models_module.Player,
                self.models_module.Field,
                self.models_module.GameEvent,
                self.models_module.GameStateSnapshot,
                self.models_module.Card,
                self.models_module.Setting,
                self.models_module.GameSave,
            ):
                self.database_module.db.session.query(model).delete()
            self.database_module.db.session.commit()
        self.game_module.lobby_state.clear()
        self.game_module.lobby_state.update(self.game_module.default_lobby_state(self.game_module.ROOM_ID))
        self.game_module.board_store.reset_owners()
        self.client = self.game_module.app.test_client()

    def test_required_database_tables_exist(self):
        with self.game_module.app.app_context():
            tables = set(inspect(self.database_module.db.engine).get_table_names())

        self.assertTrue({"games", "players", "game_states", "logs", "cards", "settings"}.issubset(tables))

    def test_local_game_http_flow_and_save_list(self):
        response = self.client.post("/menu", data={"anzahl": "2"})
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

        manual_save = self.client.post("/api/save-current", json={"name": "Freitag Abend Runde"}).get_json()
        self.assertTrue(manual_save["ok"])
        self.assertEqual(manual_save["state"]["phase"], "roll")
        self.assertIn("gespeichert", manual_save["message"])

        saves = self.client.get("/api/saves").get_json()["saves"]
        named_save = next(save for save in saves if save["name"] == "Freitag Abend Runde")
        save_id = named_save["id"]

        renamed = self.client.post(f"/api/save/{save_id}/rename", json={"name": "Finale Runde"}).get_json()
        self.assertTrue(renamed["ok"])
        self.assertEqual(renamed["save"]["name"], "Finale Runde")
        self.assertTrue({"id", "name", "game_id", "join_code", "host_id", "player_count", "round"}.issubset(renamed["save"]))

        duplicated = self.client.post(f"/api/save/{save_id}/duplicate", json={"name": "Finale Runde Kopie"}).get_json()
        self.assertTrue(duplicated["ok"])
        duplicate_id = duplicated["save"]["id"]
        self.assertNotEqual(duplicated["save"]["game_id"], renamed["save"]["game_id"])
        self.assertNotEqual(duplicated["save"]["join_code"], renamed["save"]["join_code"])

        duplicate_name = self.client.post(f"/api/save/{save_id}/duplicate", json={"name": "Finale Runde Kopie"})
        self.assertEqual(duplicate_name.status_code, 400)
        self.assertFalse(duplicate_name.get_json()["ok"])

        deleted = self.client.post(f"/api/save/{duplicate_id}/delete").get_json()
        self.assertTrue(deleted["ok"])

        default_duplicate = self.client.post(f"/api/save/{save_id}/duplicate", json={}).get_json()
        self.assertTrue(default_duplicate["ok"])
        self.assertEqual(default_duplicate["save"]["name"], "Kopie von Finale Runde")
        default_duplicate_id = default_duplicate["save"]["id"]
        self.assertTrue(self.client.post(f"/api/save/{default_duplicate_id}/delete").get_json()["ok"])

        invalid_rename = self.client.post(f"/api/save/{save_id}/rename", json={"name": "Bad/Name"})
        self.assertEqual(invalid_rename.status_code, 400)
        self.assertFalse(invalid_rename.get_json()["ok"])

        missing_save = self.client.post("/api/save/not-a-save/rename", json={"name": "Gibt es nicht"})
        self.assertEqual(missing_save.status_code, 404)
        self.assertFalse(missing_save.get_json()["ok"])

        loaded = self.client.post(f"/api/save/{save_id}/load").get_json()
        self.assertTrue(loaded["ok"])

        restored = self.client.get("/api/state").get_json()
        self.assertTrue(restored["ok"])
        self.assertEqual(restored["state"]["phase"], "roll")
        self.assertEqual(restored["state"]["aktiver"], manual_save["state"]["aktiver"])

        exited = self.client.post("/api/exit-game", json={"mode": "save"}).get_json()
        self.assertTrue(exited["ok"])
        self.assertEqual(exited["redirect_url"], "/menu")

    def test_settings_api_persists_global_preferences(self):
        saved = self.client.post(
            "/api/settings",
            json={
                "volume": "44",
                "music_volume": "25",
                "effects_volume": "90",
                "muted": "on",
                "animations": "off",
                "theme": "light",
                "speed": "instant",
            },
        ).get_json()
        self.assertTrue(saved["ok"])
        self.assertEqual(saved["settings"]["volume"], "44")
        self.assertEqual(saved["settings"]["music_volume"], "25")
        self.assertEqual(saved["settings"]["effects_volume"], "90")
        self.assertEqual(saved["settings"]["muted"], "on")
        self.assertEqual(saved["settings"]["theme"], "light")
        self.assertNotIn("autosave", saved["settings"])

        loaded = self.client.get("/api/settings").get_json()
        self.assertTrue(loaded["ok"])
        self.assertEqual(loaded["settings"]["speed"], "instant")

    def test_lobby_rejects_duplicate_names(self):
        first_client = self.game_module.app.test_client()
        second_client = self.game_module.app.test_client()

        self.assertTrue(first_client.post("/lobby/new").status_code in {302, 303})
        first_join = first_client.post("/lobby/join", data={"name": "Mara"}).get_json()
        self.assertTrue(first_join["ok"])

        duplicate_response = second_client.post("/lobby/join", data={"name": "Mara"})
        duplicate = duplicate_response.get_json()
        self.assertEqual(duplicate_response.status_code, 409)
        self.assertFalse(duplicate["ok"])

    def test_only_lobby_host_can_start_game(self):
        host_client = self.game_module.app.test_client()
        guest_client = self.game_module.app.test_client()

        self.assertTrue(host_client.post("/lobby/new").status_code in {302, 303})
        self.assertTrue(host_client.post("/lobby/join", data={"name": "Host"}).get_json()["ok"])
        self.assertTrue(guest_client.post("/lobby/join", data={"name": "Gast"}).get_json()["ok"])
        self.assertTrue(host_client.post("/lobby/ready").get_json()["ok"])
        self.assertTrue(guest_client.post("/lobby/ready").get_json()["ok"])

        guest_start = guest_client.post("/lobby/start")
        self.assertEqual(guest_start.status_code, 403)
        self.assertFalse(guest_start.get_json()["ok"])

        host_start = host_client.post("/lobby/start").get_json()
        self.assertTrue(host_start["ok"])
        self.assertEqual(host_start["redirect_url"], "/board")

    def test_lobby_save_load_rejoin_and_continue_after_other_game(self):
        host_client = self.game_module.app.test_client()
        guest_client = self.game_module.app.test_client()

        self.assertTrue(host_client.post("/lobby/new").status_code in {302, 303})
        host_join = host_client.post("/lobby/join", data={"name": "Samuel"}).get_json()
        guest_join = guest_client.post("/lobby/join", data={"name": "Lukas"}).get_json()
        self.assertTrue(host_join["ok"])
        self.assertTrue(guest_join["ok"])
        self.assertTrue(host_client.post("/lobby/ready").get_json()["ok"])
        self.assertTrue(guest_client.post("/lobby/ready").get_json()["ok"])
        self.assertTrue(host_client.post("/lobby/start").get_json()["ok"])

        self.assertTrue(host_client.post("/zug_wuerfeln").get_json()["ok"])
        moved = host_client.post("/zug_ziehen").get_json()["state"]
        field = moved["popupFeld"]
        action = "kaufen" if field.get("ist_kaufbar") and not field.get("besitzer") else "skip"
        after_action = host_client.post("/feld_aktion", json={"aktion": action, "feld": field["feld_id"]}).get_json()
        self.assertTrue(after_action["ok"])
        self.assertEqual(after_action["state"]["activePlayerName"], "Lukas")

        saved = host_client.post("/api/save-current", json={"name": "Rejoin Altspiel"}).get_json()
        self.assertTrue(saved["ok"])
        save_id = saved["save"]["id"]
        self.assertEqual(saved["save"]["host_id"], host_join["player_id"])
        self.assertTrue(saved["save"]["join_code"])
        guest_save_attempt = guest_client.post("/api/save-current", json={"name": "Gast darf nicht speichern"})
        self.assertEqual(guest_save_attempt.status_code, 403)
        self.assertFalse(guest_save_attempt.get_json()["ok"])
        guest_rename_attempt = guest_client.post(f"/api/save/{save_id}/rename", json={"name": "Gast Rename"})
        self.assertEqual(guest_rename_attempt.status_code, 403)
        self.assertFalse(guest_rename_attempt.get_json()["ok"])
        guest_duplicate_attempt = guest_client.post(f"/api/save/{save_id}/duplicate", json={"name": "Gast Kopie"})
        self.assertEqual(guest_duplicate_attempt.status_code, 403)
        self.assertFalse(guest_duplicate_attempt.get_json()["ok"])
        guest_delete_attempt = guest_client.post(f"/api/save/{save_id}/delete")
        self.assertEqual(guest_delete_attempt.status_code, 403)
        self.assertFalse(guest_delete_attempt.get_json()["ok"])

        response = host_client.post("/menu", data={"anzahl": "2"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/namen", response.headers["Location"])
        response = host_client.post("/namen", data={"spieler1": "Neu A", "spieler2": "Neu B"})
        self.assertEqual(response.status_code, 302)

        denied_load = guest_client.post(f"/api/save/{save_id}/load")
        self.assertEqual(denied_load.status_code, 403)
        self.assertFalse(denied_load.get_json()["ok"])

        loaded = host_client.post(f"/api/save/{save_id}/load").get_json()
        self.assertTrue(loaded["ok"])
        self.assertEqual(loaded["redirect_url"], "/board")

        returning_guest = self.game_module.app.test_client()
        rejoined = returning_guest.post("/lobby/join", data={"name": "Lukas", "join_code": saved["save"]["join_code"]}).get_json()
        self.assertTrue(rejoined["ok"])
        self.assertTrue(rejoined["game_started"])
        self.assertEqual(rejoined["player_id"], guest_join["player_id"])

        state = returning_guest.get("/api/state").get_json()["state"]
        self.assertEqual(state["activePlayerName"], "Lukas")
        self.assertTrue(state["canAct"])
        self.assertFalse(state["isHost"])
        self.assertTrue(returning_guest.post("/zug_wuerfeln").get_json()["ok"])

    def test_invalid_save_state_is_rejected_before_commit(self):
        with self.game_module.app.app_context():
            with self.assertRaises(ValueError):
                self.game_module.GameSaveService.create_save(
                    "broken-save",
                    {"players": [{"id": "p1", "name": "Only one"}], "board": {"fields": []}},
                )


if __name__ == "__main__":
    unittest.main()

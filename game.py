import copy
import os
import random
import re
import unicodedata
from contextlib import contextmanager

try:
    from flask import Flask, jsonify, redirect, render_template, request, session, url_for
except ImportError as exc:
    raise SystemExit(
        "Flask ist nicht installiert. Bitte fuehre `pip install -r requirements.txt` im Ordner "
        "`Spassmonopoly-Deluxe` aus."
    ) from exc

try:
    import mysql.connector
except ImportError:
    mysql = None
else:
    mysql = mysql.connector

from board_data import DEFAULT_FIELDS


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "spassmonopoly-deluxe-dev-key")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "saufmonopoly"),
}

COLOR_MAP = {
    "gelb": "#f2c94c",
    "rot": "#d96459",
    "blau": "#4a7cf3",
    "orange": "#f28c28",
    "schwarz": "#2f3640",
    "lila": "#7d53de",
    "gold": "#b8860b",
    "grun": "#1f9d74",
    "gruen": "#1f9d74",
    "pink": "#d96cb3",
    "cyan": "#31c6d4",
    "weiss": "#f5f7fa",
    "braun": "#8d5a3b",
    "hellblau": "#76b7ff",
    "dunkelgrau": "#495057",
    "rainbow": "linear-gradient(135deg, #f2c94c, #f28c28, #d96459)",
}


def normalize_text(value):
    text = str(value or "").strip().lower().replace("ß", "ss")
    text = unicodedata.normalize("NFKD", text)
    return "".join(char for char in text if not unicodedata.combining(char))


def parse_number(text):
    match = re.search(r"(\d+)", str(text or ""))
    return int(match.group(1)) if match else 0


def can_be_purchased(field):
    return normalize_text(field.get("typ")) in {"strasse", "bahnhof", "werk"}


def copy_fields(fields):
    return [dict(field) for field in fields]


class BoardStore:
    def __init__(self):
        self._memory_fields = copy_fields(DEFAULT_FIELDS)
        self._db_status_checked = False
        self._db_available = False

    def _ensure_field_shape(self, fields):
        normalized = []
        for index, field in enumerate(fields):
            normalized.append(
                {
                    "feld_id": int(field["feld_id"]),
                    "name": field.get("name", ""),
                    "typ": field.get("typ", ""),
                    "kaufpreis": field.get("kaufpreis"),
                    "miete": field.get("miete"),
                    "farbe": field.get("farbe", "Dunkelgrau"),
                    "farbe_css": COLOR_MAP.get(normalize_text(field.get("farbe")), "#4f7d5c"),
                    "alkohol_typ": field.get("alkohol_typ", "Wasser"),
                    "alkohol_menge": field.get("alkohol_menge", "0"),
                    "zusatz_regel": field.get("zusatz_regel"),
                    "besitzer": field.get("besitzer"),
                    "index": index,
                    "ist_kaufbar": can_be_purchased(field),
                }
            )
        return normalized

    def _check_db(self):
        if self._db_status_checked:
            return self._db_available

        self._db_status_checked = True
        if mysql is None:
            self._db_available = False
            return False

        try:
            connection = mysql.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT COUNT(*) AS anzahl FROM spielfelder")
            result = cursor.fetchone() or {}
            self._db_available = int(result.get("anzahl", 0)) >= 40
        except Exception:
            self._db_available = False
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                connection.close()
            except Exception:
                pass

        return self._db_available

    @contextmanager
    def _db_cursor(self, dictionary=False):
        if not self._check_db():
            raise RuntimeError("Database not available")

        connection = mysql.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=dictionary)
        try:
            yield cursor
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    def load_fields(self):
        if self._check_db():
            try:
                with self._db_cursor(dictionary=True) as cursor:
                    cursor.execute("SELECT * FROM spielfelder ORDER BY feld_id ASC")
                    return self._ensure_field_shape(cursor.fetchall())
            except Exception:
                self._db_available = False

        return self._ensure_field_shape(copy.deepcopy(self._memory_fields))

    def reset_owners(self):
        for field in self._memory_fields:
            field["besitzer"] = None

        if self._check_db():
            try:
                with self._db_cursor() as cursor:
                    cursor.execute("UPDATE spielfelder SET besitzer = NULL")
            except Exception:
                self._db_available = False

    def set_owner(self, field_id, owner_name):
        updated = False
        for field in self._memory_fields:
            if int(field["feld_id"]) == int(field_id):
                field["besitzer"] = owner_name
                updated = True
                break

        if self._check_db():
            try:
                with self._db_cursor() as cursor:
                    cursor.execute(
                        "UPDATE spielfelder SET besitzer = %s WHERE feld_id = %s",
                        (owner_name, field_id),
                    )
            except Exception:
                self._db_available = False

        return updated


board_store = BoardStore()


def get_board_state():
    fields = board_store.load_fields()
    ownership = {}
    for field in fields:
        owner = field.get("besitzer")
        if owner:
            ownership.setdefault(owner, []).append(field)
    return fields, ownership


def ensure_game_in_session():
    return bool(session.get("spieler")) and bool(session.get("positionen"))


def redirect_if_game_missing():
    if not ensure_game_in_session():
        return redirect(url_for("index"))
    return None


def get_scoreboard(fields):
    owner_counts = {}
    for field in fields:
        owner = field.get("besitzer")
        if owner:
            owner_counts[owner] = owner_counts.get(owner, 0) + 1

    names = session.get("spieler", [])
    positions = session.get("positionen", [])
    drinks = session.get("konto", [])
    steps = session.get("gesamt", [])
    active_index = session.get("aktiver", 0)

    scoreboard = []
    for index, name in enumerate(names):
        position_index = positions[index]
        current_field = fields[position_index]
        scoreboard.append(
            {
                "name": name,
                "position": current_field["name"],
                "drinks": drinks[index],
                "steps": steps[index],
                "properties": owner_counts.get(name, 0),
                "is_active": index == active_index,
            }
        )
    return scoreboard


def get_active_player_name():
    names = session.get("spieler", [])
    if not names:
        return None
    active_index = session.get("aktiver", 0) % len(names)
    return names[active_index]


def push_event(message):
    history = list(session.get("verlauf", []))
    history.insert(0, message)
    session["verlauf"] = history[:8]
    session["last_event"] = message


def get_ownership_summary(ownership):
    summary = []
    for owner, fields in ownership.items():
        summary.append(
            {
                "owner": owner,
                "count": len(fields),
                "fields": [field["name"] for field in fields],
            }
        )

    summary.sort(key=lambda entry: (-entry["count"], entry["owner"].lower()))
    return summary


def build_game_payload(fields=None, ownership=None):
    if fields is None or ownership is None:
        fields, ownership = get_board_state()

    pending_popup = session.get("pending_popup")
    waiting_for_roll = session.get("warte_auf_wurf", True)
    active_index = session.get("aktiver", 0)
    players = session.get("spieler", [])
    popup_field = None
    popup_player = None
    popup_roll = None

    if pending_popup:
        popup_field = fields[pending_popup["field_index"]]
        popup_player = pending_popup["spieler"]
        popup_roll = pending_popup["wurf"]

    phase = "roll"
    if pending_popup:
        phase = "field_action"
    elif not waiting_for_roll:
        phase = "move"

    return {
        "spieler": players,
        "aktiver": active_index,
        "activePlayerName": get_active_player_name(),
        "felder": fields,
        "positionen": session.get("positionen", []),
        "konto": session.get("konto", []),
        "gesamt": session.get("gesamt", []),
        "wurf": session.get("wurf"),
        "displayRoll": session.get("wurf") or popup_roll or session.get("letzter_wurf"),
        "popupWurf": popup_roll,
        "popupFeld": popup_field,
        "popupSpieler": popup_player,
        "scoreboard": get_scoreboard(fields),
        "ownership": get_ownership_summary(ownership),
        "phase": phase,
        "zeigeWurfPopup": phase == "move",
        "zeigeFeldinfo": bool(pending_popup),
        "lastEvent": session.get("last_event"),
        "eventLog": session.get("verlauf", []),
    }


def render_board():
    fields, ownership = get_board_state()
    return render_template("board.html", game_state=build_game_payload(fields, ownership))


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        player_count = max(2, min(8, int(request.form["anzahl"])))
        session.clear()
        board_store.reset_owners()
        session["anzahl"] = player_count
        return redirect(url_for("namen"))

    return render_template("index.html")


@app.route("/namen", methods=["GET", "POST"])
def namen():
    if "anzahl" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        players = []
        for index in range(1, session["anzahl"] + 1):
            raw_name = request.form.get(f"spieler{index}", "").strip()
            players.append(raw_name or f"Spieler {index}")

        session["spieler"] = players
        session["positionen"] = [0 for _ in players]
        session["aktiver"] = 0
        session["konto"] = [0 for _ in players]
        session["gesamt"] = [0 for _ in players]
        session["pending_popup"] = None
        session["warte_auf_wurf"] = True
        session["wurf"] = None
        session["letzter_wurf"] = None
        session["verlauf"] = []
        push_event(f"{players[0]} beginnt die Runde.")
        return redirect(url_for("spiel"))

    return render_template("spielernamen.html", anzahl=session["anzahl"])


@app.route("/board", methods=["GET"])
def spiel():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return missing_game

    return render_board()


@app.route("/zug_wuerfeln", methods=["POST"])
def zug_wuerfeln():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return jsonify({"ok": False, "msg": "Spiel wurde nicht gestartet."}), 400

    waiting_for_roll = session.get("warte_auf_wurf", True)
    if not waiting_for_roll or session.get("pending_popup"):
        return jsonify({"ok": False, "msg": "Der aktuelle Zug muss zuerst abgeschlossen werden."}), 400

    dice_1 = random.randint(1, 6)
    dice_2 = random.randint(1, 6)
    roll = [dice_1, dice_2]

    session["wurf"] = roll
    session["letzter_wurf"] = roll
    session["warte_auf_wurf"] = False
    push_event(f"{get_active_player_name()} hat {dice_1 + dice_2} gewuerfelt.")
    session.modified = True
    return jsonify({"ok": True, "state": build_game_payload()})


@app.route("/zug_ziehen", methods=["POST"])
def zug_ziehen():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return jsonify({"ok": False, "msg": "Spiel wurde nicht gestartet."}), 400

    fields, _ = get_board_state()
    active_index = session.get("aktiver", 0)
    waiting_for_roll = session.get("warte_auf_wurf", True)
    pending_popup = session.get("pending_popup")
    roll = session.get("wurf")

    if waiting_for_roll or pending_popup:
        return jsonify({"ok": False, "msg": "Es gibt gerade keinen bestaetigten Wurf zum Ziehen."}), 400
    if not roll:
        session["warte_auf_wurf"] = True
        return jsonify({"ok": False, "msg": "Der Wurf ist nicht mehr verfuegbar."}), 400

    movement = roll[0] + roll[1]
    positions = list(session.get("positionen", []))
    totals = list(session.get("gesamt", []))

    new_position = (positions[active_index] + movement) % len(fields)
    positions[active_index] = new_position
    totals[active_index] += movement

    session["positionen"] = positions
    session["gesamt"] = totals
    session["pending_popup"] = {
        "spieler": active_index,
        "field_index": new_position,
        "wurf": roll,
    }
    session["wurf"] = None
    push_event(f"{get_active_player_name()} zieht auf {fields[new_position]['name']}.")
    session.modified = True
    return jsonify({"ok": True, "state": build_game_payload()})


@app.route("/feld_aktion", methods=["POST"])
def feld_aktion():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return jsonify({"ok": False, "msg": "Spiel wurde nicht gestartet."}), 400

    payload = request.get_json(silent=True) or {}
    action = payload.get("aktion")
    field_id = payload.get("feld")
    pending_popup = session.get("pending_popup")

    if not pending_popup or not field_id:
        return jsonify({"ok": False, "msg": "Kein aktiver Zug vorhanden."}), 400

    fields, _ = get_board_state()
    field = next((item for item in fields if int(item["feld_id"]) == int(field_id)), None)
    if not field:
        return jsonify({"ok": False, "msg": "Spielfeld wurde nicht gefunden."}), 404
    if field["index"] != pending_popup["field_index"]:
        return jsonify({"ok": False, "msg": "Bitte zuerst das aktuelle Feld auswerten."}), 400

    active_index = pending_popup["spieler"]
    player_name = session["spieler"][active_index]
    drinks = list(session.get("konto", []))

    if action == "kaufen":
        if not field["ist_kaufbar"]:
            return jsonify({"ok": False, "msg": "Dieses Feld kann nicht gekauft werden."}), 400
        if field.get("besitzer"):
            return jsonify({"ok": False, "msg": "Dieses Feld gehoert bereits jemandem."}), 400

        board_store.set_owner(field["feld_id"], player_name)
        drinks[active_index] += parse_number(field.get("kaufpreis"))
        session["konto"] = drinks
        push_event(f"{player_name} kauft {field['name']} fuer {field.get('kaufpreis') or '0'}.")

    elif action == "miete":
        if field.get("besitzer") and field["besitzer"] != player_name:
            drinks[active_index] += parse_number(field.get("miete"))
            session["konto"] = drinks
            push_event(
                f"{player_name} zahlt auf {field['name']} {field.get('miete') or '0'} an {field['besitzer']}."
            )

    elif action != "skip":
        return jsonify({"ok": False, "msg": "Unbekannte Aktion."}), 400
    elif field.get("besitzer") == player_name:
        push_event(f"{player_name} landet auf dem eigenen Feld {field['name']}.")
    else:
        push_event(f"{player_name} beendet den Zug auf {field['name']}.")

    session["pending_popup"] = None
    session["warte_auf_wurf"] = True
    session["aktiver"] = (active_index + 1) % len(session["spieler"])
    session.modified = True
    push_event(f"{get_active_player_name()} ist als Naechstes am Zug.")
    session.modified = True
    return jsonify({"ok": True, "state": build_game_payload()})


@app.route("/neues_spiel", methods=["POST"])
def neues_spiel():
    session.clear()
    board_store.reset_owners()
    return redirect(url_for("index"))


if __name__ == "__main__":
    board_store.reset_owners()
    app.run(debug=True)

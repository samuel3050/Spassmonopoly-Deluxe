import copy
import os
import random
import re
import unicodedata
from contextlib import contextmanager
from uuid import uuid4

try:
    from flask import Flask, jsonify, redirect, render_template, request, session, url_for
except ImportError as exc:
    raise SystemExit(
        "Flask ist nicht installiert. Bitte führe `pip install -r requirements.txt` im Ordner "
        "`Spassmonopoly-Deluxe` aus."
    ) from exc

try:
    import mysql.connector
except ImportError:
    mysql = None
else:
    mysql = mysql.connector

from board_data import DEFAULT_FIELDS
from engine.state_io import (
    DEFAULT_ROOM_ID as DEFAULT_SAVE_ROOM_ID,
    delete_game_state as delete_saved_room,
    has_save_game as has_room_save,
    load_game_state as read_room_save,
    save_game_state as write_room_save,
)

APP_NAME = "Spaßmonopoly Deluxe"
DEFAULT_ROOM_ID = os.getenv("GAME_ROOM_ID", DEFAULT_SAVE_ROOM_ID)
ROOM_SAVE_VERSION = 1

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "spassmonopoly-deluxe-dev-key")
app.json.ensure_ascii = False

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "spassmonopoly"),
}

COLOR_MAP = {
    "gelb": "#f7d659",
    "rot": "#ef6b63",
    "blau": "#68a6ff",
    "orange": "#ffb255",
    "schwarz": "#444b54",
    "lila": "#a98bff",
    "gold": "#d7a53d",
    "grun": "#7ed88f",
    "gruen": "#7ed88f",
    "pink": "#ff8bc2",
    "cyan": "#7dd9e8",
    "weiss": "#ffffff",
    "braun": "#c99b73",
    "hellblau": "#8ed0ff",
    "dunkelgrau": "#6d7783",
    "rainbow": "linear-gradient(135deg, #ffd25f, #ff9c6b, #ff7fb4)",
}

SPECIAL_FIELD_RULES = {
    10: {"delta_self": -2, "message": "Ideenjoker: 2 Aktionspunkte zurück."},
    20: {"delta_self": -1, "message": "Ruheoase: 1 Aktionspunkt zurück."},
    30: {"delta_all": -1, "message": "Fairplay-Zentrale: Alle erhalten 1 Aktionspunkt zurück."},
    40: {"delta_all": 1, "message": "Finale der Freude: Alle erhalten 1 zusätzlichen Aktionspunkt."},
}

# Global lobby state
lobby_state = {
    'players': {},  # {player_id: {'name': str, 'ready': bool}}
    'game_started': False
}

# Global game state for multiplayer
game_state = {
    'players': [],
    'player_ids': [],
    'positions': [],
    'points': [],
    'totals': [],
    'active_player': 0,
    'round': 1,
    'turn': 1,
    'waiting_for_roll': True,
    'roll': None,
    'pending_popup': None,
    'event_log': []
}

board_store = None


def default_game_state():
    return {
        'players': [],
        'player_ids': [],
        'positions': [],
        'points': [],
        'totals': [],
        'active_player': 0,
        'round': 1,
        'turn': 1,
        'waiting_for_roll': True,
        'roll': None,
        'letzter_wurf': None,
        'pending_popup': None,
        'event_log': [],
        'last_event': None,
        'board': {
            'fields': [],
        },
        'room_id': DEFAULT_ROOM_ID,
    }


def default_lobby_state():
    return {
        'players': {},
        'game_started': False,
        'room_id': DEFAULT_ROOM_ID,
    }


def current_room_id():
    return session.get("room_id") or DEFAULT_ROOM_ID


def normalize_loaded_room(snapshot):
    if not isinstance(snapshot, dict):
        return None
    if "game_state" in snapshot:
        return snapshot
    if "players" in snapshot:
        return {
            "schema_version": ROOM_SAVE_VERSION,
            "room_id": snapshot.get("room_id", DEFAULT_ROOM_ID),
            "lobby_state": default_lobby_state(),
            "game_state": snapshot,
        }
    return None


def load_game_state(room_id=DEFAULT_ROOM_ID):
    snapshot = normalize_loaded_room(read_room_save(room_id))
    if not snapshot:
        return None

    loaded_game = default_game_state()
    loaded_game.update(snapshot.get("game_state") or {})
    loaded_game["room_id"] = room_id
    loaded_game.setdefault("board", {})
    loaded_game["board"].setdefault("fields", [])

    loaded_lobby = default_lobby_state()
    loaded_lobby.update(snapshot.get("lobby_state") or {})
    loaded_lobby["room_id"] = room_id

    game_state.clear()
    game_state.update(loaded_game)
    lobby_state.clear()
    lobby_state.update(loaded_lobby)
    return game_state


def save_game_state(room_id=DEFAULT_ROOM_ID):
    fields = game_state.get("board", {}).get("fields")
    if not fields and board_store is not None:
        game_state.setdefault("board", {})["fields"] = board_store.load_fields()

    snapshot = {
        "schema_version": ROOM_SAVE_VERSION,
        "room_id": room_id,
        "lobby_state": copy.deepcopy(lobby_state),
        "game_state": copy.deepcopy(game_state),
    }
    write_room_save(room_id, snapshot)
    return snapshot


def create_new_game(room_id=DEFAULT_ROOM_ID, lobby_entries=None):
    entries = list(lobby_entries or [])
    player_names = [entry[1]["name"] for entry in entries]
    player_ids = [entry[0] for entry in entries]

    game_state.clear()
    game_state.update(default_game_state())
    game_state["room_id"] = room_id
    game_state["players"] = player_names
    game_state["player_ids"] = player_ids
    game_state["positions"] = [0 for _ in player_names]
    game_state["points"] = [0 for _ in player_names]
    game_state["totals"] = [0 for _ in player_names]
    if board_store is not None:
        board_store.reset_owners()
    game_state["board"]["fields"] = board_store.load_fields() if board_store is not None else []

    if player_names:
        push_event(f"{player_names[0]} erÃ¶ffnet Runde 1.")

    lobby_state["game_started"] = bool(player_names)
    lobby_state["room_id"] = room_id
    save_game_state(room_id)
    return game_state

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

def clamp_points(points, index, delta):
    points[index] = max(0, points[index] + delta)

def get_field_type(field):
    return normalize_text(field.get("typ"))

def get_popup_hint(field):
    if not field:
        return None

    field_type = get_field_type(field)
    if field["ist_kaufbar"] and not field.get("besitzer"):
        return f"Dieses Feld ist frei. Du kannst es jetzt für {field.get('kaufpreis') or '0'} sichern oder weiterziehen."
    if field.get("besitzer"):
        return f"Dieses Feld gehört {field['besitzer']}. Die angezeigte Abgabe wird jetzt bestätigt."
    if field_type == "gemeinschaft":
        return "Dieses Gemeinschaftsfeld wirkt sofort auf die ganze Runde."
    if field_type == "steuer":
        return f"Dieses Feld löst eine feste Abgabe von {field.get('miete') or '0'} aus."
    if field_type == "gefangnis":
        return "Dieses Feld verhängt eine kurze Spielstrafe in Form zusätzlicher Aktionspunkte."
    if field_type == "los":
        return "Auf Los bekommst du einen kleinen Bonus zurück."
    if field_type == "spezial":
        return field.get("zusatz_regel") or "Dieses Spezialfeld hat einen eigenen Effekt."
    return field.get("zusatz_regel")

def apply_non_property_effect(field, active_index, players, points):
    field_type = get_field_type(field)
    player_name = players[active_index]

    if field_type == "los":
        clamp_points(points, active_index, -1)
        return f"{player_name} landet auf Los und erhält 1 Aktionspunkt zurück."

    if field_type == "gemeinschaft":
        for index in range(len(players)):
            clamp_points(points, index, -1)
        return f"{player_name} aktiviert {field['name']}: Alle erhalten 1 Aktionspunkt zurück."

    if field_type == "steuer":
        amount = parse_number(field.get("miete"))
        clamp_points(points, active_index, amount)
        return f"{player_name} zahlt auf {field['name']} {field.get('miete') or '0'}."

    if field_type == "gefangnis":
        clamp_points(points, active_index, 2)
        return f"{player_name} macht auf {field['name']} einen Pflichtstopp und erhält 2 Aktionspunkte."

    if field_type == "spezial":
        rule = SPECIAL_FIELD_RULES.get(int(field["feld_id"]))
        if rule is None:
            return f"{player_name} löst auf {field['name']} einen Spezialeffekt aus."
        if "delta_self" in rule:
            clamp_points(points, active_index, rule["delta_self"])
        if "delta_all" in rule:
            for index in range(len(players)):
                clamp_points(points, index, rule["delta_all"])
        return f"{player_name} aktiviert {field['name']}. {rule['message']}"

    return f"{player_name} beendet den Zug auf {field['name']}."

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
                    "farbe_css": COLOR_MAP.get(normalize_text(field.get("farbe")), "#9fb7a3"),
                    "alkohol_typ": field.get("alkohol_typ", "Bonus"),
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
            raise RuntimeError("Datenbank nicht verfügbar")

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

if board_store is None:
    board_store = BoardStore()
    if not load_game_state(DEFAULT_ROOM_ID):
        game_state.setdefault("board", {})["fields"] = board_store.load_fields()

def get_board_state():
    saved_fields = game_state.get("board", {}).get("fields")
    fields = copy_fields(saved_fields) if saved_fields else board_store.load_fields()
    ownership = {}
    for field in fields:
        owner = field.get("besitzer")
        if owner:
            ownership.setdefault(owner, []).append(field)
    return fields, ownership

def persist_board_fields(fields):
    game_state.setdefault("board", {})["fields"] = copy_fields(fields)

def ensure_game_in_session():
    return bool(game_state.get("players"))

def redirect_if_game_missing():
    if not ensure_game_in_session():
        return redirect(url_for("lobby"))
    return None

def get_current_player_index():
    player_id = session.get("player_id")
    player_ids = game_state.get("player_ids", [])
    if not player_ids:
        return game_state.get("active_player", 0)
    if not player_id or player_id not in player_ids:
        return None
    return player_ids.index(player_id)

def require_active_player():
    current_index = get_current_player_index()
    if current_index is None:
        return "Du bist diesem Spiel nicht als Spieler zugeordnet."
    if current_index != game_state.get("active_player", 0):
        active_name = get_active_player_name() or "ein anderer Spieler"
        return f"Bitte warten: {active_name} ist am Zug."
    return None

def get_scoreboard(fields):
    owner_counts = {}
    for field in fields:
        owner = field.get("besitzer")
        if owner:
            owner_counts[owner] = owner_counts.get(owner, 0) + 1

    names = game_state.get("players", [])
    positions = game_state.get("positions", [])
    points = game_state.get("points", [])
    steps = game_state.get("totals", [])
    active_index = game_state.get("active_player", 0)

    scoreboard = []
    for index, name in enumerate(names):
        position_index = positions[index]
        current_field = fields[position_index]
        scoreboard.append(
            {
                "name": name,
                "position": current_field["name"],
                "drinks": points[index],
                "steps": steps[index],
                "properties": owner_counts.get(name, 0),
                "is_active": index == active_index,
            }
        )
    return scoreboard

def get_active_player_name():
    names = game_state.get("players", [])
    if not names:
        return None
    active_index = game_state.get("active_player", 0) % len(names)
    return names[active_index]

def push_event(message):
    history = list(game_state.get("event_log", []))
    history.insert(0, message)
    game_state["event_log"] = history[:10]
    game_state["last_event"] = message

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

def get_game_highlights(fields, ownership):
    owner_counts = {owner: len(owner_fields) for owner, owner_fields in ownership.items()}
    leader_name = None
    leader_count = 0

    if owner_counts:
        leader_name, leader_count = sorted(owner_counts.items(), key=lambda item: (-item[1], item[0].lower()))[0]

    free_fields = sum(1 for field in fields if field["ist_kaufbar"] and not field.get("besitzer"))
    return {
        "runde": game_state.get("round", 1),
        "zugnummer": game_state.get("turn", 1),
        "leaderName": leader_name,
        "leaderCount": leader_count,
        "freieFelder": free_fields,
    }

def build_game_payload(fields=None, ownership=None):
    if fields is None or ownership is None:
        fields, ownership = get_board_state()

    pending_popup = game_state.get("pending_popup")
    waiting_for_roll = game_state.get("waiting_for_roll", True)
    active_index = game_state.get("active_player", 0)
    players = game_state.get("players", [])
    popup_field = None
    popup_player = None
    popup_roll = None
    popup_hint = None

    if pending_popup:
        popup_field = fields[pending_popup["field_index"]]
        popup_player = pending_popup["spieler"]
        popup_roll = pending_popup["wurf"]
        popup_hint = get_popup_hint(popup_field)

    phase = "roll"
    if pending_popup:
        phase = "field_action"
    elif not waiting_for_roll:
        phase = "move"

    return {
        "appName": APP_NAME,
        "spieler": players,
        "aktiver": active_index,
        "currentPlayerIndex": get_current_player_index(),
        "canAct": get_current_player_index() == active_index,
        "activePlayerName": get_active_player_name(),
        "felder": fields,
        "positionen": game_state.get("positions", []),
        "konto": game_state.get("points", []),
        "gesamt": game_state.get("totals", []),
        "wurf": game_state.get("roll"),
        "displayRoll": game_state.get("roll") or popup_roll or game_state.get("letzter_wurf"),
        "popupWurf": popup_roll,
        "popupFeld": popup_field,
        "popupSpieler": popup_player,
        "popupHint": popup_hint,
        "scoreboard": get_scoreboard(fields),
        "ownership": get_ownership_summary(ownership),
        "highlights": get_game_highlights(fields, ownership),
        "phase": phase,
        "lastEvent": game_state.get("last_event"),
        "eventLog": game_state.get("event_log", []),
    }

def advance_turn_from(active_index):
    next_active = (active_index + 1) % len(game_state["players"])
    game_state["active_player"] = next_active
    game_state["turn"] = game_state.get("turn", 1) + 1

    if next_active == 0:
        game_state["round"] = game_state.get("round", 1) + 1
        push_event(f"Runde {game_state['round']} beginnt. {get_active_player_name()} ist am Zug.")
    else:
        push_event(f"{get_active_player_name()} ist als Nächstes am Zug.")

def render_board():
    fields, ownership = get_board_state()
    return render_template("board.html", game_state=build_game_payload(fields, ownership))

@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("lobby"))

@app.route("/lobby", methods=["GET"])
def lobby_page():
    return render_template("lobby.html", has_saved_game=has_room_save(current_room_id()))

@app.route("/lobby/join", methods=["POST"])
def lobby_join():
    name = request.form.get("name", "").strip()
    if not name:
        return jsonify({"ok": False, "msg": "Name erforderlich"}), 400
    
    player_id = str(uuid4())
    lobby_state['players'][player_id] = {'name': name, 'ready': False}
    session['player_id'] = player_id
    session['player_name'] = name
    session['room_id'] = current_room_id()
    save_game_state(current_room_id())
    
    return jsonify({
        "ok": True,
        "player_id": player_id
    })

@app.route("/lobby/ready", methods=["POST"])
def lobby_ready():
    player_id = session.get('player_id')
    if not player_id or player_id not in lobby_state['players']:
        return jsonify({"ok": False, "msg": "Nicht in der Lobby"}), 400
    
    lobby_state['players'][player_id]['ready'] = not lobby_state['players'][player_id]['ready']
    save_game_state(current_room_id())
    return jsonify({"ok": True})

@app.route("/lobby/state", methods=["GET"])
def lobby_state_api():
    players_list = []
    for pid, pdata in lobby_state['players'].items():
        players_list.append({
            'id': pid,
            'name': pdata['name'],
            'ready': pdata['ready']
        })
    
    all_ready = len(players_list) > 0 and all(p['ready'] for p in players_list)
    
    return jsonify({
        "players": players_list,
        "all_ready": all_ready,
        "game_started": lobby_state['game_started']
    })

@app.route("/lobby/start", methods=["POST"])
def lobby_start():
    # Überprüfe, ob alle bereit sind
    lobby_entries = list(lobby_state['players'].items())
    players_list = [entry[1] for entry in lobby_entries]
    if len(players_list) < 2:
        return jsonify({"ok": False, "msg": "Mindestens 2 Spieler erforderlich"}), 400
    
    if not all(p['ready'] for p in players_list):
        return jsonify({"ok": False, "msg": "Nicht alle Spieler sind bereit"}), 400
    
    create_new_game(current_room_id(), lobby_entries)
    return jsonify({"ok": True})

@app.route("/lobby/continue", methods=["POST"])
def lobby_continue():
    if not load_game_state(current_room_id()):
        return redirect(url_for("lobby"))
    lobby_state["game_started"] = bool(game_state.get("players"))
    save_game_state(current_room_id())
    return redirect(url_for("spiel" if game_state.get("players") else "lobby"))

@app.route("/lobby/new", methods=["POST"])
def lobby_new():
    delete_saved_room(current_room_id())
    game_state.clear()
    game_state.update(default_game_state())
    lobby_state.clear()
    lobby_state.update(default_lobby_state())
    board_store.reset_owners()
    game_state["board"]["fields"] = board_store.load_fields()
    save_game_state(current_room_id())
    return redirect(url_for("lobby"))

@app.route("/", methods=["POST"])
def index_post():
    delete_saved_room(current_room_id())
    player_count = max(2, min(8, int(request.form.get("anzahl", 4))))
    session.clear()
    session["anzahl"] = player_count
    session["room_id"] = DEFAULT_ROOM_ID
    return redirect(url_for("namen"))

@app.route("/namen", methods=["GET", "POST"])
def namen():
    if "anzahl" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        players = []
        for index in range(1, session["anzahl"] + 1):
            raw_name = request.form.get(f"spieler{index}", "").strip()
            players.append(raw_name or f"Spieler {index}")

        entries = [(f"local-player-{index + 1}", {"name": name}) for index, name in enumerate(players)]
        create_new_game(current_room_id(), entries)
        return redirect(url_for("spiel"))

    return render_template("spielernamen.html", anzahl=session["anzahl"])

@app.route("/board", methods=["GET"])
def spiel():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return missing_game

    return render_board()

@app.route("/api/state", methods=["GET"])
def api_state():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return jsonify({"ok": False, "msg": "Das Spiel wurde noch nicht gestartet."}), 404

    return jsonify({"ok": True, "state": build_game_payload()})

@app.route("/zug_wuerfeln", methods=["POST"])
def zug_wuerfeln():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return jsonify({"ok": False, "msg": "Das Spiel wurde noch nicht gestartet."}), 400

    active_error = require_active_player()
    if active_error:
        return jsonify({"ok": False, "msg": active_error, "state": build_game_payload()}), 403

    waiting_for_roll = game_state.get("waiting_for_roll", True)
    if not waiting_for_roll or game_state.get("pending_popup"):
        return jsonify({"ok": False, "msg": "Der aktuelle Zug muss zuerst abgeschlossen werden."}), 400

    dice_1 = random.randint(1, 6)
    dice_2 = random.randint(1, 6)
    roll = [dice_1, dice_2]

    game_state["roll"] = roll
    game_state["letzter_wurf"] = roll
    game_state["waiting_for_roll"] = False
    push_event(f"{get_active_player_name()} hat {dice_1 + dice_2} gewürfelt.")
    save_game_state(current_room_id())
    return jsonify({"ok": True, "state": build_game_payload()})

@app.route("/zug_ziehen", methods=["POST"])
def zug_ziehen():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return jsonify({"ok": False, "msg": "Das Spiel wurde noch nicht gestartet."}), 400

    active_error = require_active_player()
    if active_error:
        return jsonify({"ok": False, "msg": active_error, "state": build_game_payload()}), 403

    fields, _ = get_board_state()
    active_index = game_state.get("active_player", 0)
    waiting_for_roll = game_state.get("waiting_for_roll", True)
    pending_popup = game_state.get("pending_popup")
    roll = game_state.get("roll")

    if waiting_for_roll or pending_popup:
        return jsonify({"ok": False, "msg": "Es gibt gerade keinen bestätigten Wurf zum Ziehen."}), 400
    if not roll:
        game_state["waiting_for_roll"] = True
        return jsonify({"ok": False, "msg": "Der Wurf ist nicht mehr verfügbar."}), 400

    movement = roll[0] + roll[1]
    positions = list(game_state.get("positions", []))
    totals = list(game_state.get("totals", []))

    new_position = (positions[active_index] + movement) % len(fields)
    positions[active_index] = new_position
    totals[active_index] += movement

    game_state["positions"] = positions
    game_state["totals"] = totals
    game_state["pending_popup"] = {
        "spieler": active_index,
        "field_index": new_position,
        "wurf": roll,
    }
    game_state["roll"] = None
    push_event(f"{get_active_player_name()} zieht auf {fields[new_position]['name']}.")
    save_game_state(current_room_id())
    return jsonify({"ok": True, "state": build_game_payload()})

@app.route("/feld_aktion", methods=["POST"])
def feld_aktion():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return jsonify({"ok": False, "msg": "Das Spiel wurde noch nicht gestartet."}), 400

    active_error = require_active_player()
    if active_error:
        return jsonify({"ok": False, "msg": active_error, "state": build_game_payload()}), 403

    payload = request.get_json(silent=True) or {}
    action = payload.get("aktion")
    field_id = payload.get("feld")
    pending_popup = game_state.get("pending_popup")

    if not pending_popup or not field_id:
        return jsonify({"ok": False, "msg": "Kein aktiver Zug vorhanden."}), 400

    fields, _ = get_board_state()
    field = next((item for item in fields if int(item["feld_id"]) == int(field_id)), None)
    if not field:
        return jsonify({"ok": False, "msg": "Spielfeld wurde nicht gefunden."}), 404
    if field["index"] != pending_popup["field_index"]:
        return jsonify({"ok": False, "msg": "Bitte zuerst das aktuelle Feld auswerten."}), 400

    active_index = pending_popup["spieler"]
    player_name = game_state["players"][active_index]
    players = list(game_state["players"])
    points = list(game_state.get("points", []))

    if action == "kaufen":
        if not field["ist_kaufbar"]:
            return jsonify({"ok": False, "msg": "Dieses Feld kann nicht gesichert werden."}), 400
        if field.get("besitzer"):
            return jsonify({"ok": False, "msg": "Dieses Feld gehört bereits jemandem."}), 400

        board_store.set_owner(field["feld_id"], player_name)
        field["besitzer"] = player_name
        fields[field["index"]] = field
        persist_board_fields(fields)
        clamp_points(points, active_index, parse_number(field.get("kaufpreis")))
        game_state["points"] = points
        push_event(f"{player_name} sichert sich {field['name']} für {field.get('kaufpreis') or '0'}.")

    elif action == "miete":
        if not field.get("besitzer") or field["besitzer"] == player_name:
            return jsonify({"ok": False, "msg": "Auf diesem Feld ist keine Abgabe fällig."}), 400

        clamp_points(points, active_index, parse_number(field.get("miete")))
        game_state["points"] = points
        push_event(
            f"{player_name} bestätigt auf {field['name']} die Abgabe von {field.get('miete') or '0'} an {field['besitzer']}."
        )

    elif action == "skip":
        effect_message = apply_non_property_effect(field, active_index, players, points)
        game_state["points"] = points
        push_event(effect_message)

    else:
        return jsonify({"ok": False, "msg": "Unbekannte Aktion."}), 400

    game_state["pending_popup"] = None
    game_state["waiting_for_roll"] = True
    advance_turn_from(active_index)
    save_game_state(current_room_id())
    return jsonify({"ok": True, "state": build_game_payload()})

@app.route("/neues_spiel", methods=["POST"])
def neues_spiel():
    game_state.clear()
    game_state.update(default_game_state())
    lobby_state.clear()
    lobby_state.update(default_lobby_state())
    board_store.reset_owners()
    game_state["board"]["fields"] = board_store.load_fields()
    delete_saved_room(current_room_id())
    save_game_state(current_room_id())
    return redirect(url_for("lobby"))

if __name__ == "__main__":
    board_store = BoardStore()
    if not load_game_state(DEFAULT_ROOM_ID):
        board_store.reset_owners()
        game_state.setdefault("board", {})["fields"] = board_store.load_fields()
    app.run(debug=True, host='0.0.0.0', port=5000)

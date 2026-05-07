import copy
import random
import re
import unicodedata


APP_NAME = "Spassmonopoly Deluxe"
STATE_SCHEMA_VERSION = 1

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
    10: {"delta_self": -2, "message": "Ideenjoker: Du darfst 2 Aktionspunkte abziehen."},
    20: {"delta_self": -1, "message": "Ruheoase: Du darfst 1 Aktionspunkt abziehen."},
    30: {"delta_all": -1, "message": "Fairplay-Zentrale: Allen wird 1 Aktionspunkt erlassen."},
    40: {"delta_all": 1, "message": "Finale der Freude: Alle bekommen 1 zusaetzlichen Aktionspunkt."},
}

GEMEINSCHAFT_EFFECTS = [
    {"delta_self": -2, "message": "Glueck gehabt! Du darfst dir 2 Aktionspunkte abziehen."},
    {"delta_self": 2, "message": "Pech gehabt! Du bekommst 2 Aktionspunkte dazu."},
    {"delta_all": 1, "message": "Eine Runde fuer alle! Jeder bekommt 1 Aktionspunkt."},
    {"delta_all": -1, "message": "Gute Stimmung! Allen wird 1 Aktionspunkt erlassen."},
    {"message": "Nichts passiert. Atmet tief durch."},
]


def normalize_text(value):
    text = str(value or "").strip().lower()
    replacements = {
        "ß": "ss",
        "ä": "a",
        "ö": "o",
        "ü": "u",
        "ÃŸ": "ss",
        "Ã¤": "a",
        "Ã¶": "o",
        "Ã¼": "u",
    }
    for search, replacement in replacements.items():
        text = text.replace(search, replacement)
    text = unicodedata.normalize("NFKD", text)
    return "".join(char for char in text if not unicodedata.combining(char))


def parse_number(text):
    match = re.search(r"(\d+)", str(text or ""))
    return int(match.group(1)) if match else 0


def can_be_purchased(field):
    return normalize_text(field.get("typ")) in {"strasse", "bahnhof", "werk"}


def get_field_type(field):
    return normalize_text(field.get("typ"))


def clamp_points(player, delta):
    player["action_points"] = max(0, int(player.get("action_points", 0)) + int(delta))


def ensure_field_shape(fields):
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
                "owner_player_id": field.get("owner_player_id"),
                "index": index,
                "ist_kaufbar": can_be_purchased(field),
            }
        )
    return normalized


def init_game(config):
    player_names = config.get("players") or config.get("player_names") or []
    if not player_names:
        player_count = max(2, min(8, int(config.get("player_count", 2))))
        player_names = [f"Spieler {index}" for index in range(1, player_count + 1)]

    fields = ensure_field_shape(config.get("fields") or [])
    if not fields:
        raise ValueError("Das Spielfeld ist leer.")

    players = []
    for index, raw_name in enumerate(player_names):
        name = str(raw_name or "").strip() or f"Spieler {index + 1}"
        players.append(
            {
                "id": f"player-{index + 1}",
                "name": name,
                "position": 0,
                "action_points": 0,
                "total_steps": 0,
                "status": "active",
            }
        )

    state = {
        "schema_version": STATE_SCHEMA_VERSION,
        "app_name": config.get("app_name", APP_NAME),
        "game": {
            "status": "running",
            "phase": "roll",
            "round": 1,
            "turn_number": 1,
        },
        "players": players,
        "turn_order": list(range(len(players))),
        "active_player_index": 0,
        "board": {
            "fields": fields,
        },
        "dice": {
            "current_roll": None,
            "last_roll": None,
            "history": [],
        },
        "pending_action": None,
        "last_event": None,
        "event_log": [],
    }
    return push_event(state, f"{players[0]['name']} eroeffnet Runde 1.")


def get_active_player(state):
    players = state.get("players", [])
    if not players:
        raise ValueError("Das Spiel hat keine Spieler.")
    active_index = int(state.get("active_player_index", 0)) % len(players)
    return active_index, players[active_index]


def push_event(game_state, message):
    state = copy.deepcopy(game_state)
    history = list(state.get("event_log", []))
    history.insert(0, message)
    state["event_log"] = history[:10]
    state["last_event"] = message
    return state


def _set_phase(state, phase):
    state.setdefault("game", {})["phase"] = phase


def _require_phase(state, expected_phase, message):
    if state.get("game", {}).get("phase") != expected_phase:
        raise ValueError(message)


def roll_dice(game_state, dice=None, rng=None):
    state = copy.deepcopy(game_state)
    _require_phase(state, "roll", "Der aktuelle Zug muss zuerst abgeschlossen werden.")
    if state.get("pending_action"):
        raise ValueError("Bitte zuerst das aktuelle Feld auswerten.")

    active_index, active_player = get_active_player(state)
    roller = rng or random
    roll = list(dice) if dice is not None else [roller.randint(1, 6), roller.randint(1, 6)]
    if len(roll) != 2 or any(int(value) < 1 or int(value) > 6 for value in roll):
        raise ValueError("Ein Wurf muss aus zwei Wuerfeln zwischen 1 und 6 bestehen.")

    roll = [int(roll[0]), int(roll[1])]
    state["dice"]["current_roll"] = roll
    state["dice"]["last_roll"] = roll
    state["dice"].setdefault("history", []).insert(
        0,
        {
            "player_id": active_player["id"],
            "player_index": active_index,
            "roll": roll,
            "total": sum(roll),
            "turn_number": state["game"].get("turn_number", 1),
        },
    )
    state["dice"]["history"] = state["dice"]["history"][:20]
    _set_phase(state, "move")
    return push_event(state, f"{active_player['name']} hat {sum(roll)} gewuerfelt.")


def move_player(game_state, steps=None):
    state = copy.deepcopy(game_state)
    _require_phase(state, "move", "Es gibt gerade keinen bestaetigten Wurf zum Ziehen.")
    active_index, active_player = get_active_player(state)

    roll = state.get("dice", {}).get("current_roll")
    if steps is None:
        if not roll:
            _set_phase(state, "roll")
            raise ValueError("Der Wurf ist nicht mehr verfuegbar.")
        steps = sum(roll)

    fields = state.get("board", {}).get("fields", [])
    if not fields:
        raise ValueError("Das Spielfeld ist leer.")

    movement = int(steps)
    active_player["position"] = (int(active_player.get("position", 0)) + movement) % len(fields)
    active_player["total_steps"] = int(active_player.get("total_steps", 0)) + movement
    state["players"][active_index] = active_player
    state["pending_action"] = {
        "player_index": active_index,
        "player_id": active_player["id"],
        "field_index": active_player["position"],
        "field_id": fields[active_player["position"]]["feld_id"],
        "roll": roll,
    }
    state["dice"]["current_roll"] = None
    _set_phase(state, "field_action")
    return push_event(state, f"{active_player['name']} zieht auf {fields[active_player['position']]['name']}.")


def apply_non_property_effect(state, field, active_index):
    field_type = get_field_type(field)
    player = state["players"][active_index]

    if field_type == "los":
        clamp_points(player, -1)
        return f"{player['name']} landet auf Los und darf 1 Aktionspunkt abziehen."

    if field_type == "gemeinschaft":
        effect = random.choice(GEMEINSCHAFT_EFFECTS)
        if "delta_self" in effect:
            clamp_points(player, effect["delta_self"])
        if "delta_all" in effect:
            for target in state["players"]:
                clamp_points(target, effect["delta_all"])
        return f"{player['name']} zieht eine Gemeinschaftskarte: {effect['message']}"

    if field_type == "steuer":
        amount = parse_number(field.get("miete"))
        clamp_points(player, amount)
        return f"{player['name']} zahlt auf {field['name']} {field.get('miete') or '0'}."

    if field_type == "gefangnis":
        clamp_points(player, 2)
        return f"{player['name']} macht auf {field['name']} einen Pflichtstopp und bekommt 2 Aktionspunkte."

    if field_type == "spezial":
        rule = SPECIAL_FIELD_RULES.get(int(field["feld_id"]))
        if rule is None:
            return f"{player['name']} loest auf {field['name']} einen Spezialeffekt aus."
        if "delta_self" in rule:
            clamp_points(player, rule["delta_self"])
        if "delta_all" in rule:
            for target in state["players"]:
                clamp_points(target, rule["delta_all"])
        return f"{player['name']} aktiviert {field['name']}. {rule['message']}"

    return f"{player['name']} beendet den Zug auf {field['name']}."


def apply_field_effect(game_state, action="skip", field_id=None):
    state = copy.deepcopy(game_state)
    _require_phase(state, "field_action", "Kein aktiver Zug vorhanden.")
    pending = state.get("pending_action")
    if not pending:
        raise ValueError("Kein aktiver Zug vorhanden.")

    fields = state.get("board", {}).get("fields", [])
    if field_id is None:
        field_id = pending.get("field_id")

    field = next((item for item in fields if int(item["feld_id"]) == int(field_id)), None)
    if not field:
        raise ValueError("Spielfeld wurde nicht gefunden.")
    if int(field["index"]) != int(pending["field_index"]):
        raise ValueError("Bitte zuerst das aktuelle Feld auswerten.")

    active_index = int(pending["player_index"])
    active_player = state["players"][active_index]
    action = action or "skip"

    if action == "kaufen":
        if not field["ist_kaufbar"]:
            raise ValueError("Dieses Feld kann nicht gesichert werden.")
        if field.get("besitzer"):
            raise ValueError("Dieses Feld gehoert bereits jemandem.")

        field["besitzer"] = active_player["name"]
        field["owner_player_id"] = active_player["id"]
        clamp_points(active_player, parse_number(field.get("kaufpreis")))
        message = f"{active_player['name']} sichert sich {field['name']} fuer {field.get('kaufpreis') or '0'}."

    elif action == "miete":
        if not field.get("besitzer") or field.get("owner_player_id") == active_player["id"] or field["besitzer"] == active_player["name"]:
            raise ValueError("Auf diesem Feld ist keine Abgabe faellig.")

        clamp_points(active_player, parse_number(field.get("miete")))
        message = (
            f"{active_player['name']} bestaetigt auf {field['name']} "
            f"die Abgabe von {field.get('miete') or '0'} an {field['besitzer']}."
        )

    elif action == "skip":
        message = apply_non_property_effect(state, field, active_index)

    else:
        raise ValueError("Unbekannte Aktion.")

    state["board"]["fields"][field["index"]] = field
    state["players"][active_index] = active_player
    state["pending_action"] = None
    _set_phase(state, "roll")
    state = push_event(state, message)
    return next_turn(state)


def next_turn(game_state):
    state = copy.deepcopy(game_state)
    players = state.get("players", [])
    if not players:
        raise ValueError("Das Spiel hat keine Spieler.")

    active_index = int(state.get("active_player_index", 0))
    next_active = (active_index + 1) % len(players)
    state["active_player_index"] = next_active
    state.setdefault("game", {})["turn_number"] = int(state["game"].get("turn_number", 1)) + 1

    if next_active == 0:
        state["game"]["round"] = int(state["game"].get("round", 1)) + 1
        return push_event(state, f"Runde {state['game']['round']} beginnt. {players[next_active]['name']} ist am Zug.")

    return push_event(state, f"{players[next_active]['name']} ist als Naechstes am Zug.")

import copy
import random
import re
import unicodedata
from datetime import datetime
from uuid import uuid4


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

DISPLAY_REPLACEMENTS = {
    "\u00c3\u0178": "ss",
    "\u00c3\u00a4": "ae",
    "\u00c3\u00b6": "oe",
    "\u00c3\u00bc": "ue",
    "\u00c3\u201e": "Ae",
    "\u00c3\u2013": "Oe",
    "\u00c3\u0152": "Ue",
    "\u00c3\u0192\u00c5\u00b8": "ss",
    "\u00c3\u0192\u00c2\u00a4": "ae",
    "\u00c3\u0192\u00c2\u00b6": "oe",
    "\u00c3\u0192\u00c2\u00bc": "ue",
    "\u00c3\u0192\u00e2\u20ac\u017e": "Ae",
    "\u00c3\u0192\u00e2\u20ac\u201c": "Oe",
    "\u00c3\u0192\u00c5\u201c": "Ue",
    "\u00e2\u20ac\u201d": "-",
    "\u00c2\u00b7": "-",
    "\u00c2": "",
    "\u00e4": "ae",
    "\u00f6": "oe",
    "\u00fc": "ue",
    "\u00c4": "Ae",
    "\u00d6": "Oe",
    "\u00dc": "Ue",
    "\u00df": "ss",
}


def normalize_text(value):
    text = str(value or "").strip().lower()
    replacements = {
        "\u00df": "ss",
        "\u00e4": "a",
        "\u00f6": "o",
        "\u00fc": "u",
        "\u00c3\u0178": "ss",
        "\u00c3\u00a4": "a",
        "\u00c3\u00b6": "o",
        "\u00c3\u00bc": "u",
        "\u00c3\u0192\u00c5\u00b8": "ss",
        "\u00c3\u0192\u00c2\u00a4": "a",
        "\u00c3\u0192\u00c2\u00b6": "o",
        "\u00c3\u0192\u00c2\u00bc": "u",
    }
    for search, replacement in replacements.items():
        text = text.replace(search, replacement)
    text = unicodedata.normalize("NFKD", text)
    return "".join(char for char in text if not unicodedata.combining(char))


def clean_display_text(value):
    """Return stable ASCII display text for saved data that may contain mojibake."""
    if value is None:
        return None
    text = str(value)
    for search, replacement in DISPLAY_REPLACEMENTS.items():
        text = text.replace(search, replacement)
    return text


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
                "name": clean_display_text(field.get("name", "")),
                "typ": clean_display_text(field.get("typ", "")),
                "kaufpreis": clean_display_text(field.get("kaufpreis")),
                "miete": clean_display_text(field.get("miete")),
                "farbe": clean_display_text(field.get("farbe", "Dunkelgrau")),
                "farbe_css": COLOR_MAP.get(normalize_text(field.get("farbe")), "#9fb7a3"),
                "alkohol_typ": clean_display_text(field.get("alkohol_typ", "Bonus")),
                "alkohol_menge": clean_display_text(field.get("alkohol_menge", "0")),
                "zusatz_regel": clean_display_text(field.get("zusatz_regel")),
                "besitzer": clean_display_text(field.get("besitzer")),
                "owner_player_id": field.get("owner_player_id"),
                "index": index,
                "ist_kaufbar": can_be_purchased(field),
            }
        )
    return normalized


def event_now():
    return datetime.now().isoformat(timespec="seconds")


def make_event(message, event_type="info", severity="info", player_id=None, field_id=None, data=None):
    return {
        "id": str(uuid4()),
        "timestamp": event_now(),
        "type": event_type,
        "severity": severity,
        "player_id": player_id,
        "field_id": field_id,
        "message": clean_display_text(message),
        "data": data or {},
    }


def normalize_event(entry):
    if isinstance(entry, dict):
        normalized = dict(entry)
        normalized.setdefault("id", str(uuid4()))
        normalized.setdefault("timestamp", event_now())
        normalized.setdefault("type", "info")
        normalized.setdefault("severity", "info")
        normalized.setdefault("player_id", None)
        normalized.setdefault("field_id", None)
        normalized.setdefault("data", {})
        normalized["message"] = clean_display_text(normalized.get("message", ""))
        return normalized
    return make_event(str(entry), event_type="legacy", severity="info")


def normalize_event_log(entries):
    return [normalize_event(entry) for entry in list(entries or [])][-80:]


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
        name = clean_display_text(str(raw_name or "").strip()) or f"Spieler {index + 1}"
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
        "board": {"fields": fields},
        "dice": {
            "current_roll": None,
            "last_roll": None,
            "history": [],
        },
        "pending_action": None,
        "last_event": None,
        "event_log": [],
    }
    return push_event(
        state,
        f"Spielstart: {players[0]['name']} eroeffnet Runde 1.",
        event_type="game_start",
        severity="success",
        player_id=players[0]["id"],
    )


def get_active_player(state):
    players = state.get("players", [])
    if not players:
        raise ValueError("Das Spiel hat keine Spieler.")
    active_index = int(state.get("active_player_index", 0)) % len(players)
    return active_index, players[active_index]


def push_event(game_state, message, event_type="info", severity="info", player_id=None, field_id=None, data=None):
    state = copy.deepcopy(game_state)
    history = normalize_event_log(state.get("event_log", []))
    event = make_event(message, event_type, severity, player_id, field_id, data)
    history.append(event)
    state["event_log"] = history[-80:]
    state["last_event"] = event["message"]
    state["last_event_entry"] = event
    return state


def _set_phase(state, phase):
    state.setdefault("game", {})["phase"] = phase


def _require_phase(state, expected_phase, message):
    if state.get("game", {}).get("phase") != expected_phase:
        raise ValueError(message)


def _require_running(state):
    if state.get("game", {}).get("status") == "finished":
        raise ValueError("Diese Runde ist beendet. Starte eine neue Runde, um weiterzuspielen.")


def roll_dice(game_state, dice=None, rng=None):
    state = copy.deepcopy(game_state)
    _require_running(state)
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
    return push_event(
        state,
        f"{active_player['name']} wuerfelt {sum(roll)} ({roll[0]} + {roll[1]}).",
        event_type="dice_roll",
        severity="info",
        player_id=active_player["id"],
        data={"roll": roll, "total": sum(roll)},
    )


def move_player(game_state, steps=None):
    state = copy.deepcopy(game_state)
    _require_running(state)
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
    start_position = int(active_player.get("position", 0))
    active_player["position"] = (start_position + movement) % len(fields)
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
    return push_event(
        state,
        f"{active_player['name']} zieht von Feld {start_position + 1} auf Feld {active_player['position'] + 1}: {fields[active_player['position']]['name']}.",
        event_type="movement",
        severity="info",
        player_id=active_player["id"],
        field_id=fields[active_player["position"]]["feld_id"],
        data={"from": start_position, "to": active_player["position"], "steps": movement},
    )


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
    _require_running(state)
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
        event_type = "field_purchase"
        severity = "success"

    elif action == "miete":
        is_own_field = field.get("owner_player_id") == active_player["id"] or field.get("besitzer") == active_player["name"]
        if not field.get("besitzer") or is_own_field:
            raise ValueError("Auf diesem Feld ist keine Abgabe faellig.")

        clamp_points(active_player, parse_number(field.get("miete")))
        message = (
            f"{active_player['name']} bestaetigt auf {field['name']} "
            f"die Abgabe von {field.get('miete') or '0'} an {field['besitzer']}."
        )
        event_type = "penalty"
        severity = "warning"

    elif action == "skip":
        message = apply_non_property_effect(state, field, active_index)
        event_type = "card_event" if get_field_type(field) == "gemeinschaft" else "field_effect"
        severity = "warning" if get_field_type(field) in {"steuer", "gefangnis"} else "info"

    else:
        raise ValueError("Unbekannte Aktion.")

    state["board"]["fields"][field["index"]] = field
    state["players"][active_index] = active_player
    state["pending_action"] = None
    _set_phase(state, "roll")
    state = push_event(
        state,
        message,
        event_type=event_type,
        severity=severity,
        player_id=active_player["id"],
        field_id=field["feld_id"],
        data={"action": action, "field": field["name"]},
    )
    return next_turn(maybe_finish_game(state))


def maybe_finish_game(game_state):
    state = copy.deepcopy(game_state)
    fields = state.get("board", {}).get("fields", [])
    buyable_fields = [field for field in fields if field.get("ist_kaufbar")]
    if not buyable_fields or any(not field.get("besitzer") for field in buyable_fields):
        return state

    owner_counts = {}
    for field in buyable_fields:
        owner_key = field.get("owner_player_id") or field.get("besitzer")
        owner_counts[owner_key] = owner_counts.get(owner_key, 0) + 1

    players = state.get("players", [])
    winner = max(
        players,
        key=lambda player: (
            owner_counts.get(player.get("id"), owner_counts.get(player.get("name"), 0)),
            -int(player.get("action_points", 0)),
            int(player.get("total_steps", 0)),
        ),
    )
    winner_count = owner_counts.get(winner.get("id"), owner_counts.get(winner.get("name"), 0))
    state.setdefault("game", {})["status"] = "finished"
    state["game"]["phase"] = "finished"
    return push_event(
        state,
        f"Gewinner: {winner['name']} gewinnt die Runde mit {winner_count} gesicherten Feldern.",
        event_type="winner",
        severity="success",
        player_id=winner["id"],
    )


def next_turn(game_state):
    state = copy.deepcopy(game_state)
    if state.get("game", {}).get("status") == "finished":
        return state

    players = state.get("players", [])
    if not players:
        raise ValueError("Das Spiel hat keine Spieler.")

    active_index = int(state.get("active_player_index", 0))
    next_active = (active_index + 1) % len(players)
    state["active_player_index"] = next_active
    state.setdefault("game", {})["turn_number"] = int(state["game"].get("turn_number", 1)) + 1

    if next_active == 0:
        state["game"]["round"] = int(state["game"].get("round", 1)) + 1
        return push_event(
            state,
            f"Runde {state['game']['round']} beginnt. {players[next_active]['name']} ist am Zug.",
            event_type="turn_change",
            severity="info",
            player_id=players[next_active]["id"],
        )

    return push_event(
        state,
        f"{players[next_active]['name']} ist als Naechstes am Zug.",
        event_type="turn_change",
        severity="info",
        player_id=players[next_active]["id"],
    )

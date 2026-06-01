from .game_engine import get_field_type


def get_popup_hint(field):
    if not field:
        return None

    field_type = get_field_type(field)
    if field["ist_kaufbar"] and not field.get("besitzer"):
        return f"Dieses Feld ist frei. Du kannst es jetzt fuer {field.get('kaufpreis') or '0'} sichern."
    if field.get("besitzer"):
        return f"Dieses Feld gehoert {field['besitzer']}. Die Abgabe von {field.get('miete') or '0'} wird jetzt faellig."
    if field_type == "gemeinschaft":
        return "Dieses Gemeinschaftsfeld loest ein zufaelliges Ereignis fuer dich oder die ganze Runde aus."
    if field_type == "steuer":
        return f"Dieses Feld verlangt eine feste Abgabe von {field.get('miete') or '0'}."
    if field_type == "gefangnis":
        return "Dieses Feld verhaengt eine Spielstrafe in Form von 2 zusaetzlichen Aktionspunkten."
    if field_type == "los":
        return "Auf Los darfst du 1 Aktionspunkt abziehen."
    if field_type == "spezial":
        return field.get("zusatz_regel") or "Dieses Spezialfeld hat einen eigenen Effekt."
    return field.get("zusatz_regel")


def get_active_player_name(game_state):
    players = game_state.get("players", [])
    if not players:
        return None
    active_index = game_state.get("active_player_index", 0) % len(players)
    return players[active_index]["name"]


def get_ownership_summary(fields):
    ownership = {}
    for field in fields:
        owner = field.get("besitzer")
        if owner:
            ownership.setdefault(owner, []).append(field)

    summary = []
    for owner, owner_fields in ownership.items():
        summary.append(
            {
                "owner": owner,
                "count": len(owner_fields),
                "fields": [field["name"] for field in owner_fields],
            }
        )

    summary.sort(key=lambda entry: (-entry["count"], entry["owner"].lower()))
    return summary


def get_scoreboard(game_state):
    fields = game_state["board"]["fields"]
    owner_counts = {}
    for field in fields:
        owner = field.get("besitzer")
        if owner:
            owner_counts[owner] = owner_counts.get(owner, 0) + 1

    active_index = game_state.get("active_player_index", 0)
    scoreboard = []
    for index, player in enumerate(game_state.get("players", [])):
        position_index = player.get("position", 0)
        current_field = fields[position_index]
        scoreboard.append(
            {
                "name": player["name"],
                "position": current_field["name"],
                "drinks": player.get("action_points", 0),
                "steps": player.get("total_steps", 0),
                "properties": owner_counts.get(player["name"], 0),
                "is_active": index == active_index,
                "status": player.get("status", "active"),
            }
        )
    return scoreboard


def get_game_highlights(game_state):
    fields = game_state["board"]["fields"]
    ownership = get_ownership_summary(fields)
    leader = ownership[0] if ownership else None
    free_fields = sum(1 for field in fields if field["ist_kaufbar"] and not field.get("besitzer"))

    return {
        "runde": game_state.get("game", {}).get("round", 1),
        "zugnummer": game_state.get("game", {}).get("turn_number", 1),
        "leaderName": leader["owner"] if leader else None,
        "leaderCount": leader["count"] if leader else 0,
        "freieFelder": free_fields,
    }


def get_current_player_index(game_state, current_player_id=None):
    if not current_player_id:
        return None
    for index, player in enumerate(game_state.get("players", [])):
        if player.get("id") == current_player_id:
            return index
    return None


def build_game_payload(game_state, current_player_id=None):
    fields = game_state["board"]["fields"]
    players = game_state.get("players", [])
    pending_action = game_state.get("pending_action")
    dice = game_state.get("dice", {})
    active_index = game_state.get("active_player_index", 0)
    current_player_index = get_current_player_index(game_state, current_player_id)
    lobby_mode = game_state.get("room", {}).get("mode") == "lobby"

    popup_field = None
    popup_player = None
    popup_roll = None
    popup_hint = None
    if pending_action:
        popup_field = fields[pending_action["field_index"]]
        popup_player = pending_action["player_index"]
        popup_roll = pending_action.get("roll")
        popup_hint = get_popup_hint(popup_field)

    display_roll = dice.get("current_roll") or popup_roll or dice.get("last_roll")

    return {
        "schemaVersion": game_state.get("schema_version"),
        "canonicalState": game_state,
        "appName": game_state.get("app_name", "Spassmonopoly Deluxe"),
        "spieler": [player["name"] for player in players],
        "aktiver": active_index,
        "currentPlayerIndex": current_player_index,
        "canAct": True if not lobby_mode else current_player_index == active_index,
        "activePlayerName": get_active_player_name(game_state),
        "felder": fields,
        "positionen": [player.get("position", 0) for player in players],
        "konto": [player.get("action_points", 0) for player in players],
        "gesamt": [player.get("total_steps", 0) for player in players],
        "wurf": dice.get("current_roll"),
        "displayRoll": display_roll,
        "popupWurf": popup_roll,
        "popupFeld": popup_field,
        "popupSpieler": popup_player,
        "popupHint": popup_hint,
        "scoreboard": get_scoreboard(game_state),
        "ownership": get_ownership_summary(fields),
        "highlights": get_game_highlights(game_state),
        "phase": game_state.get("game", {}).get("phase", "roll"),
        "gameStatus": game_state.get("game", {}).get("status", "running"),
        "lastEvent": game_state.get("last_event"),
        "eventLog": game_state.get("event_log", []),
    }


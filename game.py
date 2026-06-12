import copy
import json
import os
import logging
import random
import re
import string
import threading
import time
from secrets import token_hex
from threading import RLock
from uuid import uuid4

try:
    from dotenv import load_dotenv
except ImportError:
    pass
else:
    load_dotenv()

try:
    from flask import Flask, g, has_request_context, jsonify, redirect, render_template, request, session, url_for
except ImportError as exc:
    raise SystemExit(
        "Flask ist nicht installiert. Bitte führe `pip install -r requirements.txt` im Ordner "
        "`Spassmonopoly-Deluxe` aus."
    ) from exc

try:
    from flask_socketio import SocketIO, emit, join_room
except ImportError:
    SocketIO = None
    emit = None
    join_room = None

from engine.board_store import BoardStore
from engine.database import create_tables, init_db
from engine.game_engine import (
    apply_field_effect,
    clean_display_text,
    ensure_field_shape,
    ensure_state_defaults,
    init_game,
    move_player,
    normalize_event_log,
    push_event,
    roll_dice,
)
from engine.game_save_service import GameSaveService
from engine.state_io import (
    DEFAULT_ROOM_ID,
    delete_game_state as delete_saved_game_state,
    load_game_state as read_game_state,
    migrate_legacy_save,
    save_game_state as write_game_state,
)
from engine.view_state import build_game_payload


APP_NAME = "Spassmonopoly Deluxe"
ROOM_ID = os.getenv("GAME_ROOM_ID", DEFAULT_ROOM_ID)
MIN_LOBBY_PLAYERS = 2
MAX_LOBBY_PLAYERS = 8
JOIN_CODE_LENGTH = 6

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "spassmonopoly-deluxe-dev-key")
app.json.ensure_ascii = False
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
app.logger.setLevel(LOG_LEVEL)

if SocketIO is not None:
    # "threading" mode is the most reliable for a local game: it works with the
    # plain Werkzeug server without eventlet monkey-patching (which is fragile on
    # Windows and was leaving the client stuck on "connecting"). Socket.IO falls
    # back to HTTP long-polling, which is plenty fast for a lobby.
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
else:
    socketio = None

SOCKET_ROOM = f"game:{ROOM_ID}"

connected_clients: dict = {}

init_db(app)
create_tables(app)

board_store = BoardStore()
with app.app_context():
    if ROOM_ID == DEFAULT_ROOM_ID:
        migrate_legacy_save(ROOM_ID)

lobby_state = {
    "players": {},
    "game_started": False,
    "room_id": ROOM_ID,
}
state_lock = RLock()


def _emit(event, data, room=None, to=None):
    if socketio is None:
        return
    try:
        if to:
            socketio.emit(event, data, to=to)
        elif room:
            socketio.emit(event, data, room=room)
        else:
            socketio.emit(event, data)
    except Exception:
        pass


def structured_log(level, event, **fields):
    request_id = None
    if has_request_context():
        request_id = request.environ.get("spass.request_id") or getattr(g, "request_id", None)
        if not request_id:
            request_id = request.headers.get("X-Request-ID") or str(uuid4())
            g.request_id = request_id
            request.environ["spass.request_id"] = request_id
    payload = {
        "event": event,
        "request_id": request_id,
        "player_id": session.get("player_id") if has_request_context() else None,
        "host_id": lobby_state.get("host_id"),
        **{key: value for key, value in fields.items() if value is not None},
    }
    app.logger.log(level, json.dumps(payload, ensure_ascii=False, default=str))


@app.before_request
def attach_request_debug_context():
    g.request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.environ["spass.request_id"] = g.request_id
    g.request_started_at = time.perf_counter()
    if request.endpoint != "static":
        structured_log(
            logging.DEBUG,
            "request.start",
            method=request.method,
            path=request.path,
            endpoint=request.endpoint,
            save_id=(request.view_args or {}).get("save_id"),
        )


@app.after_request
def log_request_debug_context(response):
    response.headers["X-Request-ID"] = getattr(g, "request_id", "")
    if request.endpoint != "static":
        elapsed_ms = int((time.perf_counter() - getattr(g, "request_started_at", time.perf_counter())) * 1000)
        level = logging.WARNING if response.status_code >= 400 else logging.DEBUG
        structured_log(
            level,
            "request.finish",
            method=request.method,
            path=request.path,
            endpoint=request.endpoint,
            status=response.status_code,
            elapsed_ms=elapsed_ms,
            save_id=(request.view_args or {}).get("save_id"),
        )
    return response


@app.before_request
def check_csrf():
    if request.method == "POST" and not (request.path or "").startswith("/socket.io"):
        token = (
            request.headers.get("X-CSRF-Token")
            or (request.get_json(silent=True) or {}).get("_csrf")
            or request.form.get("_csrf")
        )
        expected = session.get("csrf_token")
        if expected and token != expected:
            return jsonify({"ok": False, "msg": "CSRF-Schutz: Ungültiger Token."}), 403


@app.context_processor
def inject_csrf():
    if "csrf_token" not in session:
        session["csrf_token"] = token_hex(32)
    return {"csrf_token": session["csrf_token"]}


def make_join_code():
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(JOIN_CODE_LENGTH))


def default_lobby_state(room_id=ROOM_ID, join_code=None, host_id=None):
    return {
        "players": {},
        "game_started": False,
        "room_id": room_id,
        "join_code": join_code or make_join_code(),
        "host_id": host_id,
    }


def ensure_game_identity(game_state, room_id=ROOM_ID, host_id=None, join_code=None):
    game_state = copy.deepcopy(game_state)
    players = game_state.get("players") or []
    room = game_state.setdefault("room", {"id": room_id, "mode": "local"})
    room.setdefault("id", room_id)
    identity = game_state.setdefault("identity", {})
    identity.setdefault("game_id", str(uuid4()))
    identity["join_code"] = identity.get("join_code") or join_code or room.get("join_code") or make_join_code()
    identity["host_id"] = identity.get("host_id") or host_id or room.get("host_id")
    if not identity.get("host_id") and players:
        identity["host_id"] = players[0].get("id")
    room["join_code"] = identity["join_code"]
    room["host_id"] = identity.get("host_id")
    return game_state


def is_canonical_game_state(raw_state):
    return (
        isinstance(raw_state, dict)
        and isinstance(raw_state.get("players"), list)
        and raw_state.get("players")
        and isinstance(raw_state["players"][0], dict)
        and isinstance(raw_state.get("board"), dict)
        and isinstance(raw_state["board"].get("fields"), list)
        and bool(raw_state["board"]["fields"])
    )


def infer_lobby_state(game_state, room_id=ROOM_ID):
    identity = game_state.get("identity") or {}
    saved_lobby = game_state.get("lobby")
    if isinstance(saved_lobby, dict):
        lobby = default_lobby_state(
            room_id,
            join_code=identity.get("join_code") or saved_lobby.get("join_code"),
            host_id=identity.get("host_id") or saved_lobby.get("host_id"),
        )
        lobby.update(copy.deepcopy(saved_lobby))
        lobby["room_id"] = room_id
        lobby["join_code"] = identity.get("join_code") or lobby.get("join_code") or make_join_code()
        lobby["host_id"] = identity.get("host_id") or lobby.get("host_id")
        lobby["game_started"] = bool(game_state.get("players"))
        return lobby

    players = {}
    for player in game_state.get("players", []):
        players[player["id"]] = {"name": clean_display_text(player["name"]), "ready": True}

    return {
        "players": players,
        "game_started": bool(players),
        "room_id": room_id,
        "join_code": identity.get("join_code") or make_join_code(),
        "host_id": identity.get("host_id") or next(iter(players), None),
    }


def normalize_legacy_server_save(snapshot, room_id=ROOM_ID):
    if not isinstance(snapshot, dict) or "game_state" not in snapshot:
        return None

    legacy_game = snapshot.get("game_state") or {}
    names = legacy_game.get("players") or []
    fields = legacy_game.get("board", {}).get("fields") or []
    if not names or not fields:
        return None

    player_ids = legacy_game.get("player_ids") or [f"player-{index + 1}" for index in range(len(names))]
    positions = legacy_game.get("positions") or [0 for _ in names]
    points = legacy_game.get("points") or [0 for _ in names]
    totals = legacy_game.get("totals") or [0 for _ in names]
    normalized_fields = ensure_field_shape(fields)

    players = []
    for index, name in enumerate(names):
        players.append(
            {
                "id": str(player_ids[index]) if index < len(player_ids) else f"player-{index + 1}",
                "name": clean_display_text(name),
                "position": int(positions[index]) if index < len(positions) else 0,
                "action_points": int(points[index]) if index < len(points) else 0,
                "total_steps": int(totals[index]) if index < len(totals) else 0,
                "status": "active",
            }
        )

    owner_ids = {player["name"]: player["id"] for player in players}
    for field in normalized_fields:
        if field.get("besitzer") and not field.get("owner_player_id"):
            field["owner_player_id"] = owner_ids.get(field["besitzer"])

    pending = legacy_game.get("pending_popup")
    waiting_for_roll = bool(legacy_game.get("waiting_for_roll", True))
    phase = "field_action" if pending else ("roll" if waiting_for_roll else "move")
    active_index = int(legacy_game.get("active_player", 0) or 0) % len(players)
    roll = legacy_game.get("roll")
    last_roll = legacy_game.get("letzter_wurf") or roll

    state = {
        "schema_version": 1,
        "app_name": APP_NAME,
        "game": {
            "status": "running",
            "phase": phase,
            "round": int(legacy_game.get("round", 1) or 1),
            "turn_number": int(legacy_game.get("turn", 1) or 1),
        },
        "players": players,
        "turn_order": list(range(len(players))),
        "active_player_index": active_index,
        "board": {"fields": normalized_fields},
        "dice": {
            "current_roll": roll if phase == "move" else None,
            "last_roll": last_roll,
            "history": [],
        },
        "pending_action": None,
        "last_event": legacy_game.get("last_event"),
        "event_log": normalize_event_log(legacy_game.get("event_log", [])),
        "room": {
            "id": room_id,
            "mode": "lobby" if snapshot.get("lobby_state") else "local",
        },
    }

    if pending:
        field_index = int(pending.get("field_index", 0) or 0)
        field_index = max(0, min(field_index, len(normalized_fields) - 1))
        state["pending_action"] = {
            "player_index": int(pending.get("spieler", active_index) or active_index),
            "player_id": players[int(pending.get("spieler", active_index) or active_index)]["id"],
            "field_index": field_index,
            "field_id": normalized_fields[field_index]["feld_id"],
            "roll": pending.get("wurf") or last_roll,
        }

    lobby = default_lobby_state(room_id)
    lobby.update(copy.deepcopy(snapshot.get("lobby_state") or {}))
    if not lobby["players"]:
        lobby = infer_lobby_state(state, room_id)
    lobby["game_started"] = True
    state["lobby"] = lobby
    state = ensure_game_identity(state, room_id, host_id=lobby.get("host_id"), join_code=lobby.get("join_code"))
    state["lobby"] = infer_lobby_state(state, room_id)
    return ensure_state_defaults(state)


def normalize_game_state(raw_state, room_id=ROOM_ID):
    if is_canonical_game_state(raw_state):
        state = copy.deepcopy(raw_state)
        state.setdefault("room", {"id": room_id, "mode": "local"})
        state["room"].setdefault("id", room_id)
        state["room"].setdefault("mode", "local")
        state.setdefault("lobby", infer_lobby_state(state, room_id))
        state = ensure_state_defaults(state)
        state = ensure_game_identity(state, room_id, host_id=state.get("lobby", {}).get("host_id"), join_code=state.get("lobby", {}).get("join_code"))
        state["board"]["fields"] = ensure_field_shape(state["board"]["fields"])
        if state["event_log"]:
            state["last_event_entry"] = state["event_log"][-1]
            state["last_event"] = state["event_log"][-1]["message"]
        for player in state.get("players", []):
            player["name"] = clean_display_text(player.get("name", "Spieler"))

        owner_ids = {player["name"]: player["id"] for player in state.get("players", [])}
        for field in state["board"]["fields"]:
            if field.get("besitzer") and not field.get("owner_player_id"):
                field["owner_player_id"] = owner_ids.get(field["besitzer"])
        return state

    return normalize_legacy_server_save(raw_state, room_id)


def is_playable_state(raw_state):
    return normalize_game_state(raw_state) is not None


def has_saved_game(room_id=ROOM_ID):
    return is_playable_state(read_game_state(room_id))


def load_game_state(room_id=ROOM_ID):
    state = normalize_game_state(read_game_state(room_id), room_id)
    if state is None:
        return None
    return state


def save_game_state(room_id=ROOM_ID, game_state=None):
    if game_state is None:
        game_state = room_id
        room_id = ROOM_ID
    game_state = copy.deepcopy(game_state)
    game_state.setdefault("room", {"id": room_id, "mode": "local"})
    game_state["room"].setdefault("id", room_id)
    game_state = ensure_game_identity(game_state, room_id, host_id=lobby_state.get("host_id"), join_code=lobby_state.get("join_code"))
    if game_state["room"].get("mode") == "lobby":
        lobby_state["host_id"] = get_host_id(game_state)
        lobby_state["join_code"] = game_state["identity"]["join_code"]
        game_state["lobby"] = copy.deepcopy(lobby_state)
    else:
        game_state.setdefault("lobby", copy.deepcopy(lobby_state))
    write_game_state(room_id, game_state)
    return game_state


def save_current_state_with_event(message, event_type="manual_save"):
    current_state = get_current_state()
    if current_state is None:
        raise ValueError("Kein aktiver Spielstand vorhanden.")
    next_state = push_event(current_state, message, event_type=event_type, severity="success")
    return persist_state(next_state)


def persist_error_event(game_state, message):
    if not game_state:
        return None
    try:
        next_state = push_event(game_state, message, event_type="error", severity="error")
        return persist_state(next_state)
    except Exception:
        app.logger.exception("Could not persist game error event")
        return game_state


def create_new_game(room_id=ROOM_ID, players=None, player_ids=None, mode="local"):
    player_names = [clean_display_text(player) for player in (players or ["Spieler 1", "Spieler 2"])]
    board_store.reset_owners()
    game_state = init_game(
        {
            "app_name": APP_NAME,
            "players": player_names,
            "fields": board_store.load_fields(),
            "room_id": room_id,
        }
    )
    if player_ids:
        for player, player_id in zip(game_state["players"], player_ids):
            player["id"] = str(player_id)

    host_id = str(player_ids[0]) if player_ids else game_state["players"][0]["id"]
    game_state["room"] = {"id": room_id, "mode": mode}
    game_state = ensure_game_identity(
        game_state,
        room_id,
        host_id=host_id,
        join_code=lobby_state.get("join_code"),
    )
    for player in game_state["players"]:
        game_state = push_event(
            game_state,
            f"{player['name']} ist dem Spiel beigetreten.",
            event_type="player_join",
            severity="success",
            player_id=player["id"],
        )
    if mode == "lobby":
        lobby_state["host_id"] = host_id
        lobby_state["join_code"] = game_state["identity"]["join_code"]
        lobby_state["game_started"] = True
        game_state["lobby"] = copy.deepcopy(lobby_state)
    return save_game_state(room_id, game_state)


def get_current_state():
    return load_game_state(ROOM_ID)


def persist_state(game_state):
    return save_game_state(ROOM_ID, game_state)


def get_current_player_index(game_state=None):
    game_state = game_state or get_current_state()
    player_id = session.get("player_id")
    if not player_id or not game_state:
        return None

    for index, player in enumerate(game_state.get("players", [])):
        if player.get("id") == player_id:
            return index
    return None


def session_player_is_known(game_state=None):
    game_state = game_state or get_current_state()
    return get_current_player_index(game_state) is not None


def get_host_id(game_state=None):
    game_state = game_state or get_current_state()
    if not game_state:
        return lobby_state.get("host_id") or next(iter(lobby_state.get("players", {})), None)

    identity = game_state.get("identity") or {}
    room = game_state.get("room") or {}
    lobby = game_state.get("lobby") or {}
    host_id = identity.get("host_id") or room.get("host_id") or lobby.get("host_id")
    if host_id:
        return host_id
    players = game_state.get("players") or []
    return players[0].get("id") if players else None


def state_player_ids(game_state):
    return {player.get("id") for player in game_state.get("players", [])}


def current_user_is_host(game_state=None):
    game_state = game_state or get_current_state()
    if not game_state:
        return False
    if game_state.get("room", {}).get("mode") != "lobby":
        return True
    return bool(session.get("player_id") and session.get("player_id") == get_host_id(game_state))


def require_host(game_state=None):
    game_state = game_state or get_current_state()
    if current_user_is_host(game_state):
        return None
    return json_error("Nur der Host darf diese Aktion ausfuehren.", 403)


def require_saved_game_host(game_state, allow_unbound=True):
    if game_state.get("room", {}).get("mode") != "lobby":
        return None
    player_id = session.get("player_id")
    if player_id == get_host_id(game_state):
        return None
    if allow_unbound and (not player_id or player_id not in state_player_ids(game_state)):
        return None
    return json_error("Nur der Host darf diese Aktion ausfuehren.", 403)


def game_requires_rejoin(game_state=None):
    game_state = game_state or get_current_state()
    return bool(game_state and game_state.get("room", {}).get("mode") == "lobby" and not session_player_is_known(game_state))


def ensure_session_id():
    if not session.get("session_id"):
        session["session_id"] = str(uuid4())
    return session["session_id"]


def bind_session_to_player(game_state, player_id):
    player = next((item for item in game_state.get("players", []) if item.get("id") == player_id), None)
    if not player:
        raise ValueError("Dieser Spieler gehört nicht zu diesem Spielstand.")
    session_id = ensure_session_id()
    session["player_id"] = player["id"]
    session["player_name"] = player["name"]
    session["room_id"] = game_state.get("room", {}).get("id", ROOM_ID)
    lobby_state["host_id"] = get_host_id(game_state)
    lobby_state["join_code"] = (game_state.get("identity") or {}).get("join_code") or lobby_state.get("join_code")
    lobby_state.setdefault("players", {}).setdefault(player["id"], {"name": player["name"], "ready": True})
    lobby_state["players"][player["id"]]["session_id"] = session_id
    return player


def require_active_player(game_state=None):
    game_state = game_state or get_current_state()
    if not game_state or game_state.get("room", {}).get("mode") != "lobby":
        return None

    current_index = get_current_player_index(game_state)
    active_index = int(game_state.get("active_player_index", 0))
    if current_index is None:
        return "Du bist diesem Spiel noch nicht als Spieler zugeordnet. Bitte tritt in der Lobby mit deinem Namen bei."
    if current_index != active_index:
        active_name = game_state["players"][active_index]["name"]
        return f"Bitte warten: {active_name} ist am Zug."
    return None


def redirect_if_game_missing():
    if not has_saved_game(ROOM_ID):
        return redirect(url_for("index"))
    return None


def json_error(message, status_code=400):
    structured_log(
        logging.WARNING if status_code < 500 else logging.ERROR,
        "response.error",
        status=status_code,
        message=message,
        endpoint=request.endpoint,
        save_id=(request.view_args or {}).get("save_id"),
    )
    return jsonify({"ok": False, "msg": message}), status_code


def parse_player_count(raw_value, default=4):
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        value = default
    return max(2, min(8, value))


def clean_save_name(raw_value, fallback=None):
    name = clean_display_text(str(raw_value or "").strip())
    name = " ".join(name.split())
    if not name and fallback:
        name = fallback
    if not name:
        raise ValueError("Bitte gib einen Namen für den Spielstand ein.")
    if len(name) < 2:
        raise ValueError("Der Name muss mindestens 2 Zeichen lang sein.")
    if len(name) > 64:
        raise ValueError("Der Name darf maximal 64 Zeichen lang sein.")
    if not re.fullmatch(r"[\wÄÖÜäöüß ._()'!-]+", name, flags=re.UNICODE):
        raise ValueError("Der Name enthält ungültige Zeichen.")
    return name


def clean_lobby_name(raw_value):
    name = clean_display_text(str(raw_value or "").strip())
    name = " ".join(name.split())
    if len(name) < 2:
        raise ValueError("Der Name muss mindestens 2 Zeichen lang sein.")
    if len(name) > 24:
        raise ValueError("Der Name darf maximal 24 Zeichen lang sein.")
    return name


def render_board():
    with app.app_context():
        game_state = get_current_state()
        return render_template(
            "board.html",
            game_state=build_game_payload(game_state, current_player_id=session.get("player_id")),
            settings=GameSaveService.get_global_settings(),
        )


def _build_lobby_payload():
    with state_lock:
        players_snap = dict(lobby_state.get("players", {}))
        host_id = lobby_state.get("host_id")
        join_code = lobby_state.get("join_code")
        game_started = bool(lobby_state.get("game_started"))
    players = [
        {
            "id": pid,
            "name": p["name"],
            "ready": bool(p.get("ready")),
            "host": pid == host_id,
            "order": idx + 1,
        }
        for idx, (pid, p) in enumerate(players_snap.items())
    ]
    all_ready = bool(players) and all(p["ready"] for p in players)
    with app.app_context():
        saved = has_saved_game(ROOM_ID)
    return {
        "players": players,
        "all_ready": all_ready,
        "game_started": game_started,
        "has_saved_game": saved,
        "host_id": host_id,
        "join_code": join_code,
        "min_players": MIN_LOBBY_PLAYERS,
        "max_players": MAX_LOBBY_PLAYERS,
    }


def broadcast_game_state(game_state):
    if socketio is None:
        return
    try:
        payload = build_game_payload(game_state, current_player_id=None)
        _emit("game_state_update", {"state": payload}, room=SOCKET_ROOM)
    except Exception:
        pass


# Players are not removed the instant a socket drops, because a normal page
# refresh briefly disconnects and reconnects. Removal only happens after the
# player has had no live socket for this many seconds (grace window).
_LOBBY_PRESENCE_GRACE = 12
_player_absent_since: dict[str, float] = {}
# Players are only auto-removed if their realtime socket was confirmed at least
# once. If sockets never work for a player, we never cull them — a broken socket
# must never make a player vanish from the lobby.
_seen_on_socket: set[str] = set()


def _active_player_ids():
    return {
        c.get("player_id")
        for c in list(connected_clients.values())
        if c.get("player_id")
    }


def _reap_presence():
    """Remove players who have been offline beyond the grace window.

    During the lobby: drop the player, migrate host if needed.
    During an active game: only the host going dark closes the game (autosave),
    other players stay in the game state so they can rejoin.
    """
    now = time.time()
    lobby_dirty = False
    host_migrated_to = None
    close_reason = None

    with state_lock:
        active = _active_player_ids()
        players = lobby_state.get("players", {})
        game_started = bool(lobby_state.get("game_started"))

        for pid in list(players.keys()):
            if pid in active:
                _player_absent_since.pop(pid, None)
                continue
            if pid not in _seen_on_socket:
                # Their socket never connected — sockets may be broken for them.
                # Never cull such a player; only "Lobby zurücksetzen" clears them.
                continue
            since = _player_absent_since.setdefault(pid, now)
            if now - since < _LOBBY_PRESENCE_GRACE:
                continue
            _player_absent_since.pop(pid, None)
            is_host = (pid == lobby_state.get("host_id"))
            if not game_started:
                players.pop(pid, None)
                lobby_dirty = True
                if is_host:
                    remaining = list(players.keys())
                    lobby_state["host_id"] = remaining[0] if remaining else None
                    if remaining:
                        host_migrated_to = remaining[0]
            elif is_host:
                close_reason = "Host hat die Verbindung getrennt. Das Spiel wurde gespeichert."

        # Forget absence timers for players no longer tracked.
        for pid in list(_player_absent_since.keys()):
            if pid not in players:
                _player_absent_since.pop(pid, None)

    if close_reason:
        try:
            with app.app_context():
                save_current_state_with_event(close_reason)
        except Exception:
            pass
        _emit("lobby_closed", {"reason": close_reason}, room=SOCKET_ROOM)
        return
    if host_migrated_to:
        _emit("host_migrated", {"new_host_id": host_migrated_to}, room=SOCKET_ROOM)
    if lobby_dirty or host_migrated_to:
        _emit("lobby_update", _build_lobby_payload(), room=SOCKET_ROOM)


def _presence_reaper():
    while True:
        time.sleep(4)
        try:
            _reap_presence()
        except Exception:
            pass


threading.Thread(target=_presence_reaper, daemon=True).start()


def rejoin_redirect_for_state(game_state):
    return url_for("rejoin_page") if game_requires_rejoin(game_state) else url_for("spiel")


if socketio is not None:
    @socketio.on("connect")
    def handle_ws_connect():
        sid = request.sid
        player_id = session.get("player_id")
        player_name = session.get("player_name")
        connected_clients[sid] = {
            "player_id": player_id,
            "connected_at": time.time(),
            "last_ping": time.time(),
        }
        join_room(SOCKET_ROOM)
        if player_id:
            _seen_on_socket.add(player_id)
        # Resilience: if this session belongs to a known lobby player who was
        # dropped by a transient disconnect (e.g. a page refresh), re-add them
        # so a reload never kicks a player out of the lobby.
        with state_lock:
            game_started = bool(lobby_state.get("game_started"))
            players = lobby_state.get("players", {})
            if player_id and player_name and not game_started and player_id not in players:
                players[player_id] = {
                    "name": player_name,
                    "ready": False,
                    "session_id": session.get("session_id"),
                }
                if not lobby_state.get("host_id"):
                    lobby_state["host_id"] = player_id
                _emit("lobby_update", _build_lobby_payload(), room=SOCKET_ROOM)
        emit("lobby_update", _build_lobby_payload())

    @socketio.on("disconnect")
    def handle_ws_disconnect():
        # Only drop the socket. The presence reaper decides whether the player
        # is actually gone (after a grace window), so a refresh never kicks them.
        connected_clients.pop(request.sid, None)

    @socketio.on("ping")
    def handle_ws_ping():
        sid = request.sid
        if sid in connected_clients:
            connected_clients[sid]["last_ping"] = time.time()
        emit("pong")

    @socketio.on("client_identify")
    def handle_ws_identify(data):
        sid = request.sid
        player_id = data.get("player_id") or session.get("player_id")
        if sid in connected_clients and player_id:
            connected_clients[sid]["player_id"] = player_id
            _seen_on_socket.add(player_id)


@app.route("/api/music/playlist", methods=["GET"])
def api_music_playlist():
    music_dir = os.path.join(app.static_folder, "music")
    if not os.path.isdir(music_dir):
        return jsonify({"ok": True, "tracks": []})
    tracks = [
        f"/static/music/{filename}"
        for filename in sorted(os.listdir(music_dir))
        if filename.lower().endswith((".mp3", ".ogg", ".wav", ".m4a"))
    ]
    return jsonify({"ok": True, "tracks": tracks})


@app.route("/api/saves", methods=["GET"])
def api_list_saves():
    """List all saved games."""
    try:
        with app.app_context():
            saves = GameSaveService.list_saves()
            return jsonify({
                "ok": True,
                "saves": [save.to_dict() for save in saves],
            })
    except Exception as e:
        app.logger.exception("Save list API failed")
        return json_error(f"Spielstände konnten nicht geladen werden: {str(e)}", 500)


@app.route("/api/save/<save_id>", methods=["GET"])
def api_get_save(save_id):
    """Get details of a specific save."""
    try:
        with app.app_context():
            game_save = GameSaveService.load_save(save_id)
            if not game_save:
                return json_error("Spielstand nicht gefunden", 404)
            return jsonify({
                "ok": True,
                "save": game_save.to_dict(),
            })
    except Exception as e:
        app.logger.exception("Save detail API failed")
        return json_error(f"Spielstand konnte nicht geladen werden: {str(e)}", 500)


@app.route("/api/save/<save_id>/load", methods=["POST"])
def api_load_save(save_id):
    """Load a saved game."""
    try:
        with app.app_context():
            game_save = GameSaveService.load_save(save_id)
            if not game_save:
                return json_error("Spielstand nicht gefunden", 404)

            game_state = game_save.get_game_state()
            normalized = normalize_game_state(game_state, ROOM_ID)
            if normalized is None:
                return json_error("Spielstand ist nicht spielbar", 422)
            host_error = require_saved_game_host(normalized)
            if host_error:
                return host_error
            lobby_state.clear()
            lobby_state.update(infer_lobby_state(normalized, ROOM_ID))
            if normalized.get("room", {}).get("mode") == "lobby":
                bind_session_to_player(normalized, get_host_id(normalized))
            save_game_state(ROOM_ID, normalized)
            structured_log(
                logging.INFO,
                "save.load",
                save_id=save_id,
                save_name=game_save.name,
                game_id=(normalized.get("identity") or {}).get("game_id"),
                join_code=(normalized.get("identity") or {}).get("join_code"),
                phase=(normalized.get("game") or {}).get("phase"),
            )
            return jsonify({
                "ok": True,
                "message": f"'{game_save.name}' geladen",
                "save_id": save_id,
                "redirect_url": rejoin_redirect_for_state(normalized),
            })
    except Exception as e:
        app.logger.exception("Save load API failed")
        return json_error(f"Spielstand konnte nicht geladen werden: {str(e)}", 500)


@app.route("/api/save-current", methods=["POST"])
def api_save_current():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return json_error("Das Spiel wurde noch nicht gestartet.", 404)

    with state_lock, app.app_context():
        try:
            host_error = require_host(get_current_state())
            if host_error:
                return host_error
            payload = request.get_json(silent=True) or {}
            requested_name = payload.get("name")
            save_name = clean_save_name(requested_name) if requested_name else None
            game_state = save_current_state_with_event("Spielstand manuell gespeichert.")
            broadcast_game_state(game_state)
            named_save = None
            if save_name:
                existing = GameSaveService.load_save_by_name(save_name)
                if existing:
                    named_save = GameSaveService.update_save(existing.id, game_state)
                else:
                    named_save = GameSaveService.create_save(save_name, game_state, description="Manueller Spielstand")
            structured_log(
                logging.INFO,
                "save.current",
                save_id=named_save.id if named_save else None,
                save_name=save_name,
                phase=(game_state.get("game") or {}).get("phase"),
                active_player_index=game_state.get("active_player_index"),
            )
            return jsonify(
                {
                    "ok": True,
                    "message": f"Als '{save_name}' gespeichert." if save_name else "Spielstand gespeichert.",
                    "save": named_save.to_dict() if named_save else None,
                    "state": build_game_payload(game_state, current_player_id=session.get("player_id")),
                }
            )
        except ValueError as exc:
            return json_error(str(exc), 400)
        except Exception as exc:
            app.logger.exception("Manual save failed")
            return json_error(f"Spielstand konnte nicht gespeichert werden: {str(exc)}", 500)


@app.route("/api/exit-game", methods=["POST"])
def api_exit_game():
    payload = request.get_json(silent=True) or {}
    mode = payload.get("mode")
    if mode not in {"save", "discard"}:
        return json_error("Ungültige Beenden-Aktion.", 400)

    with state_lock, app.app_context():
        try:
            host_error = require_host(get_current_state())
            if host_error:
                return host_error
            if mode == "save" and has_saved_game(ROOM_ID):
                save_current_state_with_event("Spiel gespeichert und beendet.", event_type="game_exit")
            session.clear()
            lobby_state.clear()
            lobby_state.update(default_lobby_state(ROOM_ID))
            return jsonify({"ok": True, "redirect_url": url_for("index")})
        except Exception as exc:
            app.logger.exception("Exit game failed")
            return json_error(f"Spiel konnte nicht beendet werden: {str(exc)}", 500)


@app.route("/api/save/<save_id>/rename", methods=["POST"])
def api_rename_save(save_id):
    """Rename a saved game."""
    try:
        data = request.get_json(silent=True) or {}
        new_name = clean_save_name(data.get("name", ""))

        with app.app_context():
            source_save = GameSaveService.load_save(save_id)
            if not source_save:
                return json_error("Spielstand nicht gefunden", 404)
            normalized = normalize_game_state(source_save.get_game_state(), ROOM_ID)
            if normalized is None:
                return json_error("Spielstand ist nicht spielbar", 422)
            host_error = require_saved_game_host(normalized)
            if host_error:
                return host_error
            game_save = GameSaveService.rename_save(save_id, new_name)
            if not game_save:
                return json_error("Spielstand nicht gefunden", 404)

            structured_log(logging.INFO, "save.rename", save_id=save_id, save_name=new_name)
            return jsonify({
                "ok": True,
                "message": f"In '{new_name}' umbenannt",
                "save": game_save.to_dict(),
            })
    except ValueError as e:
        return json_error(str(e), 400)
    except Exception as e:
        app.logger.exception("Save rename API failed")
        return json_error(f"Spielstand konnte nicht umbenannt werden: {str(e)}", 500)


@app.route("/api/save/<save_id>/delete", methods=["POST"])
def api_delete_save(save_id):
    """Delete a saved game."""
    try:
        with app.app_context():
            source_save = GameSaveService.load_save(save_id)
            if not source_save:
                return json_error("Spielstand nicht gefunden", 404)
            normalized = normalize_game_state(source_save.get_game_state(), ROOM_ID)
            if normalized is None:
                return json_error("Spielstand ist nicht spielbar", 422)
            host_error = require_saved_game_host(normalized)
            if host_error:
                return host_error
            success = GameSaveService.delete_save(save_id)
            if not success:
                return json_error("Spielstand nicht gefunden", 404)

            structured_log(logging.INFO, "save.delete", save_id=save_id, save_name=source_save.name)
            return jsonify({
                "ok": True,
                "message": "Spielstand gelöscht",
            })
    except Exception as e:
        app.logger.exception("Save delete API failed")
        return json_error(f"Spielstand konnte nicht gelöscht werden: {str(e)}", 500)


@app.route("/api/save/<save_id>/duplicate", methods=["POST"])
def api_duplicate_save(save_id):
    """Duplicate a saved game."""
    try:
        data = request.get_json(silent=True) or {}

        with app.app_context():
            source_save = GameSaveService.load_save(save_id)
            if not source_save:
                return json_error("Spielstand nicht gefunden", 404)
            normalized = normalize_game_state(source_save.get_game_state(), ROOM_ID)
            if normalized is None:
                return json_error("Spielstand ist nicht spielbar", 422)
            host_error = require_saved_game_host(normalized)
            if host_error:
                return host_error
            new_name = clean_save_name(data.get("name"), fallback=f"Kopie von {source_save.name}")
            game_save = GameSaveService.duplicate_save(save_id, new_name)
            if not game_save:
                return json_error("Spielstand nicht gefunden", 404)

            structured_log(
                logging.INFO,
                "save.duplicate",
                save_id=save_id,
                new_save_id=game_save.id,
                save_name=new_name,
            )
            return jsonify({
                "ok": True,
                "message": f"Nach '{new_name}' dupliziert",
                "save": game_save.to_dict(),
            })
    except ValueError as e:
        return json_error(str(e), 400)
    except Exception as e:
        app.logger.exception("Save duplicate API failed")
        return json_error(f"Spielstand konnte nicht dupliziert werden: {str(e)}", 500)


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    try:
        with app.app_context():
            if request.method == "GET":
                return jsonify({"ok": True, "settings": GameSaveService.get_global_settings()})

            payload = request.get_json(silent=True) or {}
            settings = GameSaveService.update_global_settings(payload)
            _emit("settings_update", {"settings": settings}, room=SOCKET_ROOM)
            return jsonify({"ok": True, "message": "Einstellungen gespeichert.", "settings": settings})
    except ValueError as e:
        return json_error(str(e), 400)
    except Exception as e:
        app.logger.exception("Settings API failed")
        return json_error(f"Einstellungen konnten nicht gespeichert werden: {str(e)}", 500)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        with state_lock:
            current_state = get_current_state()
            if current_state and current_state.get("room", {}).get("mode") == "lobby" and not current_user_is_host(current_state):
                return "Nur der Host darf eine neue Runde starten.", 403
            delete_saved_game_state(ROOM_ID)
            player_count = parse_player_count(request.form.get("anzahl"))
            session.clear()
            lobby_state.clear()
            lobby_state.update(default_lobby_state(ROOM_ID))
            session["anzahl"] = player_count
        return redirect(url_for("namen"))

    with app.app_context():
        saves = [save.to_dict() for save in GameSaveService.list_saves()]
        settings = GameSaveService.get_global_settings()
        return render_template("index.html", has_saved_game=has_saved_game(ROOM_ID), saves=saves, settings=settings)


@app.route("/continue", methods=["POST"])
def continue_game():
    if not has_saved_game(ROOM_ID):
        return redirect(url_for("index"))
    with state_lock, app.app_context():
        game_state = load_game_state(ROOM_ID)
    return redirect(rejoin_redirect_for_state(game_state))


@app.route("/rejoin", methods=["GET", "POST"])
def rejoin_page():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return missing_game

    with state_lock, app.app_context():
        game_state = get_current_state()
        if game_state is None:
            return redirect(url_for("index"))
        if request.method == "POST":
            try:
                bind_session_to_player(game_state, request.form.get("player_id", ""))
            except ValueError as exc:
                return render_template("rejoin.html", game_state=game_state, error=str(exc)), 400
            return redirect(url_for("spiel"))
        if not game_requires_rejoin(game_state):
            return redirect(url_for("spiel"))
        return render_template("rejoin.html", game_state=game_state, error=None)


@app.route("/lobby", methods=["GET"])
def lobby_page():
    with app.app_context():
        load_game_state(ROOM_ID)
        return render_template(
            "lobby.html",
            has_saved_game=has_saved_game(ROOM_ID),
            current_player_id=session.get("player_id"),
            join_code=lobby_state.get("join_code"),
            min_players=MIN_LOBBY_PLAYERS,
            max_players=MAX_LOBBY_PLAYERS,
            settings=GameSaveService.get_global_settings(),
        )


@app.route("/lobby/join", methods=["POST"])
def lobby_join():
    with state_lock:
        try:
            name = clean_lobby_name(request.form.get("name", ""))
        except ValueError as exc:
            return json_error(str(exc))
        requested_code = str(request.form.get("join_code", "") or "").strip().upper()

        current_game = get_current_state()
        if current_game and requested_code:
            expected_code = (current_game.get("identity") or {}).get("join_code")
            if expected_code and requested_code != expected_code:
                return json_error("Join Code passt nicht zu diesem Spiel.", 404)
        existing_player = None
        if current_game:
            for player in current_game.get("players", []):
                if player["name"].strip().lower() == name.lower():
                    existing_player = player
                    break

        if lobby_state.get("game_started") and current_game:
            if existing_player is None:
                return json_error("Dieses Spiel läuft bereits. Bitte mit einem vorhandenen Spielernamen verbinden.", 409)
            session_id = ensure_session_id()
            session["player_id"] = existing_player["id"]
            session["player_name"] = existing_player["name"]
            session["room_id"] = ROOM_ID
            lobby_state.setdefault("players", {}).setdefault(existing_player["id"], {"name": existing_player["name"], "ready": True})
            lobby_state["players"][existing_player["id"]]["session_id"] = session_id
            return jsonify({"ok": True, "player_id": existing_player["id"], "game_started": True})

        current_session_player = session.get("player_id")
        matching_player_id = next(
            (
                player_id
                for player_id, player in lobby_state.get("players", {}).items()
                if player["name"].strip().lower() == name.lower()
            ),
            None,
        )
        if matching_player_id and matching_player_id != current_session_player:
            return json_error("Dieser Name ist bereits vergeben.", 409)
        if len(lobby_state.get("players", {})) >= MAX_LOBBY_PLAYERS and not current_session_player:
            return json_error("Die Lobby ist voll.", 409)

        player_id = matching_player_id or current_session_player or str(uuid4())
        session_id = ensure_session_id()

        lobby_state.setdefault("players", {})[player_id] = {
            "name": name,
            "ready": bool(lobby_state.get("players", {}).get(player_id, {}).get("ready", False)),
            "session_id": session_id,
        }
        lobby_state["room_id"] = ROOM_ID
        if not lobby_state.get("host_id"):
            lobby_state["host_id"] = player_id
        lobby_state.setdefault("join_code", make_join_code())
        lobby_state["game_started"] = False
        session["player_id"] = player_id
        session["player_name"] = name
        session["room_id"] = ROOM_ID

        _emit("lobby_update", _build_lobby_payload(), room=SOCKET_ROOM)
        return jsonify({"ok": True, "player_id": player_id, "game_started": False})


@app.route("/lobby/ready", methods=["POST"])
def lobby_ready():
    with state_lock:
        player_id = session.get("player_id")
        if not player_id or player_id not in lobby_state.get("players", {}):
            return json_error("Nicht in der Lobby")

        lobby_state["players"][player_id]["ready"] = not lobby_state["players"][player_id].get("ready", False)
    _emit("lobby_update", _build_lobby_payload(), room=SOCKET_ROOM)
    return jsonify({"ok": True})


@app.route("/lobby/state", methods=["GET"])
def lobby_state_api():
    payload = _build_lobby_payload()
    payload["redirect_url"] = url_for("spiel")
    payload["ok"] = True
    return jsonify(payload)


@app.route("/lobby/start", methods=["POST"])
def lobby_start():
    with state_lock:
        if lobby_state.get("game_started") and has_saved_game(ROOM_ID):
            return jsonify({"ok": True, "redirect_url": url_for("spiel")})

        players = list(lobby_state.get("players", {}).items())
        host_id = lobby_state.get("host_id") or (players[0][0] if players else None)
        if not session.get("player_id") or session.get("player_id") != host_id:
            return json_error("Nur der Host kann die Runde starten.", 403)
        if len(players) < MIN_LOBBY_PLAYERS:
            return json_error("Mindestens 2 Spieler erforderlich")
        if not all(player.get("ready") for _, player in players):
            return json_error("Nicht alle Spieler sind bereit")

        names = [player["name"] for _, player in players]
        player_ids = [player_id for player_id, _ in players]
        with app.app_context():
            create_new_game(ROOM_ID, names, player_ids=player_ids, mode="lobby")
    _emit("game_started", {"redirect_url": url_for("spiel")}, room=SOCKET_ROOM)
    return jsonify({"ok": True, "redirect_url": url_for("spiel")})


@app.route("/lobby/continue", methods=["POST"])
def lobby_continue():
    with state_lock, app.app_context():
        game_state = load_game_state(ROOM_ID)
        if game_state is None:
            return redirect(url_for("lobby_page"))
        if lobby_state.get("players") and not current_user_is_host(game_state):
            return "Nur der Host darf einen Spielstand laden.", 403

        lobby_state["game_started"] = True
        lobby_state["host_id"] = get_host_id(game_state)
        lobby_state["join_code"] = (game_state.get("identity") or {}).get("join_code") or lobby_state.get("join_code")
        game_state["room"]["mode"] = "lobby"
        game_state["lobby"] = copy.deepcopy(lobby_state)
        save_game_state(ROOM_ID, game_state)
        if get_current_player_index(game_state) is None:
            return redirect(url_for("lobby_page"))
        return redirect(url_for("spiel"))


@app.route("/lobby/new", methods=["POST"])
def lobby_new():
    with state_lock:
        current_state = get_current_state()
        active_lobby_game = bool(current_state and current_state.get("room", {}).get("mode") == "lobby") or bool(lobby_state.get("game_started"))
        if active_lobby_game and lobby_state.get("players") and not current_user_is_host(current_state):
            return "Nur der Host darf die Lobby zuruecksetzen.", 403
        session.clear()
        lobby_state.clear()
        lobby_state.update(default_lobby_state(ROOM_ID))
        board_store.reset_owners()
        with app.app_context():
            delete_saved_game_state(ROOM_ID)
    return redirect(url_for("lobby_page"))


@app.route("/namen", methods=["GET", "POST"])
def namen():
    if "anzahl" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        players = []
        for index in range(1, session["anzahl"] + 1):
            raw_name = request.form.get(f"spieler{index}", "").strip()
            players.append(clean_display_text(raw_name or f"Spieler {index}"))

        with state_lock, app.app_context():
            create_new_game(ROOM_ID, players)
        return redirect(url_for("spiel"))

    return render_template("spielernamen.html", anzahl=session["anzahl"])


@app.route("/board", methods=["GET"])
def spiel():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return missing_game

    with app.app_context():
        if game_requires_rejoin(get_current_state()):
            return redirect(url_for("rejoin_page"))
        return render_board()


@app.route("/api/state", methods=["GET"])
def api_state():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return json_error("Das Spiel wurde noch nicht gestartet.", 404)

    with app.app_context():
        return jsonify({"ok": True, "state": build_game_payload(get_current_state(), current_player_id=session.get("player_id"))})


@app.route("/zug_wuerfeln", methods=["POST"])
def zug_wuerfeln():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return json_error("Das Spiel wurde noch nicht gestartet.")

    with state_lock, app.app_context():
        try:
            current_state = get_current_state()
            active_error = require_active_player(current_state)
            if active_error:
                return jsonify(
                    {
                        "ok": False,
                        "msg": active_error,
                        "state": build_game_payload(current_state, current_player_id=session.get("player_id")),
                    }
                ), 403
            game_state = persist_state(roll_dice(current_state))
            broadcast_game_state(game_state)
        except ValueError as exc:
            current_state = persist_error_event(get_current_state(), str(exc))
            return jsonify(
                {
                    "ok": False,
                    "msg": str(exc),
                    "state": build_game_payload(current_state, current_player_id=session.get("player_id")) if current_state else None,
                }
            ), 400

        return jsonify({"ok": True, "state": build_game_payload(game_state, current_player_id=session.get("player_id"))})


@app.route("/zug_ziehen", methods=["POST"])
def zug_ziehen():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return json_error("Das Spiel wurde noch nicht gestartet.")

    with state_lock, app.app_context():
        try:
            current_state = get_current_state()
            active_error = require_active_player(current_state)
            if active_error:
                return jsonify(
                    {
                        "ok": False,
                        "msg": active_error,
                        "state": build_game_payload(current_state, current_player_id=session.get("player_id")),
                    }
                ), 403
            game_state = persist_state(move_player(current_state))
            broadcast_game_state(game_state)
        except ValueError as exc:
            current_state = persist_error_event(get_current_state(), str(exc))
            return jsonify(
                {
                    "ok": False,
                    "msg": str(exc),
                    "state": build_game_payload(current_state, current_player_id=session.get("player_id")) if current_state else None,
                }
            ), 400

        return jsonify({"ok": True, "state": build_game_payload(game_state, current_player_id=session.get("player_id"))})


@app.route("/feld_aktion", methods=["POST"])
def feld_aktion():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return json_error("Das Spiel wurde noch nicht gestartet.")

    payload = request.get_json(silent=True) or {}

    with state_lock, app.app_context():
        try:
            current_state = get_current_state()
            active_error = require_active_player(current_state)
            if active_error:
                return jsonify(
                    {
                        "ok": False,
                        "msg": active_error,
                        "state": build_game_payload(current_state, current_player_id=session.get("player_id")),
                    }
                ), 403
            game_state = persist_state(
                apply_field_effect(
                    current_state,
                    action=payload.get("aktion", "skip"),
                    field_id=payload.get("feld"),
                )
            )
            broadcast_game_state(game_state)
        except ValueError as exc:
            current_state = persist_error_event(get_current_state(), str(exc))
            return jsonify(
                {
                    "ok": False,
                    "msg": str(exc),
                    "state": build_game_payload(current_state, current_player_id=session.get("player_id")) if current_state else None,
                }
            ), 400

        return jsonify({"ok": True, "state": build_game_payload(game_state, current_player_id=session.get("player_id"))})


@app.route("/neues_spiel", methods=["POST"])
def neues_spiel():
    with state_lock:
        previous_state = get_current_state()
        if previous_state and previous_state.get("room", {}).get("mode") == "lobby" and not current_user_is_host(previous_state):
            return "Nur der Host darf eine neue Runde starten.", 403
        return_to_lobby = (
            bool(session.get("player_id"))
            or (previous_state or {}).get("room", {}).get("mode") == "lobby"
        )
        session.clear()
        lobby_state.clear()
        lobby_state.update(default_lobby_state(ROOM_ID))
        board_store.reset_owners()
        with app.app_context():
            delete_saved_game_state(ROOM_ID)
    return redirect(url_for("lobby_page" if return_to_lobby else "index"))


with app.app_context():
    try:
        _initial_state = load_game_state(ROOM_ID)
        if _initial_state:
            lobby_state.update(infer_lobby_state(_initial_state, ROOM_ID))
        else:
            lobby_state.update(default_lobby_state(ROOM_ID))
    except Exception:
        lobby_state.update(default_lobby_state(ROOM_ID))

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes", "on"}
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    if socketio is not None:
        socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
    else:
        app.run(host=host, port=port, debug=debug)

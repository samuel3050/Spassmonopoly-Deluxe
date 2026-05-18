import json
from json import JSONDecodeError
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
SAVE_DIR = BASE_DIR / "saves"
DEFAULT_ROOM_ID = "room_default"
LEGACY_STATE_FILE = BASE_DIR / "data" / "current_game_state.json"


def _safe_room_id(room_id):
    safe = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in str(room_id or DEFAULT_ROOM_ID))
    return safe or DEFAULT_ROOM_ID


def get_save_path(room_id=DEFAULT_ROOM_ID):
    value = Path(str(room_id))
    if value.suffix == ".json" or value.parent != Path("."):
        return value
    return SAVE_DIR / f"{_safe_room_id(room_id)}.json"


def has_save_game(room_id=DEFAULT_ROOM_ID):
    path = get_save_path(room_id)
    return path.exists() and path.is_file() and path.stat().st_size > 0


def load_game_state(room_id=DEFAULT_ROOM_ID):
    path = get_save_path(room_id)
    if not path.exists() or path.stat().st_size == 0:
        return None

    try:
        with path.open("r", encoding="utf-8") as handle:
            state = json.load(handle)
    except (OSError, JSONDecodeError, TypeError, ValueError):
        return None

    return state if isinstance(state, dict) else None


def save_game_state(room_id=DEFAULT_ROOM_ID, game_state=None):
    if game_state is None:
        game_state = room_id
        room_id = DEFAULT_ROOM_ID

    path = get_save_path(room_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")

    payload = json.loads(json.dumps(game_state, ensure_ascii=False))
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    temp_path.replace(path)
    return game_state


def delete_game_state(room_id=DEFAULT_ROOM_ID):
    path = get_save_path(room_id)
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    return path


def list_saved_rooms():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    rooms = []
    for path in SAVE_DIR.glob("*.json"):
        if path.is_file() and path.stat().st_size > 0:
            rooms.append(path.stem)
    if LEGACY_STATE_FILE.exists() and LEGACY_STATE_FILE.stat().st_size > 0:
        rooms.append(DEFAULT_ROOM_ID)
    return sorted(set(rooms))


def migrate_legacy_save(room_id=DEFAULT_ROOM_ID):
    if has_save_game(room_id) or not LEGACY_STATE_FILE.exists():
        return None

    state = load_game_state(LEGACY_STATE_FILE)
    if state is None:
        return None

    return save_game_state(room_id, state)


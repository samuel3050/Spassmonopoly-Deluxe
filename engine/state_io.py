import json
import os
from json import JSONDecodeError
from pathlib import Path

from .game_save_service import GameSaveService

BASE_DIR = Path(__file__).resolve().parents[1]
SAVE_DIR = BASE_DIR / "saves"
DEFAULT_ROOM_ID = "room_default"
LEGACY_STATE_FILE = BASE_DIR / "data" / "current_game_state.json"


def _safe_room_id(room_id):
    """Sanitize room ID for use in file names."""
    safe = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in str(room_id or DEFAULT_ROOM_ID))
    return safe or DEFAULT_ROOM_ID


def has_save_game(room_id=DEFAULT_ROOM_ID):
    """Check if a game save exists for the given room."""
    try:
        game_save = GameSaveService.load_save_by_name(room_id)
        return game_save is not None
    except Exception:
        return False


def load_game_state(room_id=DEFAULT_ROOM_ID):
    """Load game state from database.

    Args:
        room_id: Room/save ID to load

    Returns:
        Game state dictionary or None if not found
    """
    try:
        game_save = GameSaveService.load_save_by_name(room_id)
        return game_save.get_game_state() if game_save else None
    except Exception:
        return None


def save_game_state(room_id=DEFAULT_ROOM_ID, game_state=None):
    """Save game state to database.

    Args:
        room_id: Room/save ID (or game_state if called with positional args only)
        game_state: Game state to save

    Returns:
        Game state that was saved
    """
    if game_state is None:
        game_state = room_id
        room_id = DEFAULT_ROOM_ID

    try:
        existing = GameSaveService.load_save_by_name(room_id)

        if existing:
            GameSaveService.update_save(existing.id, game_state)
        else:
            GameSaveService.create_save(room_id, game_state)

        return game_state
    except Exception:
        return game_state


def delete_game_state(room_id=DEFAULT_ROOM_ID):
    """Delete a game save.

    Args:
        room_id: Room/save ID to delete

    Returns:
        Path-like object or None
    """
    try:
        game_save = GameSaveService.load_save_by_name(room_id)
        if game_save:
            GameSaveService.delete_save(game_save.id)
            return f"Deleted {room_id}"
        return None
    except Exception:
        return None


def list_saved_rooms():
    """List all saved game IDs.

    Returns:
        List of room IDs
    """
    try:
        saves = GameSaveService.list_saves()
        return [save.name for save in saves]
    except Exception:
        return []


def migrate_legacy_save(room_id=DEFAULT_ROOM_ID):
    """Migrate legacy JSON save to database.

    Args:
        room_id: Room ID to migrate to

    Returns:
        Migrated game state or None
    """
    if has_save_game(room_id) or not LEGACY_STATE_FILE.exists():
        return None

    try:
        with LEGACY_STATE_FILE.open("r", encoding="utf-8") as handle:
            state = json.load(handle)
    except (OSError, JSONDecodeError, TypeError, ValueError):
        return None

    if not isinstance(state, dict):
        return None

    return save_game_state(room_id, state)


def get_save_path(room_id=DEFAULT_ROOM_ID):
    """Get the path for a save file (legacy compatibility).

    This function is kept for backward compatibility but no longer
    creates files on disk. Returns a Path object for consistency.

    Args:
        room_id: Room ID

    Returns:
        Path object representing the save location
    """
    value = Path(str(room_id))
    if value.suffix == ".json" or value.parent != Path("."):
        return value
    return SAVE_DIR / f"{_safe_room_id(room_id)}.json"


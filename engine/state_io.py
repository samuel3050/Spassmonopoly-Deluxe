import logging

from .game_save_service import GameSaveService

DEFAULT_ROOM_ID = "room_default"

logger = logging.getLogger("spassmonopoly.state_io")


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
        # A swallowed error here previously surfaced to the player as
        # "Das Spiel wurde noch nicht gestartet"; log it so real DB problems
        # (e.g. a locked database) are diagnosable instead of silent.
        logger.exception("load_game_state failed for room_id=%s", room_id)
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

    existing = GameSaveService.load_save_by_name(room_id)

    if existing:
        GameSaveService.update_save(existing.id, game_state)
    else:
        GameSaveService.create_save(room_id, game_state)

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
    """Legacy no-op: JSON file saves are no longer supported."""
    return None


def get_save_path(room_id=DEFAULT_ROOM_ID):
    """Legacy no-op kept for imports; file-based saves are disabled."""
    return None


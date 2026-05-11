import json
from pathlib import Path


def load_game_state(file_path):
    path = Path(file_path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_game_state(file_path, game_state):
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(game_state, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return game_state


import os
from pathlib import Path

try:
    from flask import Flask, jsonify, redirect, render_template, request, session, url_for
except ImportError as exc:
    raise SystemExit(
        "Flask ist nicht installiert. Bitte fuehre `pip install -r requirements.txt` im Ordner "
        "`Spassmonopoly-Deluxe` aus."
    ) from exc

from engine.board_store import BoardStore
from engine.game_engine import apply_field_effect, init_game, move_player, roll_dice
from engine.state_io import load_game_state, save_game_state
from engine.view_state import build_game_payload


APP_NAME = "Spassmonopoly Deluxe"
BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = Path(os.getenv("GAME_STATE_FILE", BASE_DIR / "data" / "current_game_state.json"))

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "spassmonopoly-deluxe-dev-key")
app.json.ensure_ascii = False

board_store = BoardStore()


def has_saved_game():
    return STATE_FILE.exists()


def get_current_state():
    return load_game_state(STATE_FILE)


def persist_state(game_state):
    save_game_state(STATE_FILE, game_state)
    return game_state


def redirect_if_game_missing():
    if not has_saved_game():
        return redirect(url_for("index"))
    return None


def json_error(message, status_code=400):
    return jsonify({"ok": False, "msg": message}), status_code


def render_board():
    return render_template("board.html", game_state=build_game_payload(get_current_state()))


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        player_count = max(2, min(8, int(request.form["anzahl"])))
        session.clear()
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

        board_store.reset_owners()
        game_state = init_game(
            {
                "app_name": APP_NAME,
                "players": players,
                "fields": board_store.load_fields(),
            }
        )
        persist_state(game_state)
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
        return json_error("Das Spiel wurde noch nicht gestartet.", 404)

    return jsonify({"ok": True, "state": build_game_payload(get_current_state())})


@app.route("/zug_wuerfeln", methods=["POST"])
def zug_wuerfeln():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return json_error("Das Spiel wurde noch nicht gestartet.")

    try:
        game_state = persist_state(roll_dice(get_current_state()))
    except ValueError as exc:
        return json_error(str(exc))

    return jsonify({"ok": True, "state": build_game_payload(game_state)})


@app.route("/zug_ziehen", methods=["POST"])
def zug_ziehen():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return json_error("Das Spiel wurde noch nicht gestartet.")

    try:
        game_state = persist_state(move_player(get_current_state()))
    except ValueError as exc:
        return json_error(str(exc))

    return jsonify({"ok": True, "state": build_game_payload(game_state)})


@app.route("/feld_aktion", methods=["POST"])
def feld_aktion():
    missing_game = redirect_if_game_missing()
    if missing_game:
        return json_error("Das Spiel wurde noch nicht gestartet.")

    payload = request.get_json(silent=True) or {}

    try:
        game_state = persist_state(
            apply_field_effect(
                get_current_state(),
                action=payload.get("aktion", "skip"),
                field_id=payload.get("feld"),
            )
        )
    except ValueError as exc:
        return json_error(str(exc))

    return jsonify({"ok": True, "state": build_game_payload(game_state)})


@app.route("/neues_spiel", methods=["POST"])
def neues_spiel():
    session.clear()
    board_store.reset_owners()
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)

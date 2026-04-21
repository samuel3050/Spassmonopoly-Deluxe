from game import app, board_store


if __name__ == "__main__":
    board_store.reset_owners()
    app.run(debug=True)

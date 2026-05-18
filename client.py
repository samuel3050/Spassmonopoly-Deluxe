import webbrowser
import time
import socket


def get_lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"

def join_game():
    # Öffne den Browser zur Lobby
    url = f"http://{get_lan_ip()}:5000/lobby"
    print(f"Öffne Browser zur Lobby: {url}")
    webbrowser.open(url)
    print("Browser geöffnet. Gib deinen Namen in der Lobby ein und warte auf andere Spieler!")
    
    # Halte das Skript offen
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nVerbindung beendet.")

if __name__ == "__main__":
    join_game()

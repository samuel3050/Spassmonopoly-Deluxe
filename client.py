import webbrowser
import time

def join_game():
    # Öffne den Browser zur Lobby
    url = 'http://10.38.80.95:5000/lobby'
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
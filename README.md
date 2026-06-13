# Spassmonopoly Deluxe

Ein browserbasiertes Brettspiel für 2 bis 8 Personen. Würfeln, über das 40-Felder-Brett
ziehen, Felder kaufen, Miete kassieren und Karten ziehen – lokal an einem Gerät oder
gemeinsam in einer Online-Lobby. Die komplette Spiellogik läuft serverseitig (Flask +
SQLAlchemy); jeder Zug, Besitz und Log-Eintrag wird gespeichert und beim Laden
wiederhergestellt.

## Funktionen

- **Punktesystem:** Jeder startet mit 30 Punkten. Felder kosten Punkte, beim Passieren von
  „Los" gibt es einen Bonus, Miete wird vom Besucher an den Eigentümer gezahlt.
- **Voller Spielzug:** Würfeln → Bewegen → Feldaktion → Spielerwechsel → Spielende.
- **Lokal & Online:** 2–8 Spieler an einem Gerät oder eine Lobby mit Beitreten,
  Bereit-Status und synchronem Start (Socket.IO).
- **Durchgehende Musik:** Ein persistenter Rahmen (`/`) hält die Hintergrundmusik am
  Laufen, während die Spielseiten in einem iframe navigieren.
- **Save Manager:** Runden benannt speichern, laden, duplizieren, umbenennen, löschen.
- **Live-Log:** Strukturierte Ereignisse mit Zeitstempel, Kategorien, Suche und Filter.
- **Speicherung:** SQLite lokal (Standard), optional MariaDB/MySQL.

## Spielregeln

1. Spieleranzahl wählen und Namen eintragen – oder über die Lobby beitreten.
2. Jeder Zug besteht aus drei Schritten: **würfeln**, **ziehen**, **Feld auswerten**.
3. Freie Straßen, Bahnhöfe und Werke können für ihren Preis gekauft werden.
4. Auf einem fremden Besitzfeld wird die Miete fällig und an den Eigentümer gezahlt.
5. Wer „Los" passiert oder erreicht, erhält einen Punktebonus.
6. Steuer-, Spezial- und Gemeinschaftsfelder verändern den Punktestand oder bringen
   Ereignisse für einzelne Spieler oder die ganze Runde.
7. Die Runde endet, wenn alle kaufbaren Felder vergeben sind. Es gewinnt, wer die meisten
   Felder besitzt (bei Gleichstand: die meisten Punkte).

## Schnellstart

```bash
python -m venv venv
venv\Scripts\activate          # Windows  (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
python game.py
```

Danach im Browser öffnen: <http://127.0.0.1:5000>

`python game.py` startet mit WebSocket-Unterstützung (Socket.IO). Für einen schlanken
LAN-Start ohne WebSockets dient `server.py` (bindet standardmäßig an `0.0.0.0`):

```bash
python server.py        # Server für andere Geräte im LAN
python client.py        # öffnet die Lobby-URL automatisch im Browser
```

## Projektstruktur

```text
game.py            Flask-App, Routen, Sockets und Spielablauf
server.py          Schlanker LAN-/Deployment-Start (HOST, PORT)
client.py          Öffnet die Lobby-URL im Browser (LAN-Helfer)
board_data.py      Spielfeld-Daten (40 Felder)
engine/
  game_engine.py   Kernlogik: Würfeln, Bewegung, Punkte, Karten, Spielende
  view_state.py    Aufbereiteter UI-State fürs Frontend
  state_io.py      Spielstand laden/speichern
  board_store.py   Spielfeldquelle (Speicher oder DB)
  database.py      SQLAlchemy-Konfiguration und Auto-Migrationen
  models.py        Datenbankmodelle
templates/         HTML-Ansichten (shell, menu, lobby, board, ...)
static/            CSS, JavaScript, Würfelbilder, Musik
tests/             Unit- und Integrationstests
```

## Konfiguration

Vorlage: `.env.example`.

| Variable | Standard | Beschreibung |
| --- | --- | --- |
| `FLASK_SECRET_KEY` | Dev-Key | Secret für Flask-Sessions |
| `GAME_ROOM_ID` | `room_default` | Name des Standard-Spielstands |
| `DB_ENGINE` | `sqlite` | `sqlite` oder `mysql` |
| `DB_FILE` | `spassmonopoly.db` | SQLite-Datei |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | – | MariaDB/MySQL (nur bei `DB_ENGINE=mysql`) |
| `HOST` / `PORT` | `0.0.0.0` / `5000` | Bindung für `server.py` und `client.py` |
| `FLASK_DEBUG` | `0` | Debugmodus |
| `LOG_LEVEL` | `INFO` | Backend-Logging-Level |

## Datenbank

SQLAlchemy mit SQLite als Standard; MariaDB/MySQL über `DB_ENGINE=mysql`. Tabellen:
`games` (Metadaten + kanonischer State), `players`, `fields`, `game_states` (Snapshots),
`logs`, `cards`, `settings`. Der laufende Backend-State ist die einzige Quelle der
Wahrheit – das Frontend sendet nur Aktionen. Benannte Spielstände entstehen über den Save
Manager oder den Speichern-Dialog.

## Musik

Lege eine MP3 in `static/music/` (mitgeliefert: `spassmonopoly_music.mp3`). Alle Dateien
in diesem Ordner werden als Playlist geladen und im Hintergrund geloopt. Achte auf die
Lizenz des Audios (eigene Aufnahmen, lizenzfreie oder freigegebene Musik).

## Entwicklung

```bash
python -m pytest          # Tests
python -m compileall -q . # Syntax-Check
```

Beiträge bitte fokussiert halten und den betroffenen Spielablauf testen. Eine Lizenz ist
vor einer breiten Veröffentlichung noch festzulegen.

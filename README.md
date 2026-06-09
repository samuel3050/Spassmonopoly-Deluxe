# Spassmonopoly Deluxe

Spassmonopoly Deluxe ist ein browserbasiertes Brettspiel fuer 2 bis 8 Personen.
Die App kombiniert Flask, eine Lobby, ein responsives 16:9-Spielbrett,
Wuerfelmechanik, Kartenereignisse, Besitzsystem, strukturierte Logs und
persistente Spielstaende.

## Funktionen

- Lobby mit Beitreten, Bereit-Status und gemeinsamem Spielstart
- Voller Kernfluss: Wuerfeln, Bewegen, Feldaktion, Spielerwechsel, Spielende
- 40 Felder mit Kauf, Abgabe, Steuer, Gemeinschaftskarten und Spezialeffekten
- Responsive Board-Ansicht fuer Desktop, Tablet und kleinere Displays
- Strukturierter Live-Log mit Zeitstempel, Kategorien, Suche und Filter
- SQLAlchemy-Speicherung mit SQLite lokal und optional MariaDB/MySQL
- LAN-Start ueber `server.py` und Browser-Client ueber `client.py`

## Schnellstart

1. Repository klonen und in den Projektordner wechseln.
2. Virtuelle Umgebung anlegen und aktivieren:

   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. Abhaengigkeiten installieren:

   ```bash
   pip install -r requirements.txt
   ```

4. Server starten:

   ```bash
   python game.py
   ```

5. Im Browser oeffnen:

   ```text
   http://127.0.0.1:5000
   ```

## LAN-Modus

```bash
python server.py
```

Der LAN-Server bindet standardmaessig an `0.0.0.0`. Andere Spieler koennen die
IP-Adresse des Host-Rechners im Browser oeffnen. `client.py` oeffnet die Lobby
automatisch ueber die lokale LAN-Adresse:

```bash
python client.py
```

## Projektstruktur

```text
.
|-- game.py                 # Flask-App, Routen und Spielablauf
|-- server.py               # LAN/Deployment-Start mit HOST und PORT
|-- client.py               # Oeffnet die Lobby im Browser
|-- board_data.py           # Integrierte Spielfeld-Daten
|-- engine/
|   |-- game_engine.py      # Kernlogik fuer Wuerfeln, Bewegung, Karten und Spielende
|   |-- view_state.py       # Aufbereiteter UI-State
|   |-- state_io.py         # Spielstand laden/speichern
|   |-- board_store.py      # Spielfeldquelle: Speicher oder optionale DB
|   |-- database.py         # SQLAlchemy-Konfiguration und Auto-Migrationen
|   `-- models.py           # Datenbankmodelle
|-- templates/              # HTML-Ansichten
|-- static/                 # CSS, JavaScript und Wuerfelbilder
|-- tests/                  # Unit- und Integrationschecks
|-- regelblatt.md           # Kurze Spielregeln
`-- requirements.txt        # Python-Abhaengigkeiten
```

## Konfiguration

Eine Vorlage liegt in `.env.example`.

| Variable | Standard | Beschreibung |
| --- | --- | --- |
| `FLASK_SECRET_KEY` | Dev-Key | Secret fuer Flask-Sessions |
| `GAME_ROOM_ID` | `room_default` | Name des Standard-Spielstands |
| `DB_ENGINE` | `sqlite` | `sqlite` oder `mysql` |
| `DB_FILE` | `spassmonopoly.db` | SQLite-Datei |
| `DB_HOST` | `localhost` | MariaDB/MySQL-Host |
| `DB_PORT` | `3306` | MariaDB/MySQL-Port |
| `DB_USER` | `root` | MariaDB/MySQL-User |
| `DB_PASSWORD` | leer | MariaDB/MySQL-Passwort |
| `DB_NAME` | `spassmonopoly` | MariaDB/MySQL-Datenbank |
| `HOST` | `0.0.0.0` | Host fuer `server.py` |
| `PORT` | `5000` | Port fuer `server.py` und `client.py` |
| `FLASK_DEBUG` | `0` | Debugmodus |
| `LOG_LEVEL` | `INFO` | Backend-Logging-Level |

## Datenbank

Die App nutzt SQLAlchemy. SQLite ist fuer lokale Entwicklung der Standard,
MariaDB/MySQL kann ueber `DB_ENGINE=mysql` aktiviert werden.

Release-relevante Tabellen:

- `games`: Metadaten und aktueller kanonischer Spielstand
- `players`: query-freundliche Spielerprojektion
- `fields`: query-freundliche Feldprojektion
- `game_state`: persistierte State-Snapshots
- `logs`: strukturierte Spielereignisse
- `cards`: persistierte Kartendefinitionen
- `settings`: Spiel- und Feature-Einstellungen

Legacy-Saves aus der alten Tabelle `game_saves` werden beim Start automatisch in
`games` uebernommen.

## Entwicklung

Vor einem Pull Request oder Release:

```bash
python -m compileall -q .
python -m unittest discover -s tests
```

Manuelle Release-Checks:

1. Neue lokale Runde mit 2 bis 4 Spielern starten.
2. Wuerfeln, bewegen und Feldaktion abschliessen.
3. Kaufbare Felder kaufen, Spezialfelder und Gemeinschaftskarten ausloesen.
4. Lobby oeffnen, mehrere Spieler beitreten lassen und Start pruefen.
5. Spielstand fortsetzen und Save-APIs pruefen.

## Open Source

Beitraege sind willkommen. Bitte halte Aenderungen fokussiert, dokumentiere neue
Konfigurationen in dieser README und teste den betroffenen Spielablauf manuell.
Eine Lizenzdatei sollte vor einer breiten Veroeffentlichung noch bewusst
festgelegt werden.

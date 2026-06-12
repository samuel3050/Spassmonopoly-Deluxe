# Spassmonopoly Deluxe

Spassmonopoly Deluxe ist ein browserbasiertes Brettspiel für 2 bis 8 Personen.
Die App kombiniert Flask, eine Lobby, ein responsives 16:9-Spielbrett,
Würfelmechanik, Kartenereignisse, Besitzsystem, strukturierte Logs und
persistente Spielstände.

## Funktionen

- Lobby mit Beitreten, Bereit-Status und gemeinsamem Spielstart
- Voller Kernfluss: Würfeln, Bewegen, Feldaktion, Spielerwechsel, Spielende
- 40 Felder mit Kauf, Abgabe, Steuer, Gemeinschaftskarten und Spezialeffekten
- Responsive Board-Ansicht für Desktop, Tablet und kleinere Displays
- Strukturierter Live-Log mit Zeitstempel, Kategorien, Suche und Filter
- SQLAlchemy-Speicherung mit SQLite lokal und optional MariaDB/MySQL
- LAN-Start über `server.py` und Browser-Client über `client.py`

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

5. Im Browser öffnen:

   ```text
   http://127.0.0.1:5000
   ```

## LAN-Modus

```bash
python server.py
```

Der LAN-Server bindet standardmaessig an `0.0.0.0`. Andere Spieler koennen die
IP-Adresse des Host-Rechners im Browser öffnen. `client.py` öffnet die Lobby
automatisch über die lokale LAN-Adresse:

```bash
python client.py
```

## Projektstruktur

```text
.
|-- game.py                 # Flask-App, Routen und Spielablauf
|-- server.py               # LAN/Deployment-Start mit HOST und PORT
|-- client.py               # Öffnet die Lobby im Browser
|-- board_data.py           # Integrierte Spielfeld-Daten
|-- engine/
|   |-- game_engine.py      # Kernlogik für Würfeln, Bewegung, Karten und Spielende
|   |-- view_state.py       # Aufbereiteter UI-State
|   |-- state_io.py         # Spielstand laden/speichern
|   |-- board_store.py      # Spielfeldquelle: Speicher oder optionale DB
|   |-- database.py         # SQLAlchemy-Konfiguration und Auto-Migrationen
|   `-- models.py           # Datenbankmodelle
|-- templates/              # HTML-Ansichten
|-- static/                 # CSS, JavaScript und Würfelbilder
|-- tests/                  # Unit- und Integrationschecks
|-- regelblatt.md           # Kurze Spielregeln
`-- requirements.txt        # Python-Abhaengigkeiten
```

## Konfiguration

Eine Vorlage liegt in `.env.example`.

| Variable | Standard | Beschreibung |
| --- | --- | --- |
| `FLASK_SECRET_KEY` | Dev-Key | Secret für Flask-Sessions |
| `GAME_ROOM_ID` | `room_default` | Name des Standard-Spielstands |
| `DB_ENGINE` | `sqlite` | `sqlite` oder `mysql` |
| `DB_FILE` | `spassmonopoly.db` | SQLite-Datei |
| `DB_HOST` | `localhost` | MariaDB/MySQL-Host |
| `DB_PORT` | `3306` | MariaDB/MySQL-Port |
| `DB_USER` | `root` | MariaDB/MySQL-User |
| `DB_PASSWORD` | leer | MariaDB/MySQL-Passwort |
| `DB_NAME` | `spassmonopoly` | MariaDB/MySQL-Datenbank |
| `HOST` | `0.0.0.0` | Host für `server.py` |
| `PORT` | `5000` | Port für `server.py` und `client.py` |
| `FLASK_DEBUG` | `0` | Debugmodus |
| `LOG_LEVEL` | `INFO` | Backend-Logging-Level |

## Datenbank

Die App nutzt SQLAlchemy. SQLite ist für lokale Entwicklung der Standard,
MariaDB/MySQL kann über `DB_ENGINE=mysql` aktiviert werden.

Release-relevante Tabellen:

- `games`: Metadaten und aktueller kanonischer Spielstand
- `players`: query-freundliche Spielerprojektion
- `fields`: query-freundliche Feldprojektion
- `game_states`: persistierte State-Snapshots
- `logs`: strukturierte Spielereignisse
- `cards`: persistierte Kartendefinitionen
- `settings`: Spiel- und Feature-Einstellungen

Legacy-Saves aus der alten Tabelle `game_saves` werden beim Start automatisch in
`games` übernommen.

## Speicherablauf

Single Source of Truth ist der Flask-Backend-State. Das Frontend sendet nur
Aktionen wie Würfeln, Bewegen, Feldaktion, Speichern oder Beenden.

Manuelles Speichern:

1. `/api/save-current` laedt den aktuellen Backend-State.
2. Der State wird validiert: Spieler, Board, Positionen, Würfel, offene Aktion,
   Karten und Settings.
3. SQLAlchemy schreibt `games`, `players`, `fields`, `game_states`, `cards`,
   `logs` und `settings` in einer DB-Transaktion.
4. Bei Erfolg wird committed und die UI zeigt eine Erfolgsmeldung.
5. Bei Fehler wird gerollbackt und die UI erhält eine Fehlermeldung.

Der laufende Backend-State wird nach Würfelwurf, Bewegung, Feldaktion,
Kartenereignis und Spielerwechsel persistiert. Benannte Spielstände entstehen
gezielt über den Save Manager oder den Speichern-Dialog im Spiel.

## Entwicklung

Vor einem Pull Request oder Release:

```bash
python -m compileall -q .
python -m unittest discover -s tests
```

Manuelle Release-Checks:

1. Neue lokale Runde mit 2 bis 4 Spielern starten.
2. Würfeln, bewegen und Feldaktion abschließen.
3. Kaufbare Felder kaufen, Spezialfelder und Gemeinschaftskarten ausloesen.
4. Lobby öffnen, mehrere Spieler beitreten lassen und Start prüfen.
5. Spielstand fortsetzen und Save-APIs pruefen.

## Open Source

Beiträge sind willkommen. Bitte halte Änderungen fokussiert, dokumentiere neue
Konfigurationen in dieser README und teste den betroffenen Spielablauf manuell.
Eine Lizenzdatei sollte vor einer breiten Veröffentlichung noch bewusst
festgelegt werden.

## Musik / Hintergrund-Audio

Das Projekt liefert keinen urheberrechtlich geschützten Monopoly-Soundtrack.
Stattdessen sucht die App standardmäßig nach einer Datei unter
`static/music/monopoly_theme.mp3` und spielt diese als Schleife ab, falls sie
vorhanden ist. Falls keine Datei gefunden wird, verwendet die Oberfläche einen
leisen Ambient-Fallback, der kein lautes Rauschen erzeugt.

Wenn du ein eigenes Titelstück nutzen möchtest, lege eine geeignete MP3-Datei
mit dem Namen `monopoly_theme.mp3` in den Ordner `static/music/`.

Hinweis: Bitte achte auf die Lizenz des Audios — verwende entweder eigene
Aufnahmen, lizenzfreie Musik oder Musik, für die du die Nutzungserlaubnis hast.

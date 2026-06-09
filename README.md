# Spassmonopoly Deluxe

Spassmonopoly Deluxe ist ein browserbasiertes Brettspiel fuer 2 bis 8 Personen.
Das Projekt kombiniert eine Flask-App, eine Lobby fuer gemeinsame Runden,
ein responsives Spielbrett, Wuerfelablauf, Besitzsystem und gespeicherte
Spielstaende.

## Funktionen

- Lobby mit Beitreten, Bereit-Status und gemeinsamem Spielstart
- Spielbrett mit 40 Feldern, Besitz, Kauf, Abgabe und Spezialfeldern
- Echtzeit-nahe Aktualisierung im Browser ueber Polling
- Lokale Speicherung der aktuellen Runde per SQLite
- Optionale MySQL-Anbindung fuer Spielfelder
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

Der LAN-Server bindet standardmaessig an alle Netzwerkinterfaces:

```bash
python server.py
```

Andere Spieler koennen danach die IP-Adresse des Host-Rechners im Browser
aufrufen. Alternativ oeffnet `client.py` die Lobby automatisch ueber die lokale
LAN-Adresse:

```bash
python client.py
```

## Projektstruktur

```text
.
├── game.py                 # Flask-App, Routen und Spielablauf
├── server.py               # LAN/Deployment-Start mit HOST und PORT
├── client.py               # Oeffnet die Lobby im Browser
├── board_data.py           # Integrierte Spielfeld-Daten
├── engine/
│   ├── game_engine.py      # Kernlogik fuer Wuerfeln, Bewegung und Felder
│   ├── view_state.py       # Aufbereiteter UI-State
│   ├── state_io.py         # Spielstand laden/speichern
│   ├── board_store.py      # Spielfeldquelle: Speicher oder optionale DB
│   ├── database.py         # SQLAlchemy-Konfiguration
│   └── models.py           # Datenbankmodelle
├── templates/              # HTML-Ansichten
├── static/                 # CSS, JavaScript und Wuerfelbilder
├── regelblatt.md           # Kurze Spielregeln
└── requirements.txt        # Python-Abhaengigkeiten
```

## Konfiguration

Die wichtigsten Einstellungen koennen ueber Umgebungsvariablen gesetzt werden.
Eine Vorlage liegt in `.env.example`.

| Variable | Standard | Beschreibung |
| --- | --- | --- |
| `FLASK_SECRET_KEY` | Dev-Key | Secret fuer Flask-Sessions |
| `GAME_ROOM_ID` | `room_default` | Name des Standard-Spielstands |
| `DB_ENGINE` | `sqlite` | `sqlite` oder `mysql` |
| `DB_FILE` | `spassmonopoly.db` | SQLite-Datei |
| `HOST` | `0.0.0.0` | Host fuer `server.py` |
| `PORT` | `5000` | Port fuer `server.py` |
| `FLASK_DEBUG` | `0` | Debugmodus fuer `server.py` |

Lokale Dateien wie `.env`, virtuelle Umgebungen, Caches und Datenbanken werden
per `.gitignore` aus dem Repository herausgehalten.

## Entwicklung

Vor einem Pull Request oder einer groesseren Aenderung sollten mindestens die
Python-Dateien kompiliert und die Tests ausgefuehrt werden:

```bash
python -m compileall -q .
python -m unittest discover -s tests
```

Zum manuellen Testen reichen fuer den Kernfluss:

1. Neue lokale Runde mit 2 bis 4 Spielern starten.
2. Wuerfeln, Figur bewegen und Feldaktion abschliessen.
3. Lobby oeffnen, zwei Spieler beitreten lassen, beide bereit setzen.
4. Spiel fortsetzen oder neue Runde starten.

## Open Source

Beitraege sind willkommen. Bitte halte Aenderungen fokussiert, dokumentiere neue
Konfigurationen in dieser README und teste den betroffenen Spielablauf manuell.
Eine Lizenzdatei sollte vor einer breiten Veroeffentlichung noch bewusst
festgelegt werden.

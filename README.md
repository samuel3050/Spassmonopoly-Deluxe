# Spaßmonopoly Deluxe

Spaßmonopoly Deluxe ist ein browserbasiertes Brettspiel mit moderner Oberfläche,
klarer Zugführung, Besitzsystem und responsivem Spielbrett.

## Starten

1. In den Projektordner wechseln:
   `cd Spassmonopoly-Deluxe`
2. Abhängigkeiten installieren:
   `pip install -r requirements.txt`
3. Server starten:
   `python game.py`

Danach ist das Spiel unter `http://127.0.0.1:5000` erreichbar.

## Architektur

Das Projekt ist in eine reine Engine und eine schlanke Flask-Oberflaeche getrennt:

- `engine/game_engine.py`: Spiellogik ohne Flask-, HTML- oder Session-Abhaengigkeit.
- `engine/state_io.py`: Laden und Speichern des zentralen JSON-Game-States.
- `engine/view_state.py`: abgeleiteter UI-Snapshot aus dem kanonischen State.
- `engine/board_store.py`: Spielfeld-Konfiguration aus MySQL oder `board_data.py`.
- `game.py`: Flask-Routen; sie laden State, rufen Engine-Funktionen auf und speichern State.
- `data/current_game_state.json`: laufender Server-State der lokalen Partie.

Der kanonische State enthaelt Spieler, aktiven Spieler, Reihenfolge, Spielfeld,
Wuerfelstatus, offene Feldaktionen, Spielstatus und Verlauf. Browser-Aktionen wie
Wuerfeln, Ziehen und Feldaktion veraendern ausschliesslich diesen JSON-State ueber
die Engine.

## Highlights

- Professionelle Start-, Lobby- und Spielansicht mit klarer UX.
- Sauberer Zugablauf: würfeln, bewegen, Feld prüfen.
- Fallback auf integrierte Spielfeld-Daten, falls keine MySQL-Datenbank erreichbar ist.
- Besitzübersicht, Live-Spielverlauf und Rundenstatistiken in Echtzeit.
- Einheitliche Sprache mit vollständigen Umlauten in der Oberfläche.

## Optionale Datenbank-Konfiguration

Wenn du MySQL verwenden willst, kannst du diese Umgebungsvariablen setzen:

- `DB_HOST`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `FLASK_SECRET_KEY`

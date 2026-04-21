# Spassmonopoly-Deluxe

Spassmonopoly-Deluxe ist ein browserbasiertes Trinkspiel im Monopoly-Stil mit Lobby,
Wuerfelanimation, Besitzsystem und responsivem Spielbrett.

## Starten

1. In den Projektordner wechseln:
   `cd Spassmonopoly-Deluxe`
2. Abhaengigkeiten installieren:
   `pip install -r requirements.txt`
3. Server starten:
   `python game.py`

Danach ist das Spiel unter `http://127.0.0.1:5000` erreichbar.

## Verbesserungen

- Die App faellt automatisch auf integrierte Spielfeld-Daten zurueck, wenn MySQL fehlt.
- Mit erreichbarer MySQL-Datenbank werden die Spielfelder weiter aus `spielfelder` geladen.
- `app.py`, `flaskserver.py` und `game.py` starten jetzt dieselbe Haupt-App.
- Das UI wurde fuer Desktop und Mobilgeraete deutlich aufgeraeumt.
- Der Zugablauf ist stabiler: Wurf, Bewegung und Feldauswertung laufen sauber nacheinander.

## Optionale Datenbank-Konfiguration

Wenn du MySQL verwenden willst, kannst du diese Umgebungsvariablen setzen:

- `DB_HOST`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `FLASK_SECRET_KEY`

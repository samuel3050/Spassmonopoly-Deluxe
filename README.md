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

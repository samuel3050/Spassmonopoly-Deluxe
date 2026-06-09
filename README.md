# Spassmonopoly Deluxe

Browserbasiertes Brettspiel mit Lobby, responsivem Spielbrett, Besitzsystem,
Wuerfelablauf und gespeicherten Spielstaenden.

## Starten

1. Abhaengigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```
2. Server starten:
   ```bash
   python game.py
   ```
3. Im Browser oeffnen:
   ```text
   http://127.0.0.1:5000
   ```

## Struktur

- `game.py`: Flask-App, Routen und Spielablauf.
- `server.py`: Server-Start fuer LAN/Deployment mit `HOST` und `PORT`.
- `client.py`: Lobby im Browser ueber die LAN-Adresse oeffnen.
- `board_data.py`: integrierte Spielfeld-Daten.
- `engine/`: Spiellogik, Speicherlogik, Datenmodelle und UI-State.
- `templates/`: HTML-Ansichten fuer Start, Lobby und Spielbrett.
- `static/`: CSS, JavaScript und Wuerfelbilder.
- `regelblatt.md`: kurze Spielregeln.

## Konfiguration

Die App kann ueber Umgebungsvariablen konfiguriert werden. Eine Vorlage liegt in
`.env.example`. Lokale Dateien wie `.env`, virtuelle Umgebungen, Caches und
Spielstand-Datenbanken werden per `.gitignore` aus dem Repo herausgehalten.

# SpassMonopoly Deluxe - Schnellstart mit MariaDB

## ⚡ 5-Minuten-Setup

### 1. Dependencies
```bash
pip install -r requirements.txt
```

### 2. Umgebung
```bash
cp .env.example .env
# Bearbeite .env mit Ihren DB-Credentials
```

### 3. Datenbank
```bash
mysql -u root -p
mysql> CREATE DATABASE spassmonopoly CHARACTER SET utf8mb4;
mysql> EXIT;
```

### 4. Starten
```bash
python game.py
```

Die Datenbank wird beim Start automatisch initialisiert!

## 📋 Neue API-Endpunkte

| Methode | Pfad | Funktion |
|---------|------|----------|
| GET | `/api/saves` | Alle Spielstände auflisten |
| GET | `/api/save/<id>` | Spielstand Details |
| POST | `/api/save/<id>/load` | Spielstand laden |
| POST | `/api/save/<id>/rename` | Umbenennen |
| POST | `/api/save/<id>/delete` | Löschen |
| POST | `/api/save/<id>/duplicate` | Duplizieren |

## 🔧 Konfiguration (.env)

```ini
DB_HOST=localhost        # MySQL Host
DB_PORT=3306            # MySQL Port
DB_USER=root            # MySQL User
DB_PASSWORD=            # MySQL Password
DB_NAME=spassmonopoly   # Datenbankname
FLASK_SECRET_KEY=...    # Session-Verschlüsselung
```

## 📊 Datenbank-Tabellen

| Tabelle | Zweck |
|---------|--------|
| `game_saves` | Spielstand-Metadaten + kompletter State |
| `players` | Spielerdaten pro Spielstand |
| `fields` | Spielfeld-Informationen |
| `game_events` | Event-Protokoll |

## ✨ Features

- ✓ Beliebig viele Spielstände
- ✓ Automatisches Speichern nach Zügen
- ✓ Spielstände umbenennen/löschen/duplizieren
- ✓ Vollständige State-Wiederherstellung
- ✓ Legacy JSON-Migration
- ✓ ACID-Transaktionen
- ✓ Fehlerbehandlung

## 🧪 Testen

```bash
python test_integration.py
```

## 📝 Detaillierte Dokumentation

Siehe: `DATABASE_INTEGRATION.md`

## 🐛 Troubleshooting

### MySQL läuft nicht?
```bash
sudo service mysql start   # Linux/Mac
# oder MySQL GUI öffnen
```

### Keine Verbindung?
```bash
# Überprüfe .env
# Überprüfe MySQL läuft
mysql -u root -p  # Test Anmeldung
```

### Tabellen nicht erstellt?
```bash
# Lösche DB und lass neu erstellen
mysql -u root -p -e "DROP DATABASE spassmonopoly;"
# App startet neu mit CREATE DATABASE
```

## 📁 Projektstruktur

```
.
├── game.py                    # Flask App (angepasst)
├── requirements.txt           # Dependencies (aktualisiert)
├── .env.example              # Konfigurationsvorlage
├── DATABASE_INTEGRATION.md   # Vollständige Dokumentation
├── engine/
│   ├── database.py           # SQLAlchemy Setup (NEU)
│   ├── models.py             # ORM Modelle (NEU)
│   ├── game_save_service.py  # Service Layer (NEU)
│   ├── state_io.py           # I/O Layer (ÜBERARBEITET)
│   ├── game_engine.py        # Spiellogik (ungeändert)
│   ├── board_store.py        # Board-Verwaltung (ungeändert)
│   └── view_state.py         # View-Präparation (ungeändert)
└── test_integration.py        # Tests (NEU)
```

## 🚀 Production Deployment

1. **Secrets sichern**
   - `.env` nicht committen
   - Environment-Variablen auf Server setzen

2. **Database**
   - Backup vor Migration
   - Connection Pool anpassen (pool_size/max_overflow)
   - Read-Replicas für Skalierbarkeit

3. **Monitoring**
   - Logs aktivieren (SQLALCHEMY_ECHO=True)
   - Error Tracking (Sentry, etc.)
   - Slow Query Logging

4. **Performance**
   - Indizes überprüfen
   - Query-Profiling
   - Caching (Redis optional)

## 📞 Support

Weitere Informationen in `DATABASE_INTEGRATION.md`

---

**Version:** 1.0  
**Status:** ✓ Production-Ready  
**Letztes Update:** 2026-06-01

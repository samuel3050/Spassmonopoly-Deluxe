"""Flask basierte Umsetzung eines einfachen Sauf‑Monopoly."""

from contextlib import contextmanager  # Importiert einen Kontextmanager für die Datenbankverbindung
from flask import Flask, render_template, request, redirect, url_for, session, jsonify  # Flask und Hilfsfunktionen importieren
import os  # Für Umgebungsvariablen
import random  # Für Würfeln
import mysql.connector  # Für MySQL-Datenbankzugriff

app = Flask(__name__)  # Erstellt die Flask-App
app.secret_key = "supersecretkey"  # Setzt den Secret Key für Sessions

# Datenbank Konfiguration kann über Umgebungsvariablen angepasst werden
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),  # Hostname der Datenbank
    "user": os.getenv("DB_USER", "root"),  # Benutzername
    "password": os.getenv("DB_PASSWORD", ""),  # Passwort
    "database": os.getenv("DB_NAME", "saufmonopoly"),  # Datenbankname
}


@contextmanager
def db_cursor(dictionary=False):
    """Context manager der einen Datenbank Cursor liefert."""
    conn = mysql.connector.connect(**DB_CONFIG)  # Verbindet zur Datenbank
    cursor = conn.cursor(dictionary=dictionary)  # Erstellt einen Cursor (optional als Dict)
    try:
        yield cursor  # Gibt den Cursor zurück
        conn.commit()  # Speichert Änderungen
    finally:
        cursor.close()  # Schließt den Cursor
        conn.close()  # Schließt die Verbindung

FELD_ANZAHL = 40  # Anzahl der Spielfelder

def reset_besitzer():
    """Setzt alle Spielfelder auf 'frei'."""
    with db_cursor() as cursor:
        cursor.execute("UPDATE spielfelder SET besitzer=NULL")  # Setzt alle Besitzer auf NULL

def lade_felder_infos():
    """Lädt alle Spielfeld Informationen als Liste von Dicts."""
    with db_cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM spielfelder ORDER BY feld_id ASC")  # Holt alle Felder sortiert
        return cursor.fetchall()  # Gibt die Felder als Liste zurück

def get_besitz_uebersicht():
    felder_infos = lade_felder_infos()  # Holt alle Felder
    besitz = {}  # Dictionary für Besitz
    for feld in felder_infos:
        if feld.get("besitzer"):  # Wenn das Feld einen Besitzer hat
            besitz.setdefault(feld["besitzer"], []).append(feld)  # Füge das Feld dem Besitzer hinzu
    return besitz  # Gibt das Besitz-Dict zurück

def parse_schlucke(text):
    import re  # Reguläre Ausdrücke für die Extraktion der Zahl
    if not text:
        return 0  # Wenn kein Text, dann 0
    match = re.search(r"(\d+)", str(text))  # Sucht nach einer Zahl im Text
    return int(match.group(1)) if match else 0  # Gibt die gefundene Zahl zurück

@app.route("/", methods=["GET", "POST"])
def index():
    # Startseite: Spieleranzahl wählen
    if request.method == "POST":
        session.clear()  # Leert die Session
        anzahl = int(request.form["anzahl"])  # Holt die Spieleranzahl aus dem Formular
        session["anzahl"] = anzahl  # Speichert die Anzahl in der Session
        return redirect(url_for("namen"))  # Weiter zur Namenseingabe
    return render_template("index.html")  # Zeigt das Formular an

@app.route("/namen", methods=["GET", "POST"])
def namen():
    # Namenseingabe für alle Spieler
    if request.method == "POST":
        spieler = []
        for i in range(1, session["anzahl"] + 1):  # Für jeden Spieler
            spieler.append(request.form[f"spieler{i}"])  # Namen aus dem Formular holen
        session["spieler"] = spieler  # Speichert die Spielernamen
        session["positionen"] = [0 for _ in range(len(spieler))]  # Startpositionen
        session["aktiver"] = 0  # Wer ist dran
        session["konto"] = [0] * len(spieler)  # Schlucke-Konto
        session["gesamt"] = [0] * len(spieler)  # Gesamtwürfe
        session["pending_popup"] = None  # Kein Popup offen
        session["warte_auf_wurf"] = True  # Warten auf Würfeln
        return redirect(url_for("spiel"))  # Weiter zum Spiel
    return render_template("spielernamen.html", anzahl=session["anzahl"])  # Zeigt das Namensformular

@app.route("/board", methods=["GET", "POST"])
def spiel():
    # Hauptspiel-Route
    felder_infos = lade_felder_infos()  # Holt alle Felderinfos
    aktiver = session.get("aktiver", 0)  # Aktiver Spieler
    pos_liste = session.get("positionen", [])  # Positionen der Spieler
    pending_popup = session.get("pending_popup")  # Offenes Feld-Popup
    warte_auf_wurf = session.get("warte_auf_wurf", True)  # Ob auf Wurf gewartet wird
    wurf = session.get("wurf")  # Letzter Wurf

    # 1. Spieler ist dran
    if warte_auf_wurf:
        if request.method == "POST":
            # Würfeln im Backend!
            würfel1 = random.randint(1, 6)  # Erster Würfel
            würfel2 = random.randint(1, 6)  # Zweiter Würfel
            summe = würfel1 + würfel2  # Summe der Würfel
            session["wurf"] = [würfel1, würfel2]  # Speichert den Wurf
            session["warte_auf_wurf"] = False  # Nicht mehr warten
            return redirect("/board")  # Seite neu laden
        return render_template(
            "board.html",
            spieler=session.get("spieler", []),  # Spielernamen
            aktiver=aktiver,  # Aktiver Spieler
            zeige_wer_ist_dran=True,  # Zeige "Wer ist dran"-Modal
            felder_infos=felder_infos,  # Felderinfos
            positionen=pos_liste,  # Positionen
            konto=session.get("konto", []),  # Schlucke-Konto
            besitz=get_besitz_uebersicht(),  # Besitzübersicht
            felder=list(range(40)),  # Feld-IDs
            wurf=None,  # Kein Wurf anzeigen
            feldinfo=None,  # Kein Feldinfo-Popup
            popup_spieler=None,  # Kein Popup-Spieler
            zeige_feldinfo=False,  # Kein Feldinfo anzeigen
            zeige_wurf_popup=False  # Kein Wurf-Popup
        )

    # 2. Würfelanimation und Wurf-Popup
    if not warte_auf_wurf and not pending_popup:
        if request.method == "POST":
            wurf = session.get("wurf")  # Holt den letzten Wurf
            summe = wurf[0] + wurf[1]  # Summe der Würfel
            aktuelle_pos = session["positionen"][aktiver]  # Aktuelle Position
            neue_pos = (aktuelle_pos + summe) % len(felder_infos)  # Neue Position nach dem Zug
            session["positionen"][aktiver] = neue_pos  # Speichert neue Position
            session["gesamt"][aktiver] += summe  # Addiert zur Gesamtzahl
            session["pending_popup"] = {
                "spieler": aktiver,
                "feld": neue_pos,
                "wurf": wurf
            }  # Öffnet das Feld-Popup
            session["wurf"] = None  # Setzt den Wurf zurück
            session["warte_auf_wurf"] = False  # Nicht mehr warten
            return redirect("/board")  # Seite neu laden
        return render_template(
            "board.html",
            spieler=session.get("spieler", []),
            aktiver=aktiver,
            zeige_wer_ist_dran=False,
            felder_infos=felder_infos,
            positionen=session.get("positionen", []),
            konto=session.get("konto", []),
            besitz=get_besitz_uebersicht(),
            felder=list(range(40)),
            wurf=session.get("wurf"),
            feldinfo=None,
            popup_spieler=None,
            zeige_feldinfo=False,
            zeige_wurf_popup=True  # Zeige das Wurf-Popup
        )

    # 3. Feld-Popup
    if pending_popup:
        popup_spieler = pending_popup["spieler"]  # Spieler, der dran ist
        popup_feldinfo = felder_infos[pending_popup["feld"]]  # Feldinfo für das aktuelle Feld
        popup_wurf = pending_popup["wurf"]  # Wurf, der zu diesem Feld geführt hat
    else:
        popup_feldinfo = None
        popup_spieler = None
        popup_wurf = None

    return render_template(
        "board.html",
        felder=list(range(40)),  # Board-Index 0..39
        spieler=session.get("spieler", []),
        positionen=session.get("positionen", []),
        aktiver=aktiver,
        wurf=popup_wurf,
        feldinfo=popup_feldinfo,
        popup_spieler=popup_spieler,
        zeige_feldinfo=bool(pending_popup),  # Zeige das Feldinfo-Popup, falls vorhanden
        felder_infos=felder_infos,
        konto=session.get("konto", []),
        besitz=get_besitz_uebersicht(),
        zeige_wer_ist_dran=False,
        zeige_wurf_popup=False
    )

@app.route("/feld_aktion", methods=["POST"])
def feld_aktion():
    data = request.get_json()  # Holt die Aktion aus dem Request
    aktion = data.get("aktion")  # Aktionstyp (kaufen, miete, skip)
    board_index = int(data.get("feld"))  # Index des Feldes (0..39)
    pending_popup = session.get("pending_popup")  # Aktuelles Popup
    if not pending_popup:
        return jsonify({"ok": False, "msg": "Kein aktiver Zug!"})  # Kein aktiver Zug

    aktiver = pending_popup["spieler"]  # Aktiver Spieler
    felder_infos = lade_felder_infos()  # Holt Felderinfos
    feld = felder_infos[board_index]  # Das aktuelle Feld
    feld_id = feld["feld_id"]  # Eindeutige ID des Feldes

    if aktion == "kaufen":
        spielername = session["spieler"][aktiver]  # Name des aktiven Spielers
        with db_cursor() as cursor:
            cursor.execute(
                "UPDATE spielfelder SET besitzer=%s WHERE feld_id=%s",
                (spielername, feld_id),
            )  # Setzt den Besitzer in der DB anhand der ID
        schlucke = parse_schlucke(feld.get("kaufpreis"))  # Holt die Schlucke für den Kauf
        session["konto"][aktiver] += schlucke  # Addiert Schlucke zum Konto
        session["pending_popup"] = None  # Popup schließen
        session["aktiver"] = (aktiver + 1) % len(session["spieler"])  # Nächster Spieler
        session["warte_auf_wurf"] = True  # Wieder auf Wurf warten
        return jsonify({"ok": True})

    if aktion == "miete":
        besitzer_name = feld.get("besitzer")  # Besitzer des Feldes
        if besitzer_name:
            schlucke = parse_schlucke(feld.get("miete"))  # Holt die Schlucke für die Miete
            session["konto"][aktiver] += schlucke  # Addiert Schlucke zum Konto
        session["pending_popup"] = None  # Popup schließen
        session["aktiver"] = (aktiver + 1) % len(session["spieler"])  # Nächster Spieler
        session["warte_auf_wurf"] = True  # Wieder auf Wurf warten
        return jsonify({"ok": True})

    if aktion == "skip":
        session["pending_popup"] = None  # Popup schließen
        session["aktiver"] = (aktiver + 1) % len(session["spieler"])  # Nächster Spieler
        session["warte_auf_wurf"] = True  # Wieder auf Wurf warten
        return jsonify({"ok": True})

    return jsonify({"ok": False})  # Unbekannte Aktion

if __name__ == "__main__":
    reset_besitzer()  # Setzt alle Felder auf frei beim Start
    app.run(debug=True)  # Startet die Flask-App im Debug-Modus
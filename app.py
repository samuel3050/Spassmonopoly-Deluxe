from flask import Flask, render_template, request, redirect, session, url_for
import random

# Flask-Anwendung initialisieren
app = Flask(__name__)

# Geheimschlüssel für Sitzungsdaten (wird für Session benötigt)
app.secret_key = "supersecretkey"

# Startseite: Spieleranzahl eingeben
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Spieleranzahl aus dem Formular lesen und in der Session speichern
        session["anzahl"] = int(request.form["anzahl"])
        # Weiterleitung zur Seite für Spielernamen
        return redirect("/namen")
    
    # HTML-Seite zum Eingeben der Spieleranzahl anzeigen
    return render_template("index.html")

# Seite zum Eingeben der Spielernamen
@app.route("/namen", methods=["GET", "POST"])
def namen():
    if request.method == "POST":
        # Namen aller Spieler auslesen (basierend auf Anzahl aus Session)
        spieler = [request.form[f"spieler{i}"] for i in range(1, session["anzahl"] + 1)]
        
        # Spielernamen in Session speichern
        session["spieler"] = spieler
        # Aktiven Spieler (Index) auf 0 setzen (erster Spieler)
        session["aktiver"] = 0
        # Punkte-Array für jeden Spieler mit 0 initialisieren
        session["gesamt"] = [0] * len(spieler)
        
        # Weiterleitung zur Würfelseite
        return redirect("/dice")
    
    # HTML-Seite zum Eintragen der Spielernamen anzeigen
    return render_template("spielernamen.html", anzahl=session["anzahl"])

# Seite mit den Würfeln anzeigen
@app.route("/dice")
def dice():
    # Spielernamen und aktiven Spieler aus Session holen
    spieler = session.get("spieler", [])
    aktiver = session.get("aktiver", 0)

    # HTML-Seite mit Würfeln anzeigen und aktuellen Spieler übergeben
    return render_template("dice.html", spieler=spieler, aktiver=aktiver)

# API-Endpunkt zum Würfeln (wird von JavaScript aufgerufen)
@app.route("/roll")
def roll():
    # Zwei Zufallszahlen (1–6) generieren für die Würfel
    würfel1 = random.randint(1, 6)
    würfel2 = random.randint(1, 6)

    # Summe berechnen
    summe = würfel1 + würfel2

    # Überprüfen, ob ein Doppelwurf vorliegt
    doppel = würfel1 == würfel2

    # Aktiven Spieler aus der Session holen
    aktiver = session["aktiver"]

    # Punkte zum Gesamtpunktestand des aktiven Spielers hinzufügen
    session["gesamt"][aktiver] += summe

    # Wenn kein Doppel, nächster Spieler ist dran
    if not doppel:
        session["aktiver"] = (aktiver + 1) % len(session["spieler"])

    # JSON-Daten mit Wurfergebnissen und Spielerinformationen zurückgeben
    return {
        "w1": würfel1,
        "w2": würfel2,
        "summe": summe,
        "doppel": doppel,
        "spieler": session["spieler"][session["aktiver"]],
        "gesamt": session["gesamt"]
    }

# Hauptprogramm starten, wenn direkt ausgeführt
if __name__ == "__main__":
    app.run(debug=True)

from contextlib import contextmanager
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import random
import mysql.connector

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "saufmonopoly"),
}

@contextmanager
def db_cursor(dictionary=False):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield cursor
        conn.commit()
    finally:
        cursor.close()
        conn.close()

FELD_ANZAHL = 40

def reset_besitzer():
    with db_cursor() as cursor:
        cursor.execute("UPDATE spielfelder SET besitzer=NULL")

def lade_felder_infos():
    with db_cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM spielfelder ORDER BY feld_id ASC")
        felder = cursor.fetchall()
        print("[DEBUG] Felder aus DB geladen:")
        for f in felder:
            print(f"  feld_id={f['feld_id']}, name={f['name']}, typ={f['typ']}, besitzer={f['besitzer']}")
        return felder

def get_besitz_uebersicht():
    felder_infos = lade_felder_infos()
    besitz = {}
    for feld in felder_infos:
        if feld.get("besitzer"):
            besitz.setdefault(feld["besitzer"], []).append(feld)
    return besitz

def parse_schlucke(text):
    import re
    if not text:
        return 0
    match = re.search(r"(\d+)", str(text))
    return int(match.group(1)) if match else 0

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session.clear()
        anzahl = int(request.form["anzahl"])
        session["anzahl"] = anzahl
        return redirect(url_for("namen"))
    return render_template("index.html")

@app.route("/namen", methods=["GET", "POST"])
def namen():
    if request.method == "POST":
        spieler = []
        for i in range(1, session["anzahl"] + 1):
            spieler.append(request.form[f"spieler{i}"])
        session["spieler"] = spieler
        session["positionen"] = [0 for _ in range(len(spieler))]
        session["aktiver"] = 0
        session["konto"] = [0] * len(spieler)
        session["gesamt"] = [0] * len(spieler)
        session["pending_popup"] = None
        session["warte_auf_wurf"] = True
        return redirect(url_for("spiel"))
    return render_template("spielernamen.html", anzahl=session["anzahl"])

@app.route("/board", methods=["GET", "POST"])
def spiel():
    felder_infos = lade_felder_infos()
    print(f"[DEBUG] feld_infos-Liste Länge: {len(felder_infos)}")
    aktiver = session.get("aktiver", 0)
    pos_liste = session.get("positionen", [])
    pending_popup = session.get("pending_popup")
    warte_auf_wurf = session.get("warte_auf_wurf", True)
    wurf = session.get("wurf")

    if warte_auf_wurf:
        if request.method == "POST":
            würfel1 = random.randint(1, 6)
            würfel2 = random.randint(1, 6)
            summe = würfel1 + würfel2
            print(
                f"[DEBUG] {session['spieler'][aktiver]} würfelt {würfel1} + {würfel2} = {summe}"
            )
            session["wurf"] = [würfel1, würfel2]
            session["warte_auf_wurf"] = False
            return redirect("/board")
        return render_template(
            "board.html",
            spieler=session.get("spieler", []),
            aktiver=aktiver,
            zeige_wer_ist_dran=True,
            felder_infos=felder_infos,
            positionen=pos_liste,
            konto=session.get("konto", []),
            besitz=get_besitz_uebersicht(),
            felder=list(range(40)),
            wurf=None,
            feldinfo=None,
            popup_spieler=None,
            zeige_feldinfo=False,
            zeige_wurf_popup=False
        )

    if not warte_auf_wurf and not pending_popup:
        if request.method == "POST":
            wurf = session.get("wurf")
            summe = wurf[0] + wurf[1]
            aktuelle_pos = session["positionen"][aktiver]
            neue_pos = (aktuelle_pos + summe) % len(felder_infos)
            print(
                f"[DEBUG] {session['spieler'][aktiver]} zieht {summe} Felder von {aktuelle_pos} auf {neue_pos}"
            )
            session["positionen"][aktiver] = neue_pos
            session["gesamt"][aktiver] += summe
            session["pending_popup"] = {
                "spieler": aktiver,
                "feld": neue_pos,
                "wurf": wurf
            }
            session["wurf"] = None
            session["warte_auf_wurf"] = False
            return redirect("/board")
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
            zeige_wurf_popup=True
        )

    if pending_popup:
        popup_spieler = pending_popup["spieler"]
        popup_feldinfo = felder_infos[pending_popup["feld"]]
        print(f"[DEBUG] pending_popup: {pending_popup}")
        print(f"[DEBUG] popup_feldinfo: feld_id={popup_feldinfo['feld_id']}, name={popup_feldinfo['name']}, typ={popup_feldinfo['typ']}")
        popup_wurf = pending_popup["wurf"]
    else:
        popup_feldinfo = None
        popup_spieler = None
        popup_wurf = None

    return render_template(
        "board.html",
        felder=list(range(40)),
        spieler=session.get("spieler", []),
        positionen=session.get("positionen", []),
        aktiver=aktiver,
        wurf=popup_wurf,
        feldinfo=popup_feldinfo,
        popup_spieler=popup_spieler,
        zeige_feldinfo=bool(pending_popup),
        felder_infos=felder_infos,
        konto=session.get("konto", []),
        besitz=get_besitz_uebersicht(),
        zeige_wer_ist_dran=False,
        zeige_wurf_popup=False
    )

@app.route("/feld_aktion", methods=["POST"])
def feld_aktion():
    data = request.get_json()
    print(f"[DEBUG] feld_aktion POST data: {data}")
    aktion = data.get("aktion")
    feld_id = int(data.get("feld"))
    print(f"[DEBUG] feld_aktion: aktion={aktion}, feld_id={feld_id}")
    pending_popup = session.get("pending_popup")
    print(f"[DEBUG] session['pending_popup']: {pending_popup}")
    if not pending_popup:
        return jsonify({"ok": False, "msg": "Kein aktiver Zug!"})

    aktiver = pending_popup["spieler"]
    felder_infos = lade_felder_infos()
    print(f"[DEBUG] Suche Feld mit feld_id={feld_id} in felder_infos")
    feld = next((f for f in felder_infos if int(f["feld_id"]) == feld_id), None)
    if not feld:
        print(f"[DEBUG] Feld mit feld_id={feld_id} NICHT gefunden!")
        return jsonify({"ok": False, "msg": f"Feld mit ID {feld_id} nicht gefunden."})
    print(f"[DEBUG] Feld gefunden: feld_id={feld['feld_id']}, name={feld['name']}, typ={feld['typ']}, besitzer={feld['besitzer']}")

    def is_strassenfeld(feldtyp):
        print(f"[DEBUG] feldtyp repr: {repr(feldtyp)}")
        typ_str = str(feldtyp).strip().lower().replace("ß", "ss")
        print(f"[DEBUG] feldtyp normalisiert: {typ_str}")
        return typ_str == "strasse"

    if aktion == "kaufen":
        spielername = session["spieler"][aktiver]
        print(
            f"[DEBUG] {spielername} möchte Feld {feld_id} ({feld['name']}) vom Typ {feld['typ']} kaufen"
        )
        if not is_strassenfeld(feld["typ"]):
            print(f"[DEBUG] Kauf abgelehnt - kein Straßenfeld (typ war: {repr(feld['typ'])})")
            return jsonify({"ok": False, "msg": f"Nur Straßen können gekauft werden. (typ: {repr(feld['typ'])})"})
        with db_cursor() as cursor:
            print(f"[DEBUG] UPDATE spielfelder SET besitzer={spielername} WHERE feld_id={feld_id}")
            cursor.execute(
                "UPDATE spielfelder SET besitzer=%s WHERE feld_id=%s",
                (spielername, feld_id),
            )
        schlucke = parse_schlucke(feld.get("kaufpreis"))
        print(f"[DEBUG] parse_schlucke({feld.get('kaufpreis')}) = {schlucke}")
        session["konto"][aktiver] += schlucke
        session["pending_popup"] = None
        session["aktiver"] = (aktiver + 1) % len(session["spieler"])
        session["warte_auf_wurf"] = True
        return jsonify({"ok": True})

    if aktion == "miete":
        besitzer_name = feld.get("besitzer")
        print(f"[DEBUG] Miete zahlen an: {besitzer_name}")
        if besitzer_name:
            schlucke = parse_schlucke(feld.get("miete"))
            print(f"[DEBUG] parse_schlucke({feld.get('miete')}) = {schlucke}")
            session["konto"][aktiver] += schlucke
        session["pending_popup"] = None
        session["aktiver"] = (aktiver + 1) % len(session["spieler"])
        session["warte_auf_wurf"] = True
        return jsonify({"ok": True})

    if aktion == "skip":
        print("[DEBUG] Aktion skip")
        session["pending_popup"] = None
        session["aktiver"] = (aktiver + 1) % len(session["spieler"])
        session["warte_auf_wurf"] = True
        return jsonify({"ok": True})

    print("[DEBUG] Unbekannte Aktion")

    return jsonify({"ok": False})  # Unbekannte Aktion

if __name__ == "__main__":
    reset_besitzer()  # Setzt alle Felder auf frei beim Start
    app.run(debug=True)  # Startet die Flask-App im Debug-Modus
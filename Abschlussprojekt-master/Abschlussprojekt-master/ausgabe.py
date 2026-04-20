import mysql.connector
from tabulate import tabulate
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')  #für ß, ü, ö, ä


# Datenbankverbindung herstellen
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="monopoly_trinkspiel"
)

cursor = conn.cursor(dictionary=True)

# Alle Spielfelder abfragen
cursor.execute("SELECT * FROM spielfelder ORDER BY feld_id ASC")
felder = cursor.fetchall()




feldname = "Biergasse 1"
spieler = "Lorenz"

cursor.execute(
    "UPDATE spielfelder SET besitzer = %s WHERE name = %s",
    (spieler, feldname)
)
conn.commit()  # wichtig: Änderungen speichern





# Ausgabe als Tabelle
felder_liste = []
for feld in felder:
    felder_liste.append([
        feld["feld_id"],
        feld["name"],
        feld["typ"],
        feld["kaufpreis"] or "-",
        feld["miete"] or "-",
        feld["alkohol_typ"],
        feld["alkohol_menge"],
        feld["zusatz_regel"] or "-",
        feld.get("besitzer") or "Frei"
    ])

print(tabulate(
    felder_liste,
    headers=["ID", "Name", "Typ", "Kaufpreis", "Miete", "Alkohol", "Menge", "Zusatzregel"],
    tablefmt="grid"
))

# Verbindung schließen
cursor.close()
conn.close()

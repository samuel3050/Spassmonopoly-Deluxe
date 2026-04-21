import io
import sys

import mysql.connector
from tabulate import tabulate

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="spassmonopoly",
)

cursor = conn.cursor(dictionary=True)
cursor.execute("SELECT * FROM spielfelder ORDER BY feld_id ASC")
felder = cursor.fetchall()

felder_liste = []
for feld in felder:
    felder_liste.append(
        [
            feld["feld_id"],
            feld["name"],
            feld["typ"],
            feld["kaufpreis"] or "-",
            feld["miete"] or "-",
            feld["alkohol_typ"],
            feld["alkohol_menge"],
            feld["zusatz_regel"] or "-",
            feld.get("besitzer") or "Frei",
        ]
    )

print(
    tabulate(
        felder_liste,
        headers=["ID", "Name", "Typ", "Preis", "Abgabe", "Bonus", "Wert", "Regel", "Besitzer"],
        tablefmt="grid",
    )
)

cursor.close()
conn.close()

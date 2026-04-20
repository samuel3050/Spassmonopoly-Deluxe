from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    print(f"Benutzername: {username}")
    print(f"Passwort: {password}")
    return f"Login empfangen für Benutzer: {username}"

if __name__ == "__main__":
    app.run(debug=True)

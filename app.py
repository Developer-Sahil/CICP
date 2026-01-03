from flask import Flask, render_template, request, redirect, url_for, session
from auth.auth import login_required
from auth.firebase_auth import firebase_bp
from database.firestore import init_firestore
from firebase_admin import firestore
import config

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.permanent_session_lifetime = 60 * 60 * 24 * 7

fs = init_firestore()

app.register_blueprint(firebase_bp)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/profile")
@login_required
def profile():
    uid = session["user_id"]

    user = fs.collection("users").document(uid).get().to_dict()

    complaints = [
        c.to_dict()
        for c in fs.collection("complaints")
        .where("user_id", "==", uid)
        .stream()
    ]

    return render_template("profile.html", user=user, complaints=complaints)

@app.route("/submit", methods=["POST"])
@login_required
def submit():
    text = request.form["raw_text"]

    fs.collection("complaints").add({
        "user_id": session["user_id"],
        "text": text,
        "timestamp": firestore.SERVER_TIMESTAMP,
        "upvotes": 0
    })

    return redirect(url_for("success"))

@app.route("/success")
def success():
    return render_template("success.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=config.DEBUG)

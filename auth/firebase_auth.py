from flask import Blueprint, request, jsonify, session
from firebase_admin import auth
from database.firestore import init_firestore
import config

firebase_bp = Blueprint("firebase_bp", __name__)
fs = init_firestore()

@firebase_bp.route("/firebase-login", methods=["POST"])
def firebase_login():
    id_token = request.json.get("idToken")

    try:
        decoded = auth.verify_id_token(id_token)

        uid = decoded["uid"]
        email = decoded["email"]
        name = decoded.get("name", email.split("@")[0])

        if not email.endswith(f"@{config.ALLOWED_GOOGLE_DOMAIN}"):
            return jsonify({"status": "error"}), 403

        user_ref = fs.collection("users").document(uid)
        if not user_ref.get().exists:
            user_ref.set({
                "uid": uid,
                "email": email,
                "name": name,
                "is_google": True,
            })

        session["logged_in"] = True
        session["user_id"] = uid
        session["email"] = email
        session["name"] = name
        session["is_google"] = True

        return jsonify({"status": "success", "redirect": "/profile"})

    except Exception as e:
        print("Firebase login error:", e)
        return jsonify({"status": "error"}), 401

# auth/firebase_auth.py
from flask import Blueprint, request, jsonify, session
from firebase_admin import credentials, auth, initialize_app
import firebase_admin
import os
from database.models import db, User
from auth.auth import login_user
import config

firebase_bp = Blueprint("firebase_bp", __name__)

service_account = {
    "type": "service_account",
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n") if os.getenv("FIREBASE_PRIVATE_KEY") else None,
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
}


if not firebase_admin._apps:
    cred = credentials.Certificate(service_account)
    initialize_app(cred)

@firebase_bp.route("/firebase-login", methods=["POST"])
def firebase_login():
    id_token = request.json.get("idToken")

    try:
        decoded = auth.verify_id_token(id_token)
        email = decoded.get("email")
        name = decoded.get("name") or email.split("@")[0]

        # Domain Restriction
        if not email.endswith(f"@{config.ALLOWED_GOOGLE_DOMAIN}"):
            return jsonify({"status": "error", "redirect": "/login", "msg": "Invalid Domain"}), 403

        # Check if user exists
        user = User.query.filter_by(email=email).first()

        # Create if not exists
        if not user:
            user = User(
                name=name,
                email=email,
                is_google=True
            )
            db.session.add(user)
            db.session.commit()

        # 🔥 LOGIN
        login_user(user)
        session["user_id"] = user.id
        session["email"] = email

        print("USER LOGGED IN:", user.id)
        return jsonify({"status": "success", "redirect": "/profile"})

    except Exception as e:
        print("FIREBASE ERROR:", e)
        return jsonify({"status": "error", "redirect": "/login"}), 401

from flask import Blueprint, request, jsonify
from firebase_admin import credentials, auth, initialize_app
import firebase_admin
import os

from database.models import db, User
from auth.auth import login_user
import config

firebase_bp = Blueprint("firebase_bp", __name__)

# 📍 Path to service account JSON
SERVICE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "firebase_service_account.json")

# 🚀 Initialize Firebase Admin
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_FILE)
    firebase_admin.initialize_app(cred, {
        "projectId": config.FIREBASE_PROJECT_ID
    })

@firebase_bp.route("/firebase-login", methods=["POST"])
def firebase_login():
    id_token = request.json.get("idToken")

    try:
        decoded = auth.verify_id_token(id_token)
        email = decoded.get("email")

        print("🔍 Login attempt:", email)

        # Domain check
        domain = config.ALLOWED_GOOGLE_DOMAIN.lower()
        if not email.lower().endswith(f"@{domain}"):
            return jsonify({
                "status": "error",
                "message": f"Only @{domain} emails allowed"
            }), 403

        # Get or create user
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                name=email.split("@")[0],
                email=email,
                is_google=True
            )
            db.session.add(user)
            db.session.commit()

        login_user(user)
        return jsonify({"status": "success", "redirect": "/profile"})


    except Exception as e:
        print("🔥 Backend Firebase Error:", e)
        return jsonify({
            "status": "error",
            "message": "Authentication failed"
        }), 401

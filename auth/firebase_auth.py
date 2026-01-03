# auth/firebase_auth.py
from flask import Blueprint, request, jsonify, session
from firebase_admin import auth
import firebase_admin
import os
from database.firebase_models import User
from auth.auth import login_user
import config

firebase_bp = Blueprint("firebase_bp", __name__)

# Firebase is already initialized in firebase_models.py
# No need to initialize again here

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
        user = User.get_by_email(email)

        # Create if not exists
        if not user:
            user_data = {
                'name': name,
                'email': email,
                'is_google': True,
                'student_id': email.split('@')[0],  # Use email prefix as student_id
                'password_hash': '',  # Empty for Google users
            }
            user = User.create(user_data)

        # 🔥 LOGIN
        login_user(user)
        session["user_id"] = user['id']
        session["email"] = email

        print("USER LOGGED IN:", user['id'])
        return jsonify({"status": "success", "redirect": "/profile"})

    except Exception as e:
        print("FIREBASE ERROR:", e)
        return jsonify({"status": "error", "redirect": "/login"}), 401
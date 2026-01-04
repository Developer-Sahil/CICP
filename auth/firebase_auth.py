# ============================================================================
# PART 2: Replace auth/firebase_auth.py with this FIXED version
# ============================================================================

from flask import Blueprint, request, jsonify, session
from firebase_admin import auth
import firebase_admin
import os
from database.firebase_models import User
from auth.auth import login_user
import config
import logging

logger = logging.getLogger(__name__)

firebase_bp = Blueprint("firebase_bp", __name__)

@firebase_bp.route("/firebase-login", methods=["POST"])
def firebase_login():
    """Handle Google Sign-In via Firebase"""
    try:
        data = request.get_json()
        id_token = data.get("idToken")
        
        if not id_token:
            logger.error("No ID token provided")
            return jsonify({
                "status": "error",
                "redirect": "/login",
                "msg": "No authentication token provided"
            }), 400
        
        # Verify the ID token
        try:
            decoded = auth.verify_id_token(id_token)
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return jsonify({
                "status": "error",
                "redirect": "/login",
                "msg": "Invalid authentication token"
            }), 401
        
        email = decoded.get("email")
        name = decoded.get("name") or email.split("@")[0]
        uid = decoded.get("uid")
        
        logger.info(f"Google login attempt for: {email}")
        
        # Domain Restriction (optional - comment out to allow all domains)
        if hasattr(config, 'ALLOWED_GOOGLE_DOMAIN') and config.ALLOWED_GOOGLE_DOMAIN:
            if not email.endswith(f"@{config.ALLOWED_GOOGLE_DOMAIN}"):
                logger.warning(f"Domain restriction: {email} not in {config.ALLOWED_GOOGLE_DOMAIN}")
                return jsonify({
                    "status": "error",
                    "redirect": "/login",
                    "msg": f"Please use your {config.ALLOWED_GOOGLE_DOMAIN} email"
                }), 403
        
        # Check if user exists in Firestore
        user = User.get_by_email(email)
        
        if not user:
            # Create new user
            logger.info(f"Creating new user for: {email}")
            user_data = {
                'name': name,
                'email': email,
                'is_google': True,
                'student_id': email.split('@')[0].upper(),  # Use email prefix as student_id
                'password_hash': '',  # Empty for Google users
                'is_admin': False,
                'is_active': True,
                'email_verified': True  # Google emails are pre-verified
            }
            
            user = User.create(user_data)
            
            if not user:
                logger.error(f"Failed to create user in Firestore: {email}")
                return jsonify({
                    "status": "error",
                    "redirect": "/login",
                    "msg": "Failed to create account"
                }), 500
            
            logger.info(f"✓ New user created: {email}")
        else:
            logger.info(f"✓ Existing user found: {email}")
        
        # Update last login
        User.update_last_login(user['id'])
        
        # Login the user - THIS IS THE CRITICAL PART
        login_user(user)
        
        # Verify session was set
        if not session.get("logged_in"):
            logger.error("Session not set after login_user()")
            return jsonify({
                "status": "error",
                "redirect": "/login",
                "msg": "Session initialization failed"
            }), 500
        
        logger.info(f"✓ User logged in successfully: {email}")
        logger.info(f"Session data: logged_in={session.get('logged_in')}, user_id={session.get('user_id')}")
        
        return jsonify({
            "status": "success",
            "redirect": "/profile"
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in firebase_login: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "redirect": "/login",
            "msg": "An error occurred during login"
        }), 500
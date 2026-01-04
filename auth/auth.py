# ============================================================================
# PART 1: Replace auth/auth.py with this FIXED version
# ============================================================================

"""
Authentication module for student login system
Handles user registration, login, password hashing, and session management
"""

from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import session, redirect, url_for, flash, request
import re
from datetime import datetime, timedelta


def hash_password(password):
    """Hash a password for storing."""
    return generate_password_hash(password, method='pbkdf2:sha256')


def verify_password(password_hash, password):
    """Verify a stored password against one provided by user."""
    return check_password_hash(password_hash, password)


def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_student_id(student_id):
    """Validate student ID format."""
    pattern = r'^[A-Za-z0-9]{6,15}$'
    return re.match(pattern, student_id) is not None


def validate_password(password):
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    
    return True, None


def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Check if user is logged in
        if not session.get("logged_in") or not session.get("user_id"):
            flash("Please login to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    """Decorator to require admin privileges for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        
        if not session.get('is_admin', False):
            flash('Admin access required.', 'danger')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Get current logged in user from session."""
    if not session.get("logged_in"):
        return None
    return session.get("user")


def login_user(user):
    """
    Log in a user by setting session data.
    
    Args:
        user: User dict from Firestore with 'id', 'email', 'name', etc.
    """
    # Clear any existing session data first
    session.clear()
    
    # Set session data
    session["user_id"] = user.get("id")
    session["email"] = user.get("email")
    session["name"] = user.get("name")
    session["student_id"] = user.get("student_id")
    session["is_google"] = user.get("is_google", False)
    session["is_admin"] = user.get("is_admin", False)
    session["logged_in"] = True
    session.permanent = True
    
    # Store full user object for easy access
    session["user"] = {
        "id": user.get("id"),
        "email": user.get("email"),
        "name": user.get("name"),
        "student_id": user.get("student_id"),
        "is_google": user.get("is_google", False),
        "is_admin": user.get("is_admin", False)
    }
    
    print(f"✓ User logged in successfully: {user.get('email')}")


def logout_user():
    """Log out the current user by clearing session."""
    session.clear()


def update_last_login(user):
    """Update user's last login timestamp."""
    from database.firebase_models import User
    User.update_last_login(user.get('id'))


def sanitize_input(text):
    """Sanitize user input to prevent XSS."""
    if not text:
        return ""
    
    dangerous_chars = ['<', '>', '"', "'", '&']
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    return text.strip()


def check_rate_limit(user_id, action, limit=5, window_minutes=15):
    """
    Check if user has exceeded rate limit for an action.
    Simple in-memory implementation.
    """
    from flask import current_app
    
    if not hasattr(current_app, 'rate_limits'):
        current_app.rate_limits = {}
    
    key = f"{user_id}:{action}"
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=window_minutes)
    
    if key not in current_app.rate_limits:
        current_app.rate_limits[key] = []
    
    # Remove old attempts
    current_app.rate_limits[key] = [
        timestamp for timestamp in current_app.rate_limits[key]
        if timestamp > cutoff
    ]
    
    attempts = len(current_app.rate_limits[key])
    
    if attempts >= limit:
        return False, 0
    
    # Record this attempt
    current_app.rate_limits[key].append(now)
    
    return True, limit - attempts - 1
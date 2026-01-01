"""
Authentication module for student login system
Handles user registration, login, password hashing, and session management
"""

from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import session, redirect, url_for, flash
import re
from datetime import datetime, timedelta


def hash_password(password):
    """
    Hash a password for storing.
    
    Args:
        password (str): Plain text password
        
    Returns:
        str: Hashed password
    """
    return generate_password_hash(password, method='pbkdf2:sha256')


def verify_password(password_hash, password):
    """
    Verify a stored password against one provided by user.
    
    Args:
        password_hash (str): Stored password hash
        password (str): User-provided password
        
    Returns:
        bool: True if password matches
    """
    return check_password_hash(password_hash, password)


def validate_email(email):
    """
    Validate email format.
    
    Args:
        email (str): Email address to validate
        
    Returns:
        bool: True if valid email format
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_student_id(student_id):
    """
    Validate student ID format.
    
    Args:
        student_id (str): Student ID to validate
        
    Returns:
        bool: True if valid format
    """
    # Example: Alphanumeric, 6-15 characters
    pattern = r'^[A-Za-z0-9]{6,15}$'
    return re.match(pattern, student_id) is not None


def validate_password(password):
    """
    Validate password strength.
    
    Args:
        password (str): Password to validate
        
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    
    return True, None


from functools import wraps
from flask import session, redirect, url_for, flash

# auth/auth.py
from functools import wraps
from flask import session, redirect, url_for, flash, request

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # check normal login
        if session.get("logged_in") and session.get("user_id"):
            return f(*args, **kwargs)

        # check google login session
        if session.get("firebase_uid") and session.get("user_id"):
            return f(*args, **kwargs)

        # if next page was intended, keep it
        next_url = request.path
        flash("Please login to continue.", "warning")
        return redirect(url_for("login", next=next_url))
    return wrapper


def admin_required(f):
    """
    Decorator to require admin privileges for routes.
    
    Usage:
        @app.route('/admin')
        @admin_required
        def admin_route():
            ...
    """
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


from flask import session

def get_current_user():
    if not session.get("logged_in"):
        return None
    return session.get("user")



from flask import session

# auth/auth.py
from flask import session

def login_user(user):
    session["user"] = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "student_id": getattr(user, "student_id", None),
        "is_google": getattr(user, "is_google", False)
    }
    session["logged_in"] = True        # 💥 THIS WAS MISSING
    session["user_id"] = user.id       # Optional: match your other checks
    session.permanent = True



def logout_user():
    """
    Log out the current user by clearing session.
    """
    session.clear()


def update_last_login(user):
    """
    Update user's last login timestamp.
    
    Args:
        user: User model instance
    """
    from database.models import db
    user.last_login = datetime.utcnow()
    db.session.commit()


def generate_reset_token():
    """
    Generate a password reset token.
    
    Returns:
        str: Reset token
    """
    import secrets
    return secrets.token_urlsafe(32)


def verify_reset_token(user, token, expiry_hours=24):
    """
    Verify a password reset token.
    
    Args:
        user: User model instance
        token (str): Reset token to verify
        expiry_hours (int): Token expiry time in hours
        
    Returns:
        bool: True if token is valid and not expired
    """
    if not user.reset_token or user.reset_token != token:
        return False
    
    if not user.reset_token_expiry:
        return False
    
    if datetime.utcnow() > user.reset_token_expiry:
        return False
    
    return True


def create_reset_token(user):
    """
    Create and store a password reset token for user.
    
    Args:
        user: User model instance
        
    Returns:
        str: Reset token
    """
    from database.models import db
    
    token = generate_reset_token()
    user.reset_token = token
    user.reset_token_expiry = datetime.utcnow() + timedelta(hours=24)
    db.session.commit()
    
    return token


def clear_reset_token(user):
    """
    Clear password reset token after use.
    
    Args:
        user: User model instance
    """
    from database.models import db
    
    user.reset_token = None
    user.reset_token_expiry = None
    db.session.commit()


def sanitize_input(text):
    """
    Sanitize user input to prevent XSS.
    
    Args:
        text (str): User input
        
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
    
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&']
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    return text.strip()


def check_rate_limit(user_id, action, limit=5, window_minutes=15):
    """
    Check if user has exceeded rate limit for an action.
    
    Args:
        user_id: User ID
        action (str): Action name (e.g., 'login_attempt')
        limit (int): Maximum attempts allowed
        window_minutes (int): Time window in minutes
        
    Returns:
        tuple: (allowed: bool, remaining: int)
    """
    # Simple in-memory rate limiting
    # In production, use Redis or database
    from flask import current_app
    
    if not hasattr(current_app, 'rate_limits'):
        current_app.rate_limits = {}
    
    key = f"{user_id}:{action}"
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=window_minutes)
    
    # Get or create attempt list
    if key not in current_app.rate_limits:
        current_app.rate_limits[key] = []
    
    # Remove old attempts
    current_app.rate_limits[key] = [
        timestamp for timestamp in current_app.rate_limits[key]
        if timestamp > cutoff
    ]
    
    # Check limit
    attempts = len(current_app.rate_limits[key])
    
    if attempts >= limit:
        return False, 0
    
    # Record this attempt
    current_app.rate_limits[key].append(now)
    
    return True, limit - attempts - 1
from functools import wraps
from flask import session, redirect, url_for

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated

def login_user(uid, email, name, is_google=True):
    session["logged_in"] = True
    session["user_id"] = uid
    session["email"] = email
    session["name"] = name
    session["is_google"] = is_google
    session.permanent = True

def logout_user():
    session.clear()

def get_current_user():
    if not session.get("logged_in"):
        return None
    return {
        "uid": session["user_id"],
        "email": session["email"],
        "name": session["name"],
        "is_google": session["is_google"]
    }

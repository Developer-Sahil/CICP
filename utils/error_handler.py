import logging
from functools import wraps
from flask import jsonify, render_template, request

logger = logging.getLogger(__name__)

def handle_errors(return_json=False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)

            except Exception as e:
                logger.exception(f"Error in {func.__name__}: {e}")

                if return_json or request.is_json:
                    return jsonify({
                        "success": False,
                        "error": "Internal server error"
                    }), 500

                return render_template(
                    "error.html",
                    error_code=500,
                    error_message="Something went wrong. Please try again."
                ), 500
        return wrapper
    return decorator

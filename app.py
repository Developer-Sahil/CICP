from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from datetime import datetime, timedelta
import logging
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


# ========== IMPORT CONFIG FIRST ==========
import config

# ========== IMPORT DATABASE MODELS ==========
from database.firebase_models import User, Complaint, IssueCluster, Category, initialize_categories

# Helper function to add get_all to User class
def _get_all_users():
    """Get all users - helper for health check"""
    try:
        from firebase_admin import firestore
        db = firestore.client()
        users = []
        for doc in db.collection('users').stream():
            data = doc.to_dict()
            data['id'] = doc.id
            users.append(data)
        return users
    except:
        return []

User.get_all = staticmethod(_get_all_users)

# ========== IMPORT AI MODULES ==========
from ai.rewrite import rewrite_complaint
from ai.classify import classify_category
from ai.severity import detect_severity
from ai.embed import generate_embedding
from ai.cluster import assign_cluster, update_clusters

# ========== IMPORT UTILITIES ==========
from utils.firebase_helpers import get_dashboard_stats, get_recent_complaints
from utils.error_handler import handle_errors

# ========== IMPORT AUTH ==========
from auth.auth import (
    login_required, admin_required, get_current_user,
    login_user, logout_user, update_last_login,
    validate_email, validate_student_id, validate_password,
    sanitize_input, check_rate_limit
)

# ========== CREATE FLASK APP ==========
app = Flask(__name__)
app.config.from_object(config)

#========== CSRF PROTECTION ============
csrf = CSRFProtect(app)

# ========== RATE LIMITER SETUP ============
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[config.API_RATE_LIMIT_DEFAULT],
    storage_uri=config.RATELIMIT_STORAGE_URL,
    strategy=config.RATELIMIT_STRATEGY,
    headers_enabled=config.RATELIMIT_HEADERS_ENABLED
)

limiter.exempt(lambda: request.path.startswith('/static/'))

print(f"✓ Rate limiter initialized")
print(f"✓ Login limit: {config.AUTH_RATE_LIMIT_LOGIN}")
print(f"✓ Register limit: {config.AUTH_RATE_LIMIT_REGISTER}")

# ========== SESSION CONFIGURATION ==========
app.secret_key = config.SECRET_KEY
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Session cookie settings
app.config['SESSION_COOKIE_NAME'] = 'cicp_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
app.config['SESSION_COOKIE_SECURE'] = True     
app.config['SESSION_COOKIE_DOMAIN'] = None 

print(f"✓ Secret key configured: {app.secret_key[:10]}...")
print(f"✓ Session lifetime: {app.config['PERMANENT_SESSION_LIFETIME']}")
print(f"✓ CSRF Protection enabled")

# ========== JINJA GLOBALS ==========
app.jinja_env.globals.update(
    FIREBASE_API_KEY=config.FIREBASE_API_KEY,
    FIREBASE_AUTH_DOMAIN=config.FIREBASE_AUTH_DOMAIN,
    FIREBASE_PROJECT_ID=config.FIREBASE_PROJECT_ID,
    FIREBASE_STORAGE_BUCKET=getattr(config, "FIREBASE_STORAGE_BUCKET", ""),
    FIREBASE_MSG_SENDER_ID=getattr(config, "FIREBASE_MSG_SENDER_ID", ""),
    FIREBASE_APP_ID=getattr(config, "FIREBASE_APP_ID", "")
)

# Helper functions for templates
app.jinja_env.globals.update({
    'min': min,
    'max': max,
    'abs': abs,
    'len': len
})

# ========== REGISTER BLUEPRINTS ==========
from auth.firebase_auth import firebase_bp
limiter.limit(config.AUTH_RATE_LIMIT_FIREBASE)(firebase_bp)
app.register_blueprint(firebase_bp)
csrf.exempt(firebase_bp)
print(f"✓ Firebase blueprint registered with rate limit: {config.AUTH_RATE_LIMIT_FIREBASE}")

# ========== CONFIGURE LOGGING ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== INITIALIZE CATEGORIES ==========
try:
    initialize_categories()
    logger.info("Categories initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize categories: {e}")

# ========== CONTEXT PROCESSOR ==========
@app.context_processor
def inject_user():
    """Make current user available in all templates"""
    return dict(current_user=get_current_user())

# ========== ERROR HANDLERS ==========
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error_code=404, error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {str(error)}")
    return render_template('error.html', error_code=500, error_message="Internal server error"), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded errors"""
    logger.warning(f"Rate limit exceeded: {request.remote_addr} on {request.path}")
    
    # Check if it's an API request (JSON)
    if request.path.startswith('/api/') or request.path.startswith('/complaint/'):
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded. Please try again later.',
            'retry_after': e.description
        }), 429
    
    # For regular pages, show error template
    return render_template('error.html', 
                         error_code=429, 
                         error_message="Too many requests. Please slow down and try again in a few minutes."), 429

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    """Handle CSRF validation errors gracefully"""
    logger.warning(f"CSRF error: {e.description} from {request.remote_addr}")
    
    # For API endpoints, return JSON
    if request.path.startswith('/api/') or request.accept_mimetypes.accept_json:
        return jsonify({
            'success': False,
            'error': 'CSRF validation failed. Please refresh the page and try again.'
        }), 400
    
    # For regular pages, show user-friendly error
    return render_template('error.html', 
                         error_code=400, 
                         error_message="Security validation failed. Please refresh the page and try again."), 400

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    return render_template('error.html', error_code=500, error_message="An unexpected error occurred"), 500


# ============================================================================
# PUBLIC ROUTES
# ============================================================================
@app.route('/')
@handle_errors()
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        return "Error loading page", 500

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit(config.AUTH_RATE_LIMIT_REGISTER, methods=['POST'])
def register():
    """User registration page with rate limiting"""
    if get_current_user():
        return redirect(url_for('profile'))
    
    if request.method == 'GET':
        return render_template('register.html')
    
    try:
        # Get form data
        name = sanitize_input(request.form.get('name', '').strip())
        student_id = sanitize_input(request.form.get('student_id', '').strip().upper())
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        department = sanitize_input(request.form.get('department', '').strip())
        year = request.form.get('year', type=int)
        hostel = sanitize_input(request.form.get('hostel', '').strip())
        room_number = sanitize_input(request.form.get('room_number', '').strip())
        phone = sanitize_input(request.form.get('phone', '').strip())
        
        # Validation
        if not all([name, student_id, email, password, confirm_password]):
            logger.warning("Registration attempt with missing required fields")
            return render_template('register.html', error="Please fill in all required fields")
        
        if password != confirm_password:
            logger.warning("Registration attempt with mismatched passwords")
            return render_template('register.html', error="Passwords do not match")
        
        if not validate_email(email):
            logger.warning(f"Registration attempt with invalid email: {email}")
            return render_template('register.html', error="Invalid email address")
        
        if not validate_student_id(student_id):
            logger.warning(f"Registration attempt with invalid student ID: {student_id}")
            return render_template('register.html', error="Invalid student ID format (6-15 alphanumeric characters)")
        
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            logger.warning(f"Registration attempt with weak password")
            return render_template('register.html', error=error_msg)
        
        # Check if user exists
        existing_user = User.get_by_email(email)
        if existing_user:
            logger.warning(f"Registration attempt with existing email: {email}")
            return render_template('register.html', error="An account with this email already exists")
        
        existing_student = User.get_by_student_id(student_id)
        if existing_student:
            logger.warning(f"Registration attempt with existing student ID: {student_id}")
            return render_template('register.html', error="An account with this student ID already exists")
        
        # Create user
        from werkzeug.security import generate_password_hash
        user_data = {
            'name': name,
            'student_id': student_id,
            'email': email,
            'password_hash': generate_password_hash(password, method='pbkdf2:sha256:600000'),
            'department': department if department else None,
            'year': year if year else None,
            'hostel': hostel if hostel else None,
            'room_number': room_number if room_number else None,
            'phone': phone if phone else None,
            'is_google': False,
            'is_admin': False,
            'is_active': True,
            'email_verified': False
        }
        
        user = User.create(user_data)
        if not user:
            logger.error(f"Failed to create user in Firestore: {email}")
            return render_template('register.html', error="Failed to create account. Please try again.")
        
        logger.info(f"✓ New user registered: {student_id} ({email})")
        
        # Log in the user immediately after registration
        login_user(user)
        User.update_last_login(user['id'])
        
        # Verify session was set
        if not session.get("logged_in"):
            logger.error("Session not set after registration")
            flash('Account created but login failed. Please login manually.', 'warning')
            return redirect(url_for('login'))
        
        logger.info(f"✓ User auto-logged in after registration: {email}")
        flash('Registration successful! Welcome to the portal.', 'success')
        return redirect(url_for('profile'))
        
    except Exception as e:
        logger.error(f"Error during registration: {e}", exc_info=True)
        return render_template('register.html', error="An error occurred. Please try again.")


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit(config.AUTH_RATE_LIMIT_LOGIN, methods=['POST'])
def login():
    """User login page with rate limiting"""
    if get_current_user():
        return redirect(url_for('profile'))
    
    if request.method == 'GET':
        return render_template('login.html')
    
    try:
        identifier = sanitize_input(request.form.get('identifier', '').strip())
        password = request.form.get('password', '')
        
        if not identifier or not password:
            return render_template('login.html', error="Please enter both email/student ID and password")
        
        # Find user by email or student ID
        user = User.get_by_email(identifier.lower())
        if not user:
            user = User.get_by_student_id(identifier.upper())
        
        if not user:
            # Generic error to prevent account enumeration
            return render_template('login.html', error="Invalid credentials. Please try again.")
        
        # Check password
        from werkzeug.security import check_password_hash
        if not check_password_hash(user['password_hash'], password):
            return render_template('login.html', error="Invalid credentials. Please try again.")
        
        if not user.get('is_active', True):
            return render_template('login.html', error="Your account has been deactivated. Please contact support.")
        
        # Log in user
        login_user(user)
        User.update_last_login(user['id'])
        
        logger.info(f"User logged in: {user['student_id']}")
        
        flash(f'Welcome back, {user["name"]}!', 'success')
        
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect(url_for('profile'))
        
    except Exception as e:
        logger.error(f"Error during login: {e}")
        return render_template('login.html', error="An error occurred. Please try again.")

@app.route('/logout')
@login_required
def logout():
    """Log out current user"""
    user = get_current_user()
    if user:
        logger.info(f"User logged out: {user['student_id']}")
    
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# ============================================================================
# USER PROFILE ROUTES
# ============================================================================

@app.route('/profile')
@login_required
@handle_errors()
def profile():
    """User profile page"""
    try:
        current_user_data = get_current_user()
        
        if not current_user_data:
            flash('Please log in to view your profile.', 'warning')
            return redirect(url_for('login'))
        
        user = User.get_by_id(current_user_data['id'])
        
        if not user:
            logger.error(f"User not found in database: {current_user_data['id']}")
            flash('User account not found. Please login again.', 'danger')
            return redirect(url_for('logout'))
        
        logger.info(f"Loading profile for user: {user['email']}")
        
        # Get user's complaints
        complaints = []
        try:
            # Get all complaints and filter by user_id
            all_complaints = Complaint.get_all()
            complaints = [c for c in all_complaints if c.get('user_id') == user['id']]
            logger.info(f"Found {len(complaints)} complaints for user {user['id']}")
        except Exception as e:
            logger.error(f"Error getting user complaints: {e}")
            complaints = []
        
        # Calculate stats
        total_complaints = len(complaints)
        high_severity = sum(1 for c in complaints if c.get('severity') == 'high')
        medium_severity = sum(1 for c in complaints if c.get('severity') == 'medium')
        low_severity = sum(1 for c in complaints if c.get('severity') == 'low')
        
        stats = {
            'total_complaints': total_complaints,
            'high_severity': high_severity,
            'medium_severity': medium_severity,
            'low_severity': low_severity
        }
        
        logger.info(f"User stats: {stats}")
        
        # Get recent complaints (last 5)
        recent_complaints = sorted(
            complaints,
            key=lambda x: x.get('timestamp', datetime.min),
            reverse=True
        )[:5]
        
        # Category breakdown
        category_breakdown = {}
        for c in complaints:
            cat = c.get('category', 'Other')
            category_breakdown[cat] = category_breakdown.get(cat, 0) + 1
        
        logger.info(f"Category breakdown: {category_breakdown}")
        
        return render_template('profile.html',
                             user=user,
                             stats=stats,
                             recent_complaints=recent_complaints,
                             category_breakdown=category_breakdown)
        
    except Exception as e:
        logger.error(f"Error loading profile: {e}", exc_info=True)
        flash('Error loading profile. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/my-complaints')
@login_required
@handle_errors()
def my_complaints():
    """View all user complaints - FIXED VERSION"""
    try:
        current_user_data = get_current_user()
        
        if not current_user_data:
            flash('Please log in to view your complaints.', 'warning')
            return redirect(url_for('login'))
        
        user = User.get_by_id(current_user_data['id'])
        
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('logout'))
        
        logger.info(f"Loading complaints for user: {user['id']}")
        
        # FIXED: Get ALL complaints and filter by user_id
        all_complaints = Complaint.get_all()
        complaints = [c for c in all_complaints if c.get('user_id') == user['id']]
        
        # Sort by timestamp (newest first)
        complaints.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
        
        logger.info(f"Found {len(complaints)} complaints for user {user['id']}")
        
        # Debug: Log first few complaint user_ids
        for i, c in enumerate(all_complaints[:5]):
            logger.info(f"Sample complaint {i}: user_id={c.get('user_id')}, matches={c.get('user_id') == user['id']}")
        
        # Simple pagination
        page = request.args.get('page', 1, type=int)
        per_page = 10
        start = (page - 1) * per_page
        end = start + per_page
        
        paginated_complaints = complaints[start:end]
        total_pages = max((len(complaints) + per_page - 1) // per_page, 1)
        
        # Create pagination object
        class Pagination:
            def __init__(self, items, page, pages, total):
                self.items = items
                self.page = page
                self.pages = pages
                self.total = total
                self.has_prev = page > 1
                self.has_next = page < pages
                self.prev_num = page - 1 if self.has_prev else None
                self.next_num = page + 1 if self.has_next else None
            
            def iter_pages(self):
                return range(1, self.pages + 1)
        
        pagination = Pagination(paginated_complaints, page, total_pages, len(complaints))
        
        return render_template('my_complaints.html', 
                             complaints=pagination, 
                             user=user,
                             total_complaints=len(complaints))
        
    except Exception as e:
        logger.error(f"Error loading complaints: {e}", exc_info=True)
        flash('Error loading complaints.', 'danger')
        return redirect(url_for('profile'))

@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
@handle_errors()
def edit_profile():
    """Edit user profile"""
    try:
        current_user_data = get_current_user()
        user = User.get_by_id(current_user_data['id'])
        
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('logout'))
        
        if request.method == 'GET':
            return render_template('edit_profile.html', user=user)
        
        # POST request - update profile
        name = sanitize_input(request.form.get('name', '').strip())
        department = sanitize_input(request.form.get('department', '').strip())
        year = request.form.get('year', type=int)
        hostel = sanitize_input(request.form.get('hostel', '').strip())
        room_number = sanitize_input(request.form.get('room_number', '').strip())
        phone = sanitize_input(request.form.get('phone', '').strip())
        
        update_data = {
            'name': name if name else user['name'],
            'department': department if department else None,
            'year': year if year else None,
            'hostel': hostel if hostel else None,
            'room_number': room_number if room_number else None,
            'phone': phone if phone else None
        }
        
        if User.update(user['id'], update_data):
            session['name'] = update_data['name']
            logger.info(f"Profile updated for user: {user['student_id']}")
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Error updating profile.', 'danger')
            return render_template('edit_profile.html', user=user)
        
    except Exception as e:
        logger.error(f"Error in edit_profile: {e}", exc_info=True)
        flash('Error accessing profile settings.', 'danger')
        return redirect(url_for('profile'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
@limiter.limit(config.AUTH_RATE_LIMIT_PASSWORD_CHANGE, methods=['POST'])
@handle_errors()
def change_password():
    """Change user password with rate limiting"""
    try:
        if request.method == 'GET':
            return render_template('change_password.html')
        
        current_user_data = get_current_user()
        user = User.get_by_id(current_user_data['id'])
        
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('logout'))
        
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate current password
        from werkzeug.security import check_password_hash, generate_password_hash
        if not check_password_hash(user['password_hash'], current_password):
            return render_template('change_password.html', error="Current password is incorrect")
        
        if new_password != confirm_password:
            return render_template('change_password.html', error="New passwords do not match")
        
        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            return render_template('change_password.html', error=error_msg)
        
        # Update password
        new_hash = generate_password_hash(new_password, method='pbkdf2:sha256:600000')
        if User.update(user['id'], {'password_hash': new_hash}):
            logger.info(f"Password changed for user: {user['student_id']}")
            flash('Password changed successfully!', 'success')
            return redirect(url_for('profile'))
        else:
            return render_template('change_password.html', error="An error occurred. Please try again.")
        
    except Exception as e:
        logger.error(f"Error in change_password: {e}", exc_info=True)
        return render_template('change_password.html', error="An unexpected error occurred.")

# ============================================================================
# COMPLAINT SUBMISSION ROUTES
# ============================================================================

@app.route('/submit', methods=['GET', 'POST'])
@handle_errors()
def submit():
    """Complaint submission page"""
    if request.method == 'GET':
        try:
            # Fix: Always initialize categories if they don't exist
            if Category.count() == 0:
                logger.info("No categories found, initializing...")
                initialize_categories()
            
            categories = Category.get_all()
            
            if not categories:
                logger.error("Categories still empty after initialization")
                # Emergency fallback
                return render_template('submit.html', 
                                     categories=[
                                         {'name': 'Mess Food Quality'},
                                         {'name': 'Campus Wi-Fi'},
                                         {'name': 'Medical Center'},
                                         {'name': 'Placement/CDC'},
                                         {'name': 'Faculty Concerns'},
                                         {'name': 'Hostel Maintenance'},
                                         {'name': 'Other'}
                                     ], 
                                     error=None)
            
            logger.info(f"Loaded {len(categories)} categories for form")
            return render_template('submit.html', categories=categories, error=None)
            
        except Exception as e:
            logger.error(f"Error in submit GET: {str(e)}")
            # Emergency fallback with hardcoded categories
            return render_template('submit.html', 
                                 categories=[
                                     {'name': 'Mess Food Quality'},
                                     {'name': 'Campus Wi-Fi'},
                                     {'name': 'Medical Center'},
                                     {'name': 'Placement/CDC'},
                                     {'name': 'Faculty Concerns'},
                                     {'name': 'Hostel Maintenance'},
                                     {'name': 'Other'}
                                 ], 
                                 error="Error loading form. Using default categories.")

    # POST request handling (rest remains the same)
    if request.method == 'POST':
        try:
            current_user = get_current_user()
            
            raw_text = request.form.get('raw_text', '').strip()
            if not raw_text:
                categories = Category.get_all()
                return render_template('submit.html', categories=categories, error="Please enter a complaint")

            if len(raw_text) > config.MAX_COMPLAINT_LENGTH:
                categories = Category.get_all()
                return render_template('submit.html', categories=categories,
                                     error=f"Complaint must be under {config.MAX_COMPLAINT_LENGTH} characters")

            category_name = request.form.get('category', '').strip()
            anonymous = request.form.get('anonymous') == 'on'
            
            # FIXED: Properly handle user_id and student_id
            if current_user and not anonymous:
                user_id = current_user['id']
                student_id = current_user['student_id']
                logger.info(f"Logged in user submitting: {user_id}")
            elif not anonymous and not current_user:
                # Manual student ID entry (no login)
                student_id = request.form.get('student_id', 'anonymous').strip()
                user_id = None
                logger.info(f"Anonymous with student ID: {student_id}")
            else:
                # Fully anonymous
                student_id = None
                user_id = None
                logger.info("Fully anonymous submission")
            
            # AI Processing
            try:
                rewritten_text = rewrite_complaint(raw_text)
            except:
                rewritten_text = raw_text

            try:
                if not category_name:
                    category_name = classify_category(rewritten_text)
                if not Category.get_by_name(category_name):
                    category_name = 'Other'
            except:
                category_name = 'Other'

            try:
                severity = detect_severity(rewritten_text)
            except:
                severity = 'medium'

            try:
                embedding = generate_embedding(rewritten_text)
            except:
                embedding = None

            # CRITICAL: Create complaint with user_id
            complaint_data = {
                'user_id': user_id,  # This is the key field
                'student_id': student_id,
                'raw_text': raw_text,
                'rewritten_text': rewritten_text,
                'category': category_name,
                'severity': severity,
                'cluster_id': None,
                'upvotes': 0
            }
            
            logger.info(f"Creating complaint with data: user_id={user_id}, student_id={student_id}")

            complaint = Complaint.create(complaint_data)
            
            if not complaint:
                categories = Category.get_all()
                return render_template('submit.html', categories=categories, error="Failed to submit complaint")
            
            logger.info(f"✓ Complaint created: {complaint['id']}")

            if embedding is not None:
                Complaint.set_embedding(complaint['id'], embedding)

            try:
                cluster_id = assign_cluster(complaint)
                if cluster_id:
                    Complaint.update(complaint['id'], {'cluster_id': cluster_id})
            except Exception as e:
                logger.error(f"Cluster assignment error: {str(e)}")

            try:
                update_clusters()
            except Exception as e:
                logger.error(f"Cluster update error: {str(e)}")

            flash('Complaint submitted successfully!', 'success')
            return redirect(url_for('success'))

        except Exception as e:
            logger.error(f"Unexpected submission error: {str(e)}", exc_info=True)
            categories = Category.get_all()
            return render_template('submit.html', categories=categories, 
                                 error="An error occurred. Please try again.")

@app.route('/success')
def success():
    try:
        return render_template('success.html')
    except Exception as e:
        logger.error(f"Error rendering success page: {str(e)}")
        return redirect(url_for('index'))

# ============================================================================
# DASHBOARD ROUTES
# ============================================================================

@app.route('/dashboard')
@handle_errors()
def dashboard():
    """Admin dashboard"""
    try:
        logger.info("Loading dashboard...")
        
        # Get statistics
        stats = get_dashboard_stats()
        logger.info(f"Stats: {stats.get('total_complaints', 0)} complaints")
        
        # Get all clusters
        clusters = IssueCluster.get_all(limit=20)
        logger.info(f"Clusters: {len(clusters)}")
        
        # Add complaint details to each cluster
        for cluster in clusters:
            try:
                complaints = Complaint.get_by_cluster(cluster['id'])
                cluster['complaints'] = complaints
                logger.info(f"Cluster {cluster['id']}: {len(complaints)} complaints")
            except Exception as e:
                logger.error(f"Error getting complaints for cluster {cluster['id']}: {e}")
                cluster['complaints'] = []
        
        # Get recent complaints directly
        recent = get_recent_complaints(limit=10)
        logger.info(f"Recent complaints: {len(recent)}")
        
        # Convert timestamp strings to datetime objects for template
        for complaint in recent:
            if complaint.get('timestamp'):
                if isinstance(complaint['timestamp'], str):
                    try:
                        complaint['timestamp'] = datetime.fromisoformat(complaint['timestamp'].replace('Z', '+00:00'))
                    except:
                        complaint['timestamp'] = datetime.utcnow()
        
        # Log what we're sending to template
        logger.info(f"Rendering dashboard with:")
        logger.info(f"  - Total complaints: {stats.get('total_complaints', 0)}")
        logger.info(f"  - High severity: {stats.get('severity_stats', {}).get('high', 0)}")
        logger.info(f"  - Clusters: {len(clusters)}")
        logger.info(f"  - Recent: {len(recent)}")
        
        return render_template('dashboard.html', 
                             stats=stats, 
                             clusters=clusters, 
                             recent=recent)
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}", exc_info=True)
        # Return dashboard with empty data instead of error page
        return render_template('dashboard.html', 
                             stats={
                                 'total_complaints': 0,
                                 'severity_stats': {'high': 0, 'medium': 0, 'low': 0},
                                 'category_stats': {},
                                 'total_clusters': 0,
                                 'recent_complaints': 0
                             }, 
                             clusters=[], 
                             recent=[],
                             error="Error loading dashboard data")

@app.route('/cluster/<cluster_id>')
@handle_errors()
def cluster_detail(cluster_id):
    try:
        cluster = IssueCluster.get_by_id(cluster_id)
        if not cluster:
            return render_template('error.html', error_code=404, error_message="Cluster not found"), 404
        
        complaints = Complaint.get_by_cluster(cluster_id)
        
        # Convert timestamp strings to datetime objects for template
        for c in complaints:
            if isinstance(c.get('timestamp'), str):
                c['timestamp'] = datetime.fromisoformat(c['timestamp'].replace('Z', '+00:00'))
        
        return render_template('cluster_detail.html', cluster=cluster, complaints=complaints)
    except Exception as e:
        logger.error(f"Cluster detail error: {e}")
        return render_template('error.html', error_code=500, error_message="Cluster load error"), 500

# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/complaint/<complaint_id>/upvote', methods=['POST'])
@handle_errors(return_json=True)
@csrf.exempt
@limiter.limit(config.API_RATE_LIMIT_UPVOTE)
def upvote_complaint(complaint_id):
    """API endpoint to upvote a complaint with rate limiting"""
    try:
        logger.info(f"Upvote request for complaint: {complaint_id}")
        
        # Check if complaint exists
        complaint = Complaint.get_by_id(complaint_id)
        if not complaint:
            logger.error(f"Complaint not found: {complaint_id}")
            return jsonify({
                'success': False, 
                'error': 'Complaint not found'
            }), 404
        
        # Increment upvotes
        upvotes = Complaint.increment_upvotes(complaint_id)
        
        if upvotes is not None:
            logger.info(f"Upvoted complaint {complaint_id}, new count: {upvotes}")
            return jsonify({
                'success': True, 
                'upvotes': upvotes
            }), 200
        else:
            logger.error(f"Failed to increment upvotes for {complaint_id}")
            return jsonify({
                'success': False, 
                'error': 'Failed to upvote'
            }), 500
        
    except Exception as e:
        logger.error(f"Upvote error for {complaint_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False, 
            'error': 'An error occurred'
        }), 500

@app.route('/api/rewrite', methods=['POST'])
@csrf.exempt
@handle_errors(return_json=True)
def api_rewrite():
    data = request.get_json()
    raw_text = data.get('text', '').strip()

    if not raw_text:
        return jsonify({'error': 'No text provided'}), 400

    rewritten = rewrite_complaint(raw_text)
    return jsonify({'rewritten_text': rewritten})

   
@app.route('/api/stats')
def api_stats():
        stats = get_dashboard_stats()
        return jsonify(stats)

# ============================================================================
# UTILITY ROUTES
# ============================================================================

@app.route('/health')
@handle_errors(return_json=True)
def health_check():
    try:
        category_count = Category.count()
        user_count = len([u for u in User.get_all()]) if hasattr(User, 'get_all') else 0
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'categories': category_count,
            'users': 'firebase'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503
    
@app.route('/test-rate-limit')
@limiter.limit("3 per minute")
def test_rate_limit():
    """Test route to verify rate limiting works"""
    return jsonify({
        'success': True,
        'message': 'Rate limit test successful',
        'timestamp': datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
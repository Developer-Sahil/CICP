from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
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
from ai.rewrite import rewrite_complaint
from ai.classify import classify_category
from ai.severity import detect_severity
from ai.embed import generate_embedding
from ai.cluster import assign_cluster, update_clusters
from utils.firebase_helpers import get_dashboard_stats, get_recent_complaints
from auth.auth import (
    login_required, admin_required, get_current_user,
    login_user, logout_user, update_last_login,
    validate_email, validate_student_id, validate_password,
    sanitize_input, check_rate_limit
)
from datetime import datetime, timedelta
import logging
import config

app = Flask(__name__)
app.config.from_object(config)

app.jinja_env.globals.update(
    FIREBASE_API_KEY=config.FIREBASE_API_KEY,
    FIREBASE_AUTH_DOMAIN=config.FIREBASE_AUTH_DOMAIN,
    FIREBASE_PROJECT_ID=config.FIREBASE_PROJECT_ID,
    FIREBASE_STORAGE_BUCKET=getattr(config, "FIREBASE_STORAGE_BUCKET", ""),
    FIREBASE_MSG_SENDER_ID=getattr(config, "FIREBASE_MSG_SENDER_ID", ""),
    FIREBASE_APP_ID=getattr(config, "FIREBASE_APP_ID", "")
)

app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Register Firebase Google Login routes
from auth.firebase_auth import firebase_bp
app.register_blueprint(firebase_bp)

app.jinja_env.globals.update({
    'min': min,
    'max': max,
    'abs': abs,
    'len': len
})

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize categories
try:
    initialize_categories()
    logger.info("Categories initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize categories: {e}")

# Context processor
@app.context_processor
def inject_user():
    """Make current user available in all templates"""
    return dict(current_user=get_current_user())

# ================== ERROR HANDLERS ==================
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error_code=404, error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {str(error)}")
    return render_template('error.html', error_code=500, error_message="Internal server error"), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    return render_template('error.html', error_code=500, error_message="An unexpected error occurred"), 500

# ============================================================================
# PUBLIC ROUTES
# ============================================================================
@app.route('/')
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
def register():
    """User registration page"""
    if get_current_user():
        return redirect(url_for('profile'))
    
    if request.method == 'GET':
        return render_template('register.html')
    
    try:
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
        
        if not all([name, student_id, email, password, confirm_password]):
            return render_template('register.html', error="Please fill in all required fields")
        
        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match")
        
        if not validate_email(email):
            return render_template('register.html', error="Invalid email address")
        
        if not validate_student_id(student_id):
            return render_template('register.html', error="Invalid student ID format (6-15 alphanumeric characters)")
        
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            return render_template('register.html', error=error_msg)
        
        # Check if user exists
        if User.get_by_email(email):
            return render_template('register.html', error="Email already registered")
        
        if User.get_by_student_id(student_id):
            return render_template('register.html', error="Student ID already registered")
        
        # Create user
        from werkzeug.security import generate_password_hash
        user_data = {
            'name': name,
            'student_id': student_id,
            'email': email,
            'password_hash': generate_password_hash(password, method='pbkdf2:sha256'),
            'department': department if department else None,
            'year': year if year else None,
            'hostel': hostel if hostel else None,
            'room_number': room_number if room_number else None,
            'phone': phone if phone else None,
            'is_google': False
        }
        
        user = User.create(user_data)
        if not user:
            return render_template('register.html', error="Failed to create account")
        
        logger.info(f"New user registered: {student_id}")
        
        # Log in the user
        login_user(user)
        User.update_last_login(user['id'])
        
        flash('Registration successful! Welcome to the portal.', 'success')
        return redirect(url_for('profile'))
        
    except Exception as e:
        logger.error(f"Error during registration: {e}")
        return render_template('register.html', error="An error occurred. Please try again.")

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if get_current_user():
        return redirect(url_for('profile'))
    
    if request.method == 'GET':
        return render_template('login.html')
    
    try:
        identifier = sanitize_input(request.form.get('identifier', '').strip())
        password = request.form.get('password', '')
        
        if not identifier or not password:
            return render_template('login.html', error="Please enter both email/student ID and password")
        
        allowed, remaining = check_rate_limit(identifier, 'login_attempt', limit=5)
        if not allowed:
            logger.warning(f"Rate limit exceeded for login: {identifier}")
            return render_template('login.html', error="Too many login attempts. Please try again in 15 minutes.")
        
        # Find user by email or student ID
        user = User.get_by_email(identifier.lower())
        if not user:
            user = User.get_by_student_id(identifier.upper())
        
        if not user:
            return render_template('login.html', error="Invalid email/student ID or password")
        
        # Check password
        from werkzeug.security import check_password_hash
        if not check_password_hash(user['password_hash'], password):
            return render_template('login.html', error="Invalid email/student ID or password")
        
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
def profile():
    """User profile page"""
    try:
        current_user_data = get_current_user()
        user = User.get_by_id(current_user_data['id'])
        
        if not user:
            flash('User account not found. Please login again.', 'danger')
            return redirect(url_for('logout'))
        
        # Get complaints
        complaints = User.get_complaints(user['id'])
        
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
        
        # Get recent complaints
        recent_complaints = complaints[:5]
        
        # Category breakdown
        category_breakdown = {}
        for c in complaints:
            cat = c.get('category', 'Other')
            category_breakdown[cat] = category_breakdown.get(cat, 0) + 1
        
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
def my_complaints():
    """View all user complaints"""
    try:
        current_user_data = get_current_user()
        user = User.get_by_id(current_user_data['id'])
        
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('logout'))
        
        # Get all complaints
        complaints = User.get_complaints(user['id'])
        
        # Simple pagination
        page = request.args.get('page', 1, type=int)
        per_page = 10
        start = (page - 1) * per_page
        end = start + per_page
        
        paginated_complaints = complaints[start:end]
        total_pages = (len(complaints) + per_page - 1) // per_page
        
        # Create pagination object
        class Pagination:
            def __init__(self, items, page, pages):
                self.items = items
                self.page = page
                self.pages = pages
                self.has_prev = page > 1
                self.has_next = page < pages
                self.prev_num = page - 1 if self.has_prev else None
                self.next_num = page + 1 if self.has_next else None
            
            def iter_pages(self):
                return range(1, self.pages + 1)
        
        pagination = Pagination(paginated_complaints, page, max(total_pages, 1))
        
        return render_template('my_complaints.html', complaints=pagination, user=user)
        
    except Exception as e:
        logger.error(f"Error loading complaints: {e}", exc_info=True)
        flash('Error loading complaints.', 'danger')
        return redirect(url_for('profile'))

@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
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
def change_password():
    """Change user password"""
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
        new_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
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
def submit():
    """Complaint submission page"""
    if request.method == 'GET':
        try:
            categories = Category.get_all()
            if not categories:
                initialize_categories()
                categories = Category.get_all()
            return render_template('submit.html', categories=categories, error=None)
        except Exception as e:
            logger.error(f"Error in submit GET: {str(e)}")
            return render_template('submit.html', categories=[], error="Error loading form.")

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
            
            if current_user and not anonymous:
                student_id = current_user['student_id']
                user_id = current_user['id']
            elif not anonymous:
                student_id = request.form.get('student_id', 'anonymous').strip()
                user_id = None
            else:
                student_id = None
                user_id = None
            
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

            complaint_data = {
                'user_id': user_id,
                'student_id': student_id,
                'raw_text': raw_text,
                'rewritten_text': rewritten_text,
                'category': category_name,
                'severity': severity,
                'cluster_id': None
            }

            complaint = Complaint.create(complaint_data)
            if not complaint:
                categories = Category.get_all()
                return render_template('submit.html', categories=categories, error="Failed to submit complaint")

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

            return redirect(url_for('success'))

        except Exception as e:
            logger.error(f"Unexpected submission error: {str(e)}")
            categories = Category.get_all()
            return render_template('submit.html', categories=categories, error="Unexpected error")

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
def dashboard():
    """Admin dashboard"""
    try:
        stats = get_dashboard_stats()
        clusters = IssueCluster.get_all(limit=20)
        
        # Add complaint counts to clusters
        for cluster in clusters:
            complaints = Complaint.get_by_cluster(cluster['id'])
            cluster['complaints'] = complaints
        
        recent = get_recent_complaints(limit=10)
        return render_template('dashboard.html', stats=stats, clusters=clusters, recent=recent)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return render_template('dashboard.html', stats={}, clusters=[], recent=[], error="Dashboard error")

@app.route('/cluster/<cluster_id>')
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
def upvote_complaint(complaint_id):
    """API endpoint to upvote a complaint"""
    try:
        upvotes = Complaint.increment_upvotes(complaint_id)
        if upvotes is not None:
            return jsonify({'success': True, 'upvotes': upvotes}), 200
        return jsonify({'success': False, 'error': 'Complaint not found'}), 404
    except Exception as e:
        logger.error(f"Upvote error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to upvote'}), 500

@app.route('/api/rewrite', methods=['POST'])
def api_rewrite():
    try:
        data = request.get_json()
        raw_text = data.get('text', '').strip()
        if not raw_text:
            return jsonify({'error': 'No text provided'}), 400
        rewritten = rewrite_complaint(raw_text)
        return jsonify({'rewritten_text': rewritten})
    except:
        return jsonify({'error': 'Rewrite failed'}), 500

@app.route('/api/stats')
def api_stats():
    try:
        stats = get_dashboard_stats()
        return jsonify(stats)
    except:
        return jsonify({'error': 'Stats fetch failed'}), 500

# ============================================================================
# UTILITY ROUTES
# ============================================================================

@app.route('/health')
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

if __name__ == '__main__':
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5000)
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from database.models import db, Complaint, IssueCluster, Category, User
from ai.rewrite import rewrite_complaint
from ai.classify import classify_category
from ai.severity import detect_severity
from ai.embed import generate_embedding
from ai.cluster import assign_cluster, update_clusters
from utils.helpers import get_dashboard_stats, get_recent_complaints
from auth.auth import (
    login_required, admin_required, get_current_user,
    login_user, logout_user, update_last_login,
    validate_email, validate_student_id, validate_password,
    sanitize_input, check_rate_limit
)
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from sqlalchemy import func
import config
from datetime import datetime, timedelta
import logging

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize database
db.init_app(app)

def init_database():
    """Initialize database and create categories"""
    try:
        with app.app_context():
            # Create all tables
            db.create_all()
            logger.info("Database tables created successfully")
            
            # Check if categories exist
            category_count = Category.query.count()
            
            if category_count == 0:
                logger.info("Initializing categories...")
                categories = [
                    'Mess Food Quality',
                    'Campus Wi-Fi',
                    'Medical Center',
                    'Placement/CDC',
                    'Faculty Concerns',
                    'Hostel Maintenance',
                    'Other'
                ]
                
                for cat_name in categories:
                    category = Category(name=cat_name)
                    db.session.add(category)
                
                db.session.commit()
                logger.info(f"Successfully initialized {len(categories)} categories")
            else:
                logger.info(f"Categories already exist: {category_count} found")
                
    except OperationalError as e:
        logger.error(f"Database operational error during initialization: {str(e)}")
        logger.error("This might indicate database file corruption or permission issues")
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error during initialization: {str(e)}")
        db.session.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error during initialization: {str(e)}")
        raise

# Initialize database on startup
try:
    init_database()
except Exception as e:
    logger.critical(f"Failed to initialize database: {str(e)}")
    logger.critical("Application may not function correctly")

# Context processor to make current_user available in all templates
@app.context_processor
def inject_user():
    """Make current user available in all templates"""
    return dict(current_user=get_current_user())

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    logger.error(f"Internal error: {str(error)}")
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Internal server error"), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle uncaught exceptions"""
    db.session.rollback()
    logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    return render_template('error.html', 
                         error_code=500, 
                         error_message="An unexpected error occurred"), 500

# ============================================================================
# PUBLIC ROUTES
# ============================================================================

@app.route('/')
def index():
    """Landing page"""
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
    # Redirect if already logged in
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
            return render_template('register.html', 
                                 error="Please fill in all required fields")
        
        if password != confirm_password:
            return render_template('register.html', 
                                 error="Passwords do not match")
        
        # Validate email
        if not validate_email(email):
            return render_template('register.html', 
                                 error="Invalid email address")
        
        # Validate student ID
        if not validate_student_id(student_id):
            return render_template('register.html', 
                                 error="Invalid student ID format (6-15 alphanumeric characters)")
        
        # Validate password strength
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            return render_template('register.html', error=error_msg)
        
        # Check if user already exists
        existing_user = User.query.filter(
            (User.email == email) | (User.student_id == student_id)
        ).first()
        
        if existing_user:
            if existing_user.email == email:
                return render_template('register.html', 
                                     error="Email already registered")
            else:
                return render_template('register.html', 
                                     error="Student ID already registered")
        
        # Create new user
        user = User(
            name=name,
            student_id=student_id,
            email=email,
            department=department if department else None,
            year=year if year else None,
            hostel=hostel if hostel else None,
            room_number=room_number if room_number else None,
            phone=phone if phone else None
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"New user registered: {student_id}")
        
        # Log in the user
        login_user(user)
        update_last_login(user)
        
        flash('Registration successful! Welcome to the portal.', 'success')
        return redirect(url_for('profile'))
        
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Database integrity error during registration: {e}")
        return render_template('register.html', 
                             error="Email or Student ID already exists")
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during registration: {e}")
        return render_template('register.html', 
                             error="An error occurred. Please try again.")


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    # Redirect if already logged in
    if get_current_user():
        return redirect(url_for('profile'))
    
    if request.method == 'GET':
        return render_template('login.html')
    
    try:
        identifier = sanitize_input(request.form.get('identifier', '').strip())
        password = request.form.get('password', '')
        remember_me = request.form.get('remember_me') == 'on'
        
        if not identifier or not password:
            return render_template('login.html', 
                                 error="Please enter both email/student ID and password")
        
        # Rate limiting
        allowed, remaining = check_rate_limit(identifier, 'login_attempt', limit=5)
        if not allowed:
            logger.warning(f"Rate limit exceeded for login: {identifier}")
            return render_template('login.html', 
                                 error="Too many login attempts. Please try again in 15 minutes.")
        
        # Find user by email or student ID
        user = User.query.filter(
            (User.email == identifier.lower()) | 
            (User.student_id == identifier.upper())
        ).first()
        
        if not user or not user.check_password(password):
            return render_template('login.html', 
                                 error="Invalid email/student ID or password")
        
        if not user.is_active:
            return render_template('login.html', 
                                 error="Your account has been deactivated. Please contact support.")
        
        # Log in user
        login_user(user)
        update_last_login(user)
        
        logger.info(f"User logged in: {user.student_id}")
        
        # Set session lifetime
        if remember_me:
            session.permanent = True
        
        flash(f'Welcome back, {user.name}!', 'success')
        
        # Redirect to intended page or profile
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect(url_for('profile'))
        
    except Exception as e:
        logger.error(f"Error during login: {e}")
        return render_template('login.html', 
                             error="An error occurred. Please try again.")


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


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page"""
    if request.method == 'GET':
        return render_template('forgot_password.html')
    
    try:
        email = request.form.get('email', '').strip().lower()
        
        if not validate_email(email):
            return render_template('forgot_password.html',
                                 error="Invalid email address")
        
        user = User.query.filter_by(email=email).first()
        
        # Don't reveal if email exists (security)
        flash('If an account exists with that email, you will receive password reset instructions.', 'info')
        
        if user:
            from auth.auth import create_reset_token
            token = create_reset_token(user)
            
            # TODO: Send email with reset link
            # For now, just log it
            logger.info(f"Password reset requested for: {email}")
            logger.info(f"Reset token: {token}")
            # In production: send_reset_email(user.email, token)
        
        return redirect(url_for('login'))
        
    except Exception as e:
        logger.error(f"Error in forgot password: {e}")
        flash('An error occurred. Please try again.', 'danger')
        return render_template('forgot_password.html')

# ============================================================================
# USER PROFILE ROUTES
# ============================================================================

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    try:
        current_user = get_current_user()
        user = User.query.get(current_user['id'])
        
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('logout'))
        
        # Get user statistics
        total_complaints = user.get_complaint_count()
        high_severity = user.complaints.filter_by(severity='high').count()
        medium_severity = user.complaints.filter_by(severity='medium').count()
        low_severity = user.complaints.filter_by(severity='low').count()
        
        stats = {
            'total_complaints': total_complaints,
            'high_severity': high_severity,
            'medium_severity': medium_severity,
            'low_severity': low_severity
        }
        
        # Get recent complaints
        recent_complaints = user.get_recent_complaints(limit=5)
        
        # Category breakdown
        category_breakdown = dict(
            db.session.query(
                Complaint.category,
                func.count(Complaint.id)
            ).filter(
                Complaint.user_id == user.id
            ).group_by(
                Complaint.category
            ).all()
        )
        
        return render_template('profile.html',
                             user=user,
                             stats=stats,
                             recent_complaints=recent_complaints,
                             category_breakdown=category_breakdown)
        
    except Exception as e:
        logger.error(f"Error loading profile: {e}")
        flash('Error loading profile.', 'danger')
        return redirect(url_for('index'))


@app.route('/my-complaints')
@login_required
def my_complaints():
    """View all user complaints"""
    try:
        current_user = get_current_user()
        user = User.query.get(current_user['id'])
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        complaints = user.complaints.order_by(
            Complaint.timestamp.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return render_template('my_complaints.html',
                             complaints=complaints,
                             user=user)
        
    except Exception as e:
        logger.error(f"Error loading complaints: {e}")
        flash('Error loading complaints.', 'danger')
        return redirect(url_for('profile'))


@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    current_user = get_current_user()
    user = User.query.get(current_user['id'])
    
    if request.method == 'GET':
        return render_template('edit_profile.html', user=user)
    
    try:
        # Update user information
        user.name = sanitize_input(request.form.get('name', '').strip())
        user.department = sanitize_input(request.form.get('department', '').strip()) or None
        user.year = request.form.get('year', type=int) or None
        user.hostel = sanitize_input(request.form.get('hostel', '').strip()) or None
        user.room_number = sanitize_input(request.form.get('room_number', '').strip()) or None
        user.phone = sanitize_input(request.form.get('phone', '').strip()) or None
        
        db.session.commit()
        
        # Update session
        session['name'] = user.name
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating profile: {e}")
        flash('Error updating profile.', 'danger')
        return render_template('edit_profile.html', user=user)


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    if request.method == 'GET':
        return render_template('change_password.html')
    
    try:
        current_user = get_current_user()
        user = User.query.get(current_user['id'])
        
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate current password
        if not user.check_password(current_password):
            return render_template('change_password.html',
                                 error="Current password is incorrect")
        
        # Validate new password
        if new_password != confirm_password:
            return render_template('change_password.html',
                                 error="New passwords do not match")
        
        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            return render_template('change_password.html', error=error_msg)
        
        # Update password
        user.set_password(new_password)
        db.session.commit()
        
        logger.info(f"Password changed for user: {user.student_id}")
        
        flash('Password changed successfully!', 'success')
        return redirect(url_for('profile'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error changing password: {e}")
        return render_template('change_password.html',
                             error="An error occurred. Please try again.")

# ============================================================================
# COMPLAINT SUBMISSION ROUTES
# ============================================================================

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    """Complaint submission page"""
    if request.method == 'GET':
        try:
            # Try to fetch categories with error handling
            categories = []
            error_message = None
            
            try:
                categories = Category.query.order_by(Category.name).all()
                logger.info(f"Successfully loaded {len(categories)} categories")
                
                # If no categories found, try to reinitialize
                if not categories:
                    logger.warning("No categories found, attempting to reinitialize")
                    init_database()
                    categories = Category.query.all()
                    
            except OperationalError as e:
                logger.error(f"Database operational error loading categories: {str(e)}")
                error_message = "Database connection error. Please contact administrator."
            except SQLAlchemyError as e:
                logger.error(f"Database error loading categories: {str(e)}")
                error_message = "Error loading categories from database."
            except Exception as e:
                logger.error(f"Unexpected error loading categories: {str(e)}")
                error_message = "Unexpected error loading categories."
            
            return render_template('submit.html', 
                                 categories=categories,
                                 error=error_message)
                                 
        except Exception as e:
            logger.error(f"Critical error in submit GET: {str(e)}")
            return render_template('submit.html', 
                                 categories=[],
                                 error="Critical error loading form. Please try again later.")
    
    if request.method == 'POST':
        try:
            # Get current user if logged in
            current_user = get_current_user()
            
            # Get form data with validation
            raw_text = request.form.get('raw_text', '').strip()
            if not raw_text:
                categories = Category.query.all()
                return render_template('submit.html', 
                                     categories=categories,
                                     error="Please enter a complaint description")
            
            # Validate text length
            if len(raw_text) > config.MAX_COMPLAINT_LENGTH:
                categories = Category.query.all()
                return render_template('submit.html', 
                                     categories=categories,
                                     error=f"Complaint must be less than {config.MAX_COMPLAINT_LENGTH} characters")
            
            category_name = request.form.get('category', '').strip()
            anonymous = request.form.get('anonymous') == 'on'
            
            # Determine student_id
            if current_user and not anonymous:
                student_id = current_user['student_id']
            elif not anonymous:
                student_id = request.form.get('student_id', 'anonymous').strip()
            else:
                student_id = None
            
            # AI Processing Pipeline with error handling
            try:
                # 1. Rewrite complaint
                rewritten_text = rewrite_complaint(raw_text)
                logger.info("Complaint rewritten successfully")
            except Exception as e:
                logger.error(f"Error rewriting complaint: {str(e)}")
                rewritten_text = raw_text  # Fallback to original
            
            try:
                # 2. Classify category (if not provided)
                if not category_name:
                    category_name = classify_category(rewritten_text)
                    logger.info(f"Category classified as: {category_name}")
                
                # Validate category exists
                category_exists = Category.query.filter_by(name=category_name).first()
                if not category_exists:
                    logger.warning(f"Category '{category_name}' not found, using 'Other'")
                    category_name = 'Other'
                    
            except Exception as e:
                logger.error(f"Error classifying category: {str(e)}")
                category_name = 'Other'
            
            try:
                # 3. Detect severity
                severity = detect_severity(rewritten_text)
                logger.info(f"Severity detected as: {severity}")
            except Exception as e:
                logger.error(f"Error detecting severity: {str(e)}")
                severity = 'medium'  # Default fallback
            
            try:
                # 4. Generate embedding
                embedding = generate_embedding(rewritten_text)
                logger.info("Embedding generated successfully")
            except Exception as e:
                logger.error(f"Error generating embedding: {str(e)}")
                embedding = None  # Can proceed without embedding
            
            # 5. Create complaint
            complaint = Complaint(
                user_id=current_user['id'] if current_user else None,
                student_id=student_id if student_id else None,
                raw_text=raw_text,
                rewritten_text=rewritten_text,
                category=category_name,
                severity=severity,
                timestamp=datetime.utcnow()
            )
            
            # Set embedding if generated
            if embedding is not None:
                complaint.set_embedding(embedding)
            
            db.session.add(complaint)
            db.session.flush()  # Get the complaint ID before clustering
            logger.info(f"Complaint created with ID: {complaint.id}")
            
            try:
                # 6. Assign to cluster
                cluster_id = assign_cluster(complaint)
                complaint.cluster_id = cluster_id
                logger.info(f"Complaint assigned to cluster: {cluster_id}")
            except Exception as e:
                logger.error(f"Error assigning cluster: {str(e)}")
                # Continue without clustering
            
            db.session.commit()
            logger.info("Complaint saved successfully")
            
            try:
                # 7. Update cluster statistics (non-blocking)
                update_clusters()
            except Exception as e:
                logger.error(f"Error updating clusters: {str(e)}")
                # Non-critical, continue
            
            return redirect(url_for('success'))
            
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Database integrity error: {str(e)}")
            categories = Category.query.all()
            return render_template('submit.html', 
                                 categories=categories,
                                 error="Database error: Duplicate entry or constraint violation")
        
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error submitting complaint: {str(e)}")
            categories = Category.query.all()
            return render_template('submit.html', 
                                 categories=categories,
                                 error="Database error. Please try again.")
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error submitting complaint: {str(e)}")
            categories = Category.query.all()
            return render_template('submit.html', 
                                 categories=categories,
                                 error="An unexpected error occurred. Please try again.")


@app.route('/success')
def success():
    """Success page after complaint submission"""
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
    """Admin dashboard - accessible to all but shows different data for admins"""
    try:
        stats = get_dashboard_stats()
        clusters = IssueCluster.query.order_by(IssueCluster.count.desc()).limit(20).all()
        recent = get_recent_complaints(limit=10)
        
        return render_template(
            'dashboard.html',
            stats=stats,
            clusters=clusters,
            recent=recent
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error loading dashboard: {str(e)}")
        return render_template('dashboard.html', 
                             stats={}, 
                             clusters=[], 
                             recent=[],
                             error="Error loading dashboard data")
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        return render_template('dashboard.html', 
                             stats={}, 
                             clusters=[], 
                             recent=[],
                             error="Error loading dashboard")


@app.route('/cluster/<int:cluster_id>')
def cluster_detail(cluster_id):
    """Cluster detail page"""
    try:
        cluster = IssueCluster.query.get(cluster_id)
        if not cluster:
            return render_template('error.html', 
                                 error_code=404, 
                                 error_message="Cluster not found"), 404
        
        complaints = Complaint.query.filter_by(cluster_id=cluster_id)\
                                    .order_by(Complaint.timestamp.desc())\
                                    .all()
        
        return render_template(
            'cluster_detail.html',
            cluster=cluster,
            complaints=complaints
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error loading cluster: {str(e)}")
        return render_template('error.html', 
                             error_code=500, 
                             error_message="Error loading cluster details"), 500

# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/api/rewrite', methods=['POST'])
def api_rewrite():
    """API endpoint for AI rewriting"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        raw_text = data.get('text', '').strip()
        
        if not raw_text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Validate length
        if len(raw_text) > config.MAX_COMPLAINT_LENGTH:
            return jsonify({'error': f'Text too long. Maximum {config.MAX_COMPLAINT_LENGTH} characters'}), 400
        
        rewritten = rewrite_complaint(raw_text)
        return jsonify({'rewritten_text': rewritten})
        
    except Exception as e:
        logger.error(f"Error in rewrite API: {str(e)}")
        return jsonify({'error': 'Failed to rewrite text. Please try again.'}), 500


@app.route('/api/stats')
def api_stats():
    """API endpoint for dashboard statistics"""
    try:
        stats = get_dashboard_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error in stats API: {str(e)}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500

# ============================================================================
# UTILITY ROUTES
# ============================================================================

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        
        # Check categories exist
        category_count = Category.query.count()
        
        # Check users table
        user_count = User.query.count()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'categories': category_count,
            'users': user_count
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503


@app.route('/debug/db-info')
def db_info():
    """Database diagnostic information (remove in production)"""
    if not config.DEBUG:
        return jsonify({'error': 'Only available in DEBUG mode'}), 403
    
    try:
        info = {
            'database_uri': config.DATABASE_URI,
            'categories_count': Category.query.count(),
            'complaints_count': Complaint.query.count(),
            'clusters_count': IssueCluster.query.count(),
            'users_count': User.query.count(),
            'categories': [c.name for c in Category.query.all()]
        }
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5000)
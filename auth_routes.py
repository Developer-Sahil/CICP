"""
Authentication routes for the Campus Complaint Portal
Add these routes to your app.py file
"""

from flask import render_template, request, redirect, url_for, flash, session
from database.models import db, User, Complaint
from auth.auth import (
    login_required, admin_required, get_current_user,
    login_user, logout_user, update_last_login,
    validate_email, validate_student_id, validate_password,
    sanitize_input, check_rate_limit
)
from sqlalchemy.exc import IntegrityError
import logging

logger = logging.getLogger(__name__)


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
        from sqlalchemy import func
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


# Update the submit route to associate complaints with logged-in users
@app.route('/submit', methods=['GET', 'POST'])
def submit():
    """Complaint submission page - updated for authentication"""
    if request.method == 'POST':
        try:
            # Get current user if logged in
            current_user = get_current_user()
            
            # ... existing complaint processing code ...
            
            # When creating complaint, add user_id if logged in
            complaint = Complaint(
                user_id=current_user['id'] if current_user else None,
                student_id=student_id if student_id else None,
                raw_text=raw_text,
                rewritten_text=rewritten_text,
                category=category_name,
                severity=severity,
                timestamp=datetime.utcnow()
            )
            
            # ... rest of existing code ...
            
        except Exception as e:
            # ... existing error handling ...
            pass
    
    # ... existing GET code ...


# Context processor to make current_user available in all templates
@app.context_processor
def inject_user():
    """Make current user available in all templates"""
    return dict(current_user=get_current_user())
from flask import Flask, render_template, request, jsonify, redirect, url_for
from database.models import db, Complaint, IssueCluster, Category
from ai.rewrite import rewrite_complaint
from ai.classify import classify_category
from ai.severity import detect_severity
from ai.embed import generate_embedding
from ai.cluster import assign_cluster, update_clusters
from utils.helpers import get_dashboard_stats, get_recent_complaints
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
import config
from datetime import datetime
import logging

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = config.SECRET_KEY

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

@app.route('/')
def index():
    """Landing page"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        return "Error loading page", 500

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
            student_id = None if anonymous else request.form.get('student_id', 'anonymous').strip()
            
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

@app.route('/dashboard')
def dashboard():
    """Admin dashboard"""
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

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        
        # Check categories exist
        category_count = Category.query.count()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'categories': category_count
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

# Database diagnostic endpoint (for debugging)
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
            'categories': [c.name for c in Category.query.all()]
        }
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5000)
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
            db.create_all()
            logger.info("Database tables created successfully")
            
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
                
    except Exception as e:
        logger.error(f"Unexpected error during initialization: {str(e)}")
        raise

# Initialize database on startup
try:
    init_database()
except Exception as e:
    logger.critical(f"Failed to initialize database: {str(e)}")
    logger.critical("Application may not function correctly")

# ================== ERROR HANDLERS ==================
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    logger.error(f"Internal error: {str(error)}")
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Internal server error"), 500

@app.errorhandler(Exception)
def handle_exception(e):
    db.session.rollback()
    logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    return render_template('error.html', 
                         error_code=500, 
                         error_message="An unexpected error occurred"), 500

# ================== ROUTES ==================
@app.route('/')
def index():
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
            categories = Category.query.order_by(Category.name).all()
            if not categories:
                init_database()
                categories = Category.query.all()
            return render_template('submit.html', categories=categories, error=None)
        except Exception as e:
            logger.error(f"Critical error in submit GET: {str(e)}")
            return render_template('submit.html', categories=[], error="Critical error loading form.")

    if request.method == 'POST':
        try:
            raw_text = request.form.get('raw_text', '').strip()
            if not raw_text:
                categories = Category.query.all()
                return render_template('submit.html', categories=categories, error="Please enter a complaint")

            if len(raw_text) > config.MAX_COMPLAINT_LENGTH:
                categories = Category.query.all()
                return render_template('submit.html', categories=categories,
                                       error=f"Complaint must be under {config.MAX_COMPLAINT_LENGTH} characters")

            category_name = request.form.get('category', '').strip()
            anonymous = request.form.get('anonymous') == 'on'
            student_id = None if anonymous else request.form.get('student_id', '').strip()

            try:
                rewritten_text = rewrite_complaint(raw_text)
            except:
                rewritten_text = raw_text

            try:
                if not category_name:
                    category_name = classify_category(rewritten_text)
                if not Category.query.filter_by(name=category_name).first():
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

            complaint = Complaint(
                student_id=student_id if student_id else None,
                raw_text=raw_text,
                rewritten_text=rewritten_text,
                category=category_name,
                severity=severity,
                timestamp=datetime.utcnow()
            )

            if embedding is not None:
                complaint.set_embedding(embedding)

            db.session.add(complaint)
            db.session.flush()

            try:
                cluster_id = assign_cluster(complaint)
                complaint.cluster_id = cluster_id
            except Exception as e:
                logger.error(f"Cluster assignment error: {str(e)}")

            db.session.commit()

            try:
                update_clusters()
            except Exception as e:
                logger.error(f"Cluster update error: {str(e)}")

            return redirect(url_for('success'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected submission error: {str(e)}")
            categories = Category.query.all()
            return render_template('submit.html', categories=categories, error="Unexpected error")

@app.route('/success')
def success():
    try:
        return render_template('success.html')
    except Exception as e:
        logger.error(f"Error rendering success page: {str(e)}")
        return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    try:
        stats = get_dashboard_stats()
        clusters = IssueCluster.query.order_by(IssueCluster.count.desc()).limit(20).all()
        recent = get_recent_complaints(limit=10)
        return render_template('dashboard.html', stats=stats, clusters=clusters, recent=recent)
    except:
        return render_template('dashboard.html', stats={}, clusters=[], recent=[], error="Dashboard error")

@app.route('/cluster/<int:cluster_id>')
def cluster_detail(cluster_id):
    try:
        cluster = IssueCluster.query.get(cluster_id)
        if not cluster:
            return render_template('error.html', error_code=404, error_message="Cluster not found"), 404
        complaints = Complaint.query.filter_by(cluster_id=cluster_id).order_by(Complaint.timestamp.desc()).all()
        return render_template('cluster_detail.html', cluster=cluster, complaints=complaints)
    except:
        return render_template('error.html', error_code=500, error_message="Cluster load error"), 500


# ================== 🔵 UPVOTE API ROUTE (ADDED HERE) ==================
@app.route('/complaint/<int:id>/upvote', methods=['POST'])
def upvote_complaint(id):
    """API endpoint to upvote a complaint"""
    try:
        complaint = Complaint.query.get(id)
        if not complaint:
            return jsonify({'success': False, 'error': 'Complaint not found'}), 404

        complaint.upvotes += 1
        db.session.commit()

        return jsonify({'success': True, 'upvotes': complaint.upvotes}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Upvote error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to upvote'}), 500


# ================== EXISTING APIs ==================
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

# Health check endpoint
@app.route('/health')
def health_check():
    try:
        db.session.execute('SELECT 1')
        category_count = Category.query.count()
        return jsonify({'status': 'healthy', 'categories': category_count})
    except:
        return jsonify({'status': 'unhealthy'}), 503

# Debug DB info
@app.route('/debug/db-info')
def db_info():
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

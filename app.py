from flask import Flask, render_template, request, jsonify, redirect, url_for
from database.models import db, Complaint, IssueCluster, Category
from ai.rewrite import rewrite_complaint
from ai.classify import classify_category
from ai.severity import detect_severity
from ai.embed import generate_embedding
from ai.cluster import assign_cluster, update_clusters
from utils.helpers import get_dashboard_stats, get_recent_complaints
import config
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = config.SECRET_KEY

# Initialize database
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()
    # Initialize categories if not exist
    if Category.query.count() == 0:
        categories = [
            'Mess Food Quality',
            'Campus Wi-Fi',
            'Medical Center',
            'Placement/CDC',
            'Faculty Concerns',
            'Hostel Maintenance',
            'Other'
        ]
        for cat in categories:
            category = Category(name=cat)
            db.session.add(category)
        db.session.commit()

@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    """Complaint submission page"""
    if request.method == 'GET':
        categories = Category.query.all()
        return render_template('submit.html', categories=categories)
    
    if request.method == 'POST':
        try:
            # Get form data
            raw_text = request.form.get('raw_text')
            category_name = request.form.get('category')
            anonymous = request.form.get('anonymous') == 'on'
            student_id = None if anonymous else request.form.get('student_id', 'anonymous')
            
            # AI Processing Pipeline
            # 1. Rewrite complaint
            rewritten_text = rewrite_complaint(raw_text)
            
            # 2. Classify category (if not provided)
            if not category_name:
                category_name = classify_category(rewritten_text)
            
            # 3. Detect severity
            severity = detect_severity(rewritten_text)
            
            # 4. Generate embedding
            embedding = generate_embedding(rewritten_text)
            
            # 5. Create complaint
            complaint = Complaint(
                student_id=student_id,
                raw_text=raw_text,
                rewritten_text=rewritten_text,
                category=category_name,
                severity=severity,
                embedding=embedding,
                timestamp=datetime.utcnow()
            )
            
            db.session.add(complaint)
            db.session.commit()
            
            # 6. Assign to cluster
            cluster_id = assign_cluster(complaint)
            complaint.cluster_id = cluster_id
            db.session.commit()
            
            # 7. Update cluster statistics
            update_clusters()
            
            return redirect(url_for('success'))
            
        except Exception as e:
            print(f"Error submitting complaint: {e}")
            return render_template('submit.html', error=str(e))

@app.route('/success')
def success():
    """Success page after complaint submission"""
    return render_template('success.html')

@app.route('/dashboard')
def dashboard():
    """Admin dashboard"""
    stats = get_dashboard_stats()
    clusters = IssueCluster.query.order_by(IssueCluster.count.desc()).all()
    recent = get_recent_complaints(limit=10)
    
    return render_template(
        'dashboard.html',
        stats=stats,
        clusters=clusters,
        recent=recent
    )

@app.route('/cluster/<int:cluster_id>')
def cluster_detail(cluster_id):
    """Cluster detail page"""
    cluster = IssueCluster.query.get_or_404(cluster_id)
    complaints = Complaint.query.filter_by(cluster_id=cluster_id).all()
    
    return render_template(
        'cluster_detail.html',
        cluster=cluster,
        complaints=complaints
    )

@app.route('/api/rewrite', methods=['POST'])
def api_rewrite():
    """API endpoint for AI rewriting"""
    try:
        data = request.get_json()
        raw_text = data.get('text', '')
        
        if not raw_text:
            return jsonify({'error': 'No text provided'}), 400
        
        rewritten = rewrite_complaint(raw_text)
        return jsonify({'rewritten_text': rewritten})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """API endpoint for dashboard statistics"""
    stats = get_dashboard_stats()
    return jsonify(stats)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
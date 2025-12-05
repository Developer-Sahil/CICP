from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pickle

db = SQLAlchemy()

class Complaint(db.Model):
    """Model for storing student complaints"""
    __tablename__ = 'complaints'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(100), nullable=True)  # NULL for anonymous
    raw_text = db.Column(db.Text, nullable=False)
    rewritten_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # low, medium, high
    embedding = db.Column(db.LargeBinary, nullable=True)  # Pickled numpy array
    cluster_id = db.Column(db.Integer, db.ForeignKey('issue_clusters.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    cluster = db.relationship('IssueCluster', back_populates='complaints')
    
    def set_embedding(self, embedding_array):
        """Store numpy array as binary"""
        self.embedding = pickle.dumps(embedding_array)
    
    def get_embedding(self):
        """Retrieve numpy array from binary"""
        if self.embedding:
            return pickle.loads(self.embedding)
        return None
    
    def __repr__(self):
        return f'<Complaint {self.id} - {self.category}>'


class IssueCluster(db.Model):
    """Model for grouping similar complaints"""
    __tablename__ = 'issue_clusters'
    
    id = db.Column(db.Integer, primary_key=True)
    cluster_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    count = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    complaints = db.relationship('Complaint', back_populates='cluster', lazy='dynamic')
    
    def update_count(self):
        """Update complaint count for this cluster"""
        self.count = self.complaints.count()
        self.last_updated = datetime.utcnow()
    
    def __repr__(self):
        return f'<IssueCluster {self.id} - {self.cluster_name} ({self.count})>'


class Category(db.Model):
    """Model for complaint categories"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    
    def __repr__(self):
        return f'<Category {self.name}>'
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pickle
import numpy as np
import logging

db = SQLAlchemy()
logger = logging.getLogger(__name__)

# ============================================================================
# USER MODEL
# ============================================================================

class User(db.Model):
    """Model for student users"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=True)
    year = db.Column(db.Integer, nullable=True)  # 1, 2, 3, 4 for year of study
    hostel = db.Column(db.String(100), nullable=True)
    room_number = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    
    # Relationship to complaints
    complaints = db.relationship('Complaint', 
                                 backref='user', 
                                 lazy='dynamic',
                                 foreign_keys='Complaint.user_id')
    
    def set_password(self, password):
        """Set password hash"""
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        """Check password against hash"""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def get_complaint_count(self):
        """Get number of complaints submitted by user"""
        try:
            return self.complaints.count()
        except Exception as e:
            logger.error(f"Error getting complaint count: {e}")
            return 0
    
    def get_high_severity_count(self):
        """Get number of high severity complaints by user"""
        try:
            return self.complaints.filter_by(severity='high').count()
        except Exception as e:
            logger.error(f"Error getting high severity count: {e}")
            return 0
    
    def get_recent_complaints(self, limit=5):
        """Get user's recent complaints"""
        try:
            return self.complaints.order_by(
                Complaint.timestamp.desc()
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting recent complaints: {e}")
            return []
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'email': self.email,
            'name': self.name,
            'department': self.department,
            'year': self.year,
            'hostel': self.hostel,
            'room_number': self.room_number,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def __repr__(self):
        return f'<User {self.student_id} - {self.name}>'


# ============================================================================
# COMPLAINT MODEL
# ============================================================================

class Complaint(db.Model):
    """Model for storing student complaints"""
    __tablename__ = 'complaints'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)  # NEW FIELD
    student_id = db.Column(db.String(100), nullable=True, index=True)  # NULL for anonymous, indexed for querie
    raw_text = db.Column(db.Text, nullable=False)
    rewritten_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False, index=True)
    severity = db.Column(db.String(20), nullable=False, default='medium', index=True)
    embedding = db.Column(db.LargeBinary, nullable=True)  # Pickled numpy array
    cluster_id = db.Column(
        db.Integer, 
        db.ForeignKey('issue_clusters.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # ⭐ NEW FIELD — REQUIRED FOR UPVOTING
    upvotes = db.Column(db.Integer, default=0, nullable=False)

    # Relationship
    cluster = db.relationship('IssueCluster', back_populates='complaints')
    
    def set_embedding(self, embedding_array):
        """Store numpy array as binary"""
        try:
            if embedding_array is not None:
                if isinstance(embedding_array, list):
                    embedding_array = np.array(embedding_array)
                self.embedding = pickle.dumps(embedding_array)
            else:
                self.embedding = None
        except Exception as e:
            logger.error(f"Error setting embedding: {str(e)}")
            self.embedding = None
    
    def get_embedding(self):
        """Retrieve numpy array from binary"""
        try:
            if self.embedding:
                return pickle.loads(self.embedding)
            return None
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return None
    
    def to_dict(self):
        """Convert complaint to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'student_id': self.student_id if self.student_id else 'Anonymous',
            'raw_text': self.raw_text,
            'rewritten_text': self.rewritten_text,
            'category': self.category,
            'severity': self.severity,
            'cluster_id': self.cluster_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'upvotes': self.upvotes
        }
    
    def __repr__(self):
        return f'<Complaint {self.id} - {self.category}>'


# ============================================================================
# ISSUE CLUSTER MODEL
# ============================================================================

class IssueCluster(db.Model):
    """Model for grouping similar complaints"""
    __tablename__ = 'issue_clusters'
    
    id = db.Column(db.Integer, primary_key=True)
    cluster_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False, index=True)
    severity = db.Column(db.String(20), nullable=False, default='medium', index=True)
    count = db.Column(db.Integer, default=0, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationship
    complaints = db.relationship(
        'Complaint',
        back_populates='cluster',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    def update_count(self):
        """Update complaint count for this cluster"""
        try:
            self.count = self.complaints.count()
            self.last_updated = datetime.utcnow()
            return self.count
        except Exception as e:
            logger.error(f"Error updating cluster count: {str(e)}")
            return 0
    
    def get_recent_complaints(self, limit=5):
        """Get recent complaints in this cluster"""
        try:
            return self.complaints.order_by(
                Complaint.timestamp.desc()
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting recent complaints: {str(e)}")
            return []
    
    def to_dict(self):
        """Convert cluster to dictionary"""
        return {
            'id': self.id,
            'cluster_name': self.cluster_name,
            'category': self.category,
            'severity': self.severity,
            'count': self.count,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    def __repr__(self):
        return f'<IssueCluster {self.id} - {self.cluster_name} ({self.count})>'


# ============================================================================
# CATEGORY MODEL
# ============================================================================

class Category(db.Model):
    """Model for complaint categories"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert category to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Category {self.name}>'
    


# ============================================================================
# FIREBASE USER MODEL
# ============================================================================

class FirebaseUser(db.Model):
    """Google Login authenticated users"""
    __tablename__ = 'firebase_users'
    
    id = db.Column(db.Integer, primary_key=True)
    firebase_uid = db.Column(db.String(128), unique=True, nullable=False, index=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120))
    photo_url = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<FirebaseUser {self.email}>'


# ============================================================================
# DATABASE UTILITY FUNCTIONS
# ============================================================================
def safe_commit():
    """Safely commit changes"""
    try:
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        logger.error(f"Commit error: {str(e)}")
        return False, str(e)


def safe_add(obj):
    """Safely add object"""
    try:
        db.session.add(obj)
        return True, None
    except Exception as e:
        logger.error(f"Add error: {str(e)}")
        return False, str(e)


def safe_delete(obj):
    """Safely delete object"""
    try:
        db.session.delete(obj)
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete error: {str(e)}")
        return False, str(e)



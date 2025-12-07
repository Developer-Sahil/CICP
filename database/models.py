from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pickle
import numpy as np
import logging

db = SQLAlchemy()
logger = logging.getLogger(__name__)

class Complaint(db.Model):
    """Model for storing student complaints"""
    __tablename__ = 'complaints'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(100), nullable=True, index=True)  # NULL for anonymous, indexed for queries
    raw_text = db.Column(db.Text, nullable=False)
    rewritten_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False, index=True)  # Indexed for queries
    severity = db.Column(db.String(20), nullable=False, default='medium', index=True)  # low, medium, high
    embedding = db.Column(db.LargeBinary, nullable=True)  # Pickled numpy array
    cluster_id = db.Column(db.Integer, db.ForeignKey('issue_clusters.id', ondelete='SET NULL'), nullable=True, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationship
    cluster = db.relationship('IssueCluster', back_populates='complaints')
    
    def set_embedding(self, embedding_array):
        """
        Store numpy array as binary
        
        Args:
            embedding_array: numpy array or list
        """
        try:
            if embedding_array is not None:
                # Convert to numpy array if it's a list
                if isinstance(embedding_array, list):
                    embedding_array = np.array(embedding_array)
                self.embedding = pickle.dumps(embedding_array)
            else:
                self.embedding = None
        except Exception as e:
            logger.error(f"Error setting embedding: {str(e)}")
            self.embedding = None
    
    def get_embedding(self):
        """
        Retrieve numpy array from binary
        
        Returns:
            numpy.ndarray or None
        """
        try:
            if self.embedding:
                return pickle.loads(self.embedding)
            return None
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return None
    
    def to_dict(self):
        """
        Convert complaint to dictionary
        
        Returns:
            dict: Complaint data
        """
        return {
            'id': self.id,
            'student_id': self.student_id if self.student_id else 'Anonymous',
            'raw_text': self.raw_text,
            'rewritten_text': self.rewritten_text,
            'category': self.category,
            'severity': self.severity,
            'cluster_id': self.cluster_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    def __repr__(self):
        return f'<Complaint {self.id} - {self.category}>'


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
    complaints = db.relationship('Complaint', 
                                back_populates='cluster', 
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    
    def update_count(self):
        """
        Update complaint count for this cluster
        
        Returns:
            int: Updated count
        """
        try:
            self.count = self.complaints.count()
            self.last_updated = datetime.utcnow()
            return self.count
        except Exception as e:
            logger.error(f"Error updating cluster count: {str(e)}")
            return 0
    
    def get_recent_complaints(self, limit=5):
        """
        Get recent complaints in this cluster
        
        Args:
            limit (int): Number of complaints to retrieve
            
        Returns:
            list: List of Complaint objects
        """
        try:
            return self.complaints.order_by(
                Complaint.timestamp.desc()
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting recent complaints: {str(e)}")
            return []
    
    def to_dict(self):
        """
        Convert cluster to dictionary
        
        Returns:
            dict: Cluster data
        """
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


class Category(db.Model):
    """Model for complaint categories"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """
        Convert category to dictionary
        
        Returns:
            dict: Category data
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Category {self.name}>'


# Database utility functions
def safe_commit():
    """
    Safely commit database changes with rollback on error
    
    Returns:
        tuple: (success: bool, error: str or None)
    """
    try:
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        logger.error(f"Database commit error: {str(e)}")
        return False, str(e)


def safe_add(obj):
    """
    Safely add object to database session
    
    Args:
        obj: Database model object
        
    Returns:
        tuple: (success: bool, error: str or None)
    """
    try:
        db.session.add(obj)
        return True, None
    except Exception as e:
        logger.error(f"Database add error: {str(e)}")
        return False, str(e)


def safe_delete(obj):
    """
    Safely delete object from database
    
    Args:
        obj: Database model object
        
    Returns:
        tuple: (success: bool, error: str or None)
    """
    try:
        db.session.delete(obj)
        db.session.commit()
        return True, None
    except Exception as e:
        db.session.rollback()
        logger.error(f"Database delete error: {str(e)}")
        return False, str(e)
"""
Firebase Firestore database models and operations
Replaces SQLAlchemy models with Firestore operations
"""
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import pickle
import numpy as np
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
def initialize_firebase():
    """Initialize Firebase Admin SDK if not already initialized"""
    if not firebase_admin._apps:
        try:
            # Try to load from service account file first
            if os.path.exists('firebase_service_account.json'):
                cred = credentials.Certificate('firebase_service_account.json')
                firebase_admin.initialize_app(cred)
                logger.info("Firebase initialized from service account file")
            else:
                # Use environment variables
                service_account = {
                    "type": "service_account",
                    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                    "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
                    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
                }
                cred = credentials.Certificate(service_account)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase initialized from environment variables")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise

# Initialize Firebase
initialize_firebase()

# Initialize Firestore client
db = firestore.client()

# Collection names
USERS_COLLECTION = 'users'
COMPLAINTS_COLLECTION = 'complaints'
CATEGORIES_COLLECTION = 'categories'
CLUSTERS_COLLECTION = 'issue_clusters'

# ============================================================================
# USER OPERATIONS
# ============================================================================

class User:
    """User model for Firestore"""
    
    @staticmethod
    def create(user_data):
        """Create a new user"""
        try:
            user_data['created_at'] = datetime.utcnow()
            user_data['last_login'] = None
            user_data['is_active'] = True
            user_data['is_admin'] = user_data.get('is_admin', False)
            user_data['email_verified'] = user_data.get('email_verified', False)
            
            doc_ref = db.collection(USERS_COLLECTION).document()
            user_data['id'] = doc_ref.id
            doc_ref.set(user_data)
            
            logger.info(f"Created user: {user_data.get('email')}")
            return user_data
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        try:
            doc = db.collection(USERS_COLLECTION).document(user_id).get()
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        try:
            users = db.collection(USERS_COLLECTION).where('email', '==', email).limit(1).get()
            for user in users:
                data = user.to_dict()
                data['id'] = user.id
                return data
            return None
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    @staticmethod
    def get_by_student_id(student_id):
        """Get user by student ID"""
        try:
            users = db.collection(USERS_COLLECTION).where('student_id', '==', student_id).limit(1).get()
            for user in users:
                data = user.to_dict()
                data['id'] = user.id
                return data
            return None
        except Exception as e:
            logger.error(f"Error getting user by student_id: {e}")
            return None
    
    @staticmethod
    def update(user_id, update_data):
        """Update user data"""
        try:
            db.collection(USERS_COLLECTION).document(user_id).update(update_data)
            logger.info(f"Updated user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    @staticmethod
    def update_last_login(user_id):
        """Update last login timestamp"""
        return User.update(user_id, {'last_login': datetime.utcnow()})
    
    @staticmethod
    def get_complaint_count(user_id):
        """Get complaint count for user"""
        try:
            complaints = db.collection(COMPLAINTS_COLLECTION).where('user_id', '==', user_id).get()
            return len(list(complaints))
        except Exception as e:
            logger.error(f"Error getting complaint count: {e}")
            return 0
    
    @staticmethod
    def get_complaints(user_id, limit=None):
        """Get user's complaints"""
        try:
            query = db.collection(COMPLAINTS_COLLECTION).where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING)
            if limit:
                query = query.limit(limit)
            
            complaints = []
            for doc in query.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                complaints.append(data)
            return complaints
        except Exception as e:
            logger.error(f"Error getting user complaints: {e}")
            return []

# ============================================================================
# COMPLAINT OPERATIONS
# ============================================================================

class Complaint:
    """Complaint model for Firestore"""
    
    @staticmethod
    def create(complaint_data):
        """Create a new complaint"""
        try:
            complaint_data['timestamp'] = datetime.utcnow()
            complaint_data['upvotes'] = 0
            
            doc_ref = db.collection(COMPLAINTS_COLLECTION).document()
            complaint_data['id'] = doc_ref.id
            doc_ref.set(complaint_data)
            
            logger.info(f"Created complaint: {doc_ref.id}")
            return complaint_data
        except Exception as e:
            logger.error(f"Error creating complaint: {e}")
            return None
    
    @staticmethod
    def get_by_id(complaint_id):
        """Get complaint by ID"""
        try:
            doc = db.collection(COMPLAINTS_COLLECTION).document(complaint_id).get()
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            return None
        except Exception as e:
            logger.error(f"Error getting complaint: {e}")
            return None
    
    @staticmethod
    def get_all(limit=None):
        """Get all complaints"""
        try:
            query = db.collection(COMPLAINTS_COLLECTION).order_by('timestamp', direction=firestore.Query.DESCENDING)
            if limit:
                query = query.limit(limit)
            
            complaints = []
            for doc in query.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                complaints.append(data)
            return complaints
        except Exception as e:
            logger.error(f"Error getting complaints: {e}")
            return []
    
    @staticmethod
    def update(complaint_id, update_data):
        """Update complaint"""
        try:
            db.collection(COMPLAINTS_COLLECTION).document(complaint_id).update(update_data)
            return True
        except Exception as e:
            logger.error(f"Error updating complaint: {e}")
            return False
    
    @staticmethod
    def increment_upvotes(complaint_id):
        """Increment upvotes for a complaint"""
        try:
            doc_ref = db.collection(COMPLAINTS_COLLECTION).document(complaint_id)
            doc_ref.update({'upvotes': firestore.Increment(1)})
            
            # Get updated count
            doc = doc_ref.get()
            return doc.to_dict().get('upvotes', 0) if doc.exists else 0
        except Exception as e:
            logger.error(f"Error incrementing upvotes: {e}")
            return None
    
    @staticmethod
    def count():
        """Count total complaints"""
        try:
            complaints = db.collection(COMPLAINTS_COLLECTION).get()
            return len(list(complaints))
        except Exception as e:
            logger.error(f"Error counting complaints: {e}")
            return 0
    
    @staticmethod
    def count_by_severity(severity):
        """Count complaints by severity"""
        try:
            complaints = db.collection(COMPLAINTS_COLLECTION).where('severity', '==', severity).get()
            return len(list(complaints))
        except Exception as e:
            logger.error(f"Error counting by severity: {e}")
            return 0
    
    @staticmethod
    def count_by_category(category):
        """Count complaints by category"""
        try:
            complaints = db.collection(COMPLAINTS_COLLECTION).where('category', '==', category).get()
            return len(list(complaints))
        except Exception as e:
            logger.error(f"Error counting by category: {e}")
            return 0
    
    @staticmethod
    def get_by_cluster(cluster_id, limit=None):
        """Get complaints by cluster ID"""
        try:
            query = db.collection(COMPLAINTS_COLLECTION).where('cluster_id', '==', cluster_id).order_by('timestamp', direction=firestore.Query.DESCENDING)
            if limit:
                query = query.limit(limit)
            
            complaints = []
            for doc in query.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                complaints.append(data)
            return complaints
        except Exception as e:
            logger.error(f"Error getting complaints by cluster: {e}")
            return []
    
    @staticmethod
    def set_embedding(complaint_id, embedding_array):
        """Store numpy array as base64 string"""
        try:
            if embedding_array is not None:
                if isinstance(embedding_array, list):
                    embedding_array = np.array(embedding_array)
                # Convert to bytes and then to base64 string for Firestore
                embedding_bytes = pickle.dumps(embedding_array)
                import base64
                embedding_str = base64.b64encode(embedding_bytes).decode('utf-8')
                Complaint.update(complaint_id, {'embedding': embedding_str})
        except Exception as e:
            logger.error(f"Error setting embedding: {e}")
    
    @staticmethod
    def get_embedding(complaint_data):
        """Retrieve numpy array from base64 string"""
        try:
            embedding_str = complaint_data.get('embedding')
            if embedding_str:
                import base64
                embedding_bytes = base64.b64decode(embedding_str)
                return pickle.loads(embedding_bytes)
            return None
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return None

# ============================================================================
# CATEGORY OPERATIONS
# ============================================================================

class Category:
    """Category model for Firestore"""
    
    @staticmethod
    def create(name, description=None):
        """Create a new category"""
        try:
            data = {
                'name': name,
                'description': description,
                'created_at': datetime.utcnow()
            }
            doc_ref = db.collection(CATEGORIES_COLLECTION).document()
            data['id'] = doc_ref.id
            doc_ref.set(data)
            
            logger.info(f"Created category: {name}")
            return data
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            return None
    
    @staticmethod
    def get_all():
        """Get all categories"""
        try:
            categories = []
            for doc in db.collection(CATEGORIES_COLLECTION).stream():
                data = doc.to_dict()
                data['id'] = doc.id
                categories.append(data)
            return categories
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []
    
    @staticmethod
    def get_by_name(name):
        """Get category by name"""
        try:
            cats = db.collection(CATEGORIES_COLLECTION).where('name', '==', name).limit(1).get()
            for cat in cats:
                data = cat.to_dict()
                data['id'] = cat.id
                return data
            return None
        except Exception as e:
            logger.error(f"Error getting category: {e}")
            return None
    
    @staticmethod
    def count():
        """Count categories"""
        try:
            categories = db.collection(CATEGORIES_COLLECTION).get()
            return len(list(categories))
        except Exception as e:
            logger.error(f"Error counting categories: {e}")
            return 0

# ============================================================================
# CLUSTER OPERATIONS
# ============================================================================

class IssueCluster:
    """Issue Cluster model for Firestore"""
    
    @staticmethod
    def create(cluster_data):
        """Create a new cluster"""
        try:
            cluster_data['last_updated'] = datetime.utcnow()
            cluster_data['count'] = cluster_data.get('count', 1)
            
            doc_ref = db.collection(CLUSTERS_COLLECTION).document()
            cluster_data['id'] = doc_ref.id
            doc_ref.set(cluster_data)
            
            logger.info(f"Created cluster: {doc_ref.id}")
            return cluster_data
        except Exception as e:
            logger.error(f"Error creating cluster: {e}")
            return None
    
    @staticmethod
    def get_by_id(cluster_id):
        """Get cluster by ID"""
        try:
            doc = db.collection(CLUSTERS_COLLECTION).document(cluster_id).get()
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            return None
        except Exception as e:
            logger.error(f"Error getting cluster: {e}")
            return None
    
    @staticmethod
    def get_all(limit=None):
        """Get all clusters"""
        try:
            query = db.collection(CLUSTERS_COLLECTION).order_by('count', direction=firestore.Query.DESCENDING)
            if limit:
                query = query.limit(limit)
            
            clusters = []
            for doc in query.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                clusters.append(data)
            return clusters
        except Exception as e:
            logger.error(f"Error getting clusters: {e}")
            return []
    
    @staticmethod
    def get_by_category_severity(category, severity):
        """Get clusters by category and severity"""
        try:
            clusters = []
            query = db.collection(CLUSTERS_COLLECTION)\
                .where('category', '==', category)\
                .where('severity', '==', severity)
            
            for doc in query.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                clusters.append(data)
            return clusters
        except Exception as e:
            logger.error(f"Error getting clusters by category/severity: {e}")
            return []
    
    @staticmethod
    def update(cluster_id, update_data):
        """Update cluster"""
        try:
            update_data['last_updated'] = datetime.utcnow()
            db.collection(CLUSTERS_COLLECTION).document(cluster_id).update(update_data)
            return True
        except Exception as e:
            logger.error(f"Error updating cluster: {e}")
            return False
    
    @staticmethod
    def update_count(cluster_id):
        """Update complaint count for cluster"""
        try:
            complaints = Complaint.get_by_cluster(cluster_id)
            count = len(complaints)
            IssueCluster.update(cluster_id, {'count': count})
            return count
        except Exception as e:
            logger.error(f"Error updating cluster count: {e}")
            return 0
    
    @staticmethod
    def delete(cluster_id):
        """Delete cluster"""
        try:
            db.collection(CLUSTERS_COLLECTION).document(cluster_id).delete()
            return True
        except Exception as e:
            logger.error(f"Error deleting cluster: {e}")
            return False
    
    @staticmethod
    def count():
        """Count clusters"""
        try:
            clusters = db.collection(CLUSTERS_COLLECTION).get()
            return len(list(clusters))
        except Exception as e:
            logger.error(f"Error counting clusters: {e}")
            return 0

# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize_categories():
    """Initialize default categories"""
    try:
        if Category.count() == 0:
            default_categories = [
                'Mess Food Quality',
                'Campus Wi-Fi',
                'Medical Center',
                'Placement/CDC',
                'Faculty Concerns',
                'Hostel Maintenance',
                'Other'
            ]
            
            for cat_name in default_categories:
                Category.create(cat_name)
            
            logger.info(f"Initialized {len(default_categories)} categories")
            return True
        return True
    except Exception as e:
        logger.error(f"Error initializing categories: {e}")
        return False
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Flask Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'True') == 'True'

# Database Configuration
DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///complaints.db')

# AI API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Gemini Model Configuration
GEMINI_MODEL = 'gemini-pro'
GEMINI_EMBEDDING_MODEL = 'models/embedding-001'

# Application Settings
MAX_COMPLAINT_LENGTH = 2000
EMBEDDING_DIMENSION = 768

# Clustering Configuration
SIMILARITY_THRESHOLD = 0.75  # Cosine similarity threshold for clustering
MIN_CLUSTER_SIZE = 2

# Severity Keywords
SEVERITY_HIGH_KEYWORDS = [
    'urgent', 'emergency', 'critical', 'dangerous', 'unsafe',
    'health risk', 'serious', 'immediate', 'broken', 'not working'
]

SEVERITY_MEDIUM_KEYWORDS = [
    'problem', 'issue', 'concern', 'delay', 'poor',
    'need attention', 'frustrating', 'inconvenient'
]

# Category Keywords
CATEGORY_KEYWORDS = {
    'Mess Food Quality': ['food', 'mess', 'meal', 'dining', 'kitchen', 'hygiene', 'quality'],
    'Campus Wi-Fi': ['wifi', 'internet', 'network', 'connection', 'slow', 'connectivity'],
    'Medical Center': ['medical', 'doctor', 'health', 'clinic', 'medicine', 'sick'],
    'Placement/CDC': ['placement', 'cdc', 'career', 'job', 'interview', 'company'],
    'Faculty Concerns': ['faculty', 'professor', 'teacher', 'teaching', 'class', 'course'],
    'Hostel Maintenance': ['hostel', 'room', 'maintenance', 'repair', 'cleaning', 'ac', 'water']
}
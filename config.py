import os
from dotenv import load_dotenv
import secrets

# Load environment variables
load_dotenv()

# Flask Configuration
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    print("WARNING: Using auto-generated SECRET_KEY. Set SECRET_KEY in .env for production!")

DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')

# Database Configuration
DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///complaints.db')

if not DATABASE_URI:
    raise ValueError("DATABASE_URI must be set in environment variables")

#college domain import from .env
ALLOWED_GOOGLE_DOMAIN = os.getenv("ALLOWED_GOOGLE_DOMAIN", "mycollege.ac.in")


# AI API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

if not GEMINI_API_KEY and not os.getenv('TESTING'):
    print("WARNING: GEMINI_API_KEY not set. AI features will not work!")

# Gemini Model Configuration
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-pro')
GEMINI_EMBEDDING_MODEL = os.getenv('GEMINI_EMBEDDING_MODEL', 'models/embedding-001')

# Application Settings
MAX_COMPLAINT_LENGTH = int(os.getenv('MAX_COMPLAINT_LENGTH', '2000'))
EMBEDDING_DIMENSION = int(os.getenv('EMBEDDING_DIMENSION', '768'))

if MAX_COMPLAINT_LENGTH < 100 or MAX_COMPLAINT_LENGTH > 10000:
    raise ValueError("MAX_COMPLAINT_LENGTH must be between 100 and 10000")

if EMBEDDING_DIMENSION < 1:
    raise ValueError("EMBEDDING_DIMENSION must be positive")

# Clustering Configuration
SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', '0.75'))
MIN_CLUSTER_SIZE = int(os.getenv('MIN_CLUSTER_SIZE', '2'))

if SIMILARITY_THRESHOLD < 0 or SIMILARITY_THRESHOLD > 1:
    raise ValueError("SIMILARITY_THRESHOLD must be between 0 and 1")

if MIN_CLUSTER_SIZE < 1:
    raise ValueError("MIN_CLUSTER_SIZE must be at least 1")

# General Rate Limiting
# RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() in ('true', '1', 't')
RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '10'))
RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() in ('true', '1', 't')
RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')  # Use Redis in production
RATELIMIT_STRATEGY = 'fixed-window'  # or 'moving-window'
RATELIMIT_HEADERS_ENABLED = True  # Send rate limit info in headers

# Authentication specific limits
AUTH_RATE_LIMIT_LOGIN = os.getenv('AUTH_RATE_LIMIT_LOGIN', '5 per 15 minutes')
AUTH_RATE_LIMIT_REGISTER = os.getenv('AUTH_RATE_LIMIT_REGISTER', '3 per hour')
AUTH_RATE_LIMIT_PASSWORD_CHANGE = os.getenv('AUTH_RATE_LIMIT_PASSWORD_CHANGE', '3 per hour')
AUTH_RATE_LIMIT_FIREBASE = os.getenv('AUTH_RATE_LIMIT_FIREBASE', '10 per 15 minutes')

# General API limits
API_RATE_LIMIT_DEFAULT = os.getenv('API_RATE_LIMIT_DEFAULT', '100 per hour')
API_RATE_LIMIT_UPVOTE = os.getenv('API_RATE_LIMIT_UPVOTE', '30 per minute')

# ============================================================================
# ENHANCED SEVERITY KEYWORDS - COMPREHENSIVE MEDICAL & SAFETY TERMS
# ============================================================================

# CRITICAL/HIGH SEVERITY - Requires immediate action (within hours)
SEVERITY_HIGH_KEYWORDS = tuple([
    # Medical Emergencies & Hospitalization
    'hospital', 'hospitalized', 'hospitalization', 'admitted', 'admission',
    'emergency room', 'er', 'er visit', 'ambulance', 'paramedic',
    'medical emergency', 'health emergency', 'urgent care',
    
    # Injuries & Physical Harm
    'injury', 'injured', 'hurt', 'wounded', 'trauma',
    'broken bone', 'fracture', 'sprain', 'dislocation',
    'bleeding', 'blood', 'hemorrhage', 'cut badly',
    'unconscious', 'fainted', 'collapsed', 'passed out',
    'concussion', 'head injury', 'severe pain',
    
    # Poisoning & Contamination
    'poisoning', 'poison', 'poisoned', 'toxic', 'toxin',
    'food poisoning', 'food contamination', 'contaminated',
    'chemical exposure', 'gas leak', 'fumes',
    
    # Severe Illness
    'severe illness', 'critically ill', 'life-threatening',
    'difficulty breathing', 'can\'t breathe', 'breathing problem',
    'chest pain', 'heart attack', 'cardiac', 'stroke',
    'seizure', 'convulsion', 'anaphylaxis', 'allergic shock',
    'high fever', 'severe fever', 'vomiting blood',
    'multiple students sick', 'outbreak', 'epidemic',
    
    # Safety Hazards
    'fire', 'flames', 'burning', 'smoke', 'fire hazard',
    'electrical shock', 'electrocuted', 'live wire', 'exposed wire',
    'gas leak', 'carbon monoxide', 'co detector',
    'structural damage', 'building unsafe', 'collapse', 'collapsing',
    'ceiling falling', 'ceiling collapsed', 'wall crack', 'foundation',
    'flood', 'flooding', 'water damage severe',
    
    # Violence & Threats
    'assault', 'assaulted', 'attacked', 'violence', 'violent',
    'threat', 'threatened', 'threatening', 'intimidation',
    'harassment', 'sexual harassment', 'abuse', 'abused',
    'rape', 'sexual assault', 'molested', 'groped',
    'fight', 'physical altercation', 'stabbed', 'weapon',
    
    # Critical Service Failures
    'no water for days', 'no water multiple days', 'water cut off',
    'no electricity days', 'power out days', 'blackout days',
    'no heating winter', 'freezing', 'extreme cold',
    'no cooling summer', 'extreme heat', 'heat stroke',
    'sewage backup', 'sewage overflow', 'toilet overflow',
    'raw sewage', 'sewage leak',
    
    # Severe Hygiene Issues
    'maggots', 'worms in food', 'rat in food', 'mouse in food',
    'cockroach in food', 'insect in food', 'bugs in food',
    'rotten food', 'spoiled food', 'moldy food', 'mold everywhere',
    'food made sick', 'food caused illness', 'food safety',
    'unsanitary', 'unhygienic', 'filthy conditions',
    
    # Mental Health Crises
    'suicidal', 'suicide', 'want to die', 'kill myself',
    'mental breakdown', 'mental crisis', 'severe depression',
    'severe anxiety', 'panic attack severe',
    
    # Dangerous Conditions
    'dangerous', 'hazardous', 'deadly', 'fatal',
    'life at risk', 'safety risk', 'immediate danger',
    'urgent', 'emergency', 'critical', 'dire',
    'unsafe conditions', 'hazard', 'peril',
    
    # Repeated Critical Issues
    'ignored for weeks', 'reported many times', 'still not fixed critical',
    'getting worse', 'escalating', 'emergency situation'
])

# MEDIUM SEVERITY - Needs attention (within days/weeks)
SEVERITY_MEDIUM_KEYWORDS = tuple([
    # Service Issues
    'problem', 'issue', 'concern', 'trouble', 'difficulty',
    'malfunction', 'malfunctioning', 'not working properly',
    'faulty', 'defective', 'broken', 'damaged',
    'out of order', 'stopped working', 'doesn\'t work',
    
    # Quality Issues
    'poor quality', 'bad quality', 'low quality', 'substandard',
    'inadequate', 'insufficient', 'lacking', 'poor service',
    'unacceptable', 'disappointing', 'unsatisfactory',
    
    # Performance Issues
    'slow', 'very slow', 'sluggish', 'lagging', 'delay',
    'delayed', 'taking too long', 'wait time', 'waiting forever',
    'inconsistent', 'unreliable', 'spotty', 'intermittent',
    
    # Maintenance Needs
    'needs repair', 'needs fixing', 'needs maintenance',
    'leaking', 'leak', 'dripping', 'water leak',
    'clogged', 'blocked', 'stuck', 'jammed',
    'worn out', 'deteriorating', 'degraded',
    
    # Inconvenience
    'inconvenient', 'inconvenience', 'frustrating', 'annoying',
    'bothersome', 'troublesome', 'problematic',
    'uncomfortable', 'unpleasant', 'difficult to use',
    
    # Attention Needed
    'need attention', 'requires attention', 'should be fixed',
    'needs improvement', 'could be better', 'not good enough',
    'disappointing', 'expected better', 'falling short',
    
    # Academic Concerns
    'unfair grading', 'biased', 'discrimination', 'favoritism',
    'poor teaching', 'difficult to understand', 'unclear',
    'disorganized', 'unprepared', 'unprofessional',
    
    # Communication Issues
    'no response', 'didn\'t respond', 'ignored email',
    'can\'t reach', 'unavailable', 'not responding',
    'poor communication', 'lack of information',
    
    # Recurring Issues
    'again', 'another time', 'still happening', 'continues',
    'ongoing', 'persistent', 'recurring', 'repeated'
])

# LOW SEVERITY - Minor issues, suggestions (no specific timeline)
SEVERITY_LOW_KEYWORDS = tuple([
    'suggestion', 'recommend', 'could improve', 'would be nice',
    'minor', 'small', 'aesthetic', 'cosmetic',
    'preference', 'opinion', 'feedback', 'idea'
])

# Category Keywords (immutable)
CATEGORY_KEYWORDS = {
    'Mess Food Quality': tuple([
        'food', 'mess', 'meal', 'dining', 'kitchen', 'hygiene', 'quality', 
        'cafeteria', 'restaurant', 'breakfast', 'lunch', 'dinner',
        'menu', 'taste', 'portion', 'serving', 'chef', 'cooking'
    ]),
    'Campus Wi-Fi': tuple([
        'wifi', 'wi-fi', 'internet', 'network', 'connection', 'slow', 
        'connectivity', 'bandwidth', 'router', 'signal', 'speed',
        'online', 'disconnect', 'lag', 'latency'
    ]),
    'Medical Center': tuple([
        'medical', 'doctor', 'health', 'clinic', 'medicine', 'sick', 
        'hospital', 'nurse', 'first aid', 'physician', 'treatment',
        'prescription', 'appointment', 'emergency', 'healthcare'
    ]),
    'Placement/CDC': tuple([
        'placement', 'cdc', 'career', 'job', 'interview', 'company', 
        'recruitment', 'internship', 'hiring', 'recruiter',
        'employment', 'opportunity', 'resume', 'portfolio'
    ]),
    'Faculty Concerns': tuple([
        'faculty', 'professor', 'teacher', 'teaching', 'class', 'course', 
        'lecture', 'instructor', 'tutor', 'academic', 'assignment',
        'exam', 'grade', 'evaluation', 'curriculum'
    ]),
    'Hostel Maintenance': tuple([
        'hostel', 'room', 'maintenance', 'repair', 'cleaning', 'ac', 'water', 
        'plumbing', 'electricity', 'bed', 'furniture', 'bathroom',
        'shower', 'toilet', 'door', 'window', 'fan', 'light'
    ])
}

# Email Configuration (optional)
MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'app.log')

# Session Configuration
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
PERMANENT_SESSION_LIFETIME = int(os.getenv('SESSION_LIFETIME', '3600'))

# CSRF Protection
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None

# File Upload Configuration
MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', str(16 * 1024 * 1024)))
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_AUTH_DOMAIN = os.getenv("FIREBASE_AUTH_DOMAIN")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")
FIREBASE_MSG_SENDER_ID = os.getenv("FIREBASE_MSG_SENDER_ID")
FIREBASE_APP_ID = os.getenv("FIREBASE_APP_ID")



def validate_config():
    """
    Validate all configuration settings
    
    Raises:
        ValueError: If any configuration is invalid
    """
    errors = []
    
    if not SECRET_KEY:
        errors.append("SECRET_KEY is required")
    
    if not DATABASE_URI:
        errors.append("DATABASE_URI is required")
    
    if RATE_LIMIT_PER_MINUTE < 1:
        errors.append("RATE_LIMIT_PER_MINUTE must be positive")
    
    if PERMANENT_SESSION_LIFETIME < 60:
        errors.append("PERMANENT_SESSION_LIFETIME must be at least 60 seconds")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True

# Validate on import
try:
    validate_config()
except ValueError as e:
    print(f"Configuration validation failed: {e}")
    if not DEBUG:
        raise
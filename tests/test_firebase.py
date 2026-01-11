from dotenv import load_dotenv
load_dotenv()

import firebase_admin
from firebase_admin import credentials, firestore
import os

print("Testing Firebase Connection...")
print("=" * 60)

# Method 1: Try service account file first
if os.path.exists('firebase_service_account.json'):
    print("✓ Found firebase_service_account.json")
    cred = credentials.Certificate('firebase_service_account.json')
else:
    # Method 2: Use environment variables
    print("✓ Using environment variables")
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

# Initialize
firebase_admin.initialize_app(cred)
print("✓ Firebase Admin initialized")

# Test Firestore
db = firestore.client()
print("✓ Firestore client created")

# Test write
test_ref = db.collection('test').document('test_doc')
test_ref.set({'message': 'Hello from CICP!', 'timestamp': firestore.SERVER_TIMESTAMP})
print("✓ Test write successful")

# Test read
doc = test_ref.get()
if doc.exists:
    print(f"✓ Test read successful: {doc.to_dict()}")

# Clean up
test_ref.delete()
print("✓ Test cleanup successful")

print("=" * 60)
print("🎉 Firebase is working perfectly!")
"""
Debug script to test authentication system
Run this to verify user creation and session handling
"""

from database.firebase_models import User
from auth.auth import login_user
from flask import Flask, session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_authentication():
    """Test the complete authentication flow"""
    print("=" * 60)
    print("AUTHENTICATION SYSTEM TEST")
    print("=" * 60)
    print()
    
    # Step 1: Check if any users exist
    print("Step 1: Checking existing users...")
    user = User.get_by_email(test_email)
    if user:
        print(f"✓ Found existing user: {user['email']}")
        print(f"  Name: {user['name']}")
        print(f"  Student ID: {user['student_id']}")
        print(f"  Is Google: {user.get('is_google', False)}")
    else:
        print(f"✗ No user found with email: {test_email}")
        print()
        print("Step 2: Creating test user...")
        
        user_data = {
            'name': 'Test User',
            'email': test_email,
            'student_id': 'TEST001',
            'password_hash': 'test_hash',  # Not a real hash for testing
            'is_google': False,
            'is_admin': False,
            'is_active': True,
            'email_verified': False
        }
        
        user = User.create(user_data)
        
        if user:
            print(f"✓ Test user created: {user['email']}")
        else:
            print("✗ Failed to create test user")
            return False
    
    print()
    print("Step 3: Testing login_user() function...")
    
    # Create a minimal Flask app to test session
    app = Flask(__name__)
    app.secret_key = 'test-secret-key'
    
    with app.test_request_context():
        # Test login_user
        login_user(user)
        
        # Check session
        print(f"  logged_in: {session.get('logged_in')}")
        print(f"  user_id: {session.get('user_id')}")
        print(f"  email: {session.get('email')}")
        print(f"  name: {session.get('name')}")
        print(f"  student_id: {session.get('student_id')}")
        
        if session.get('logged_in') and session.get('user_id'):
            print("✓ Session set correctly")
            print()
            print("=" * 60)
            print("✅ AUTHENTICATION SYSTEM IS WORKING!")
            print("=" * 60)
            return True
        else:
            print("✗ Session NOT set correctly")
            print()
            print("=" * 60)
            print("❌ AUTHENTICATION SYSTEM HAS ISSUES")
            print("=" * 60)
            return False


def check_all_users():
    """List all users in the database"""
    print()
    print("=" * 60)
    print("ALL USERS IN DATABASE")
    print("=" * 60)
    
    try:
        from firebase_admin import firestore
        db = firestore.client()
        users = db.collection('users').stream()
        
        count = 0
        for doc in users:
            count += 1
            data = doc.to_dict()
            print(f"\n{count}. {data.get('name')}")
            print(f"   Email: {data.get('email')}")
            print(f"   Student ID: {data.get('student_id')}")
            print(f"   Is Google: {data.get('is_google', False)}")
            print(f"   Created: {data.get('created_at')}")
        
        print()
        print(f"Total users: {count}")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error listing users: {e}")


if __name__ == "__main__":
    # Test authentication
    success = test_authentication()
    
    # List all users
    check_all_users()
    
    if success:
        print()
        print("🎉 Your authentication system is working!")
        print()
        print("Next steps:")
        print("1. Restart your Flask app: python app.py")
        print("2. Try registering: http://localhost:5000/register")
        print("3. Try Google Sign-In: http://localhost:5000/login")
    else:
        print()
        print("⚠️  Authentication system needs fixes!")
        print()
        print("Please check:")
        print("1. auth/auth.py - login_user() function")
        print("2. auth/firebase_auth.py - firebase_login() route")
        print("3. app.py - SECRET_KEY is set")
        print("4. Session configuration in app.py")
"""
Test script to check profile data
Run this to verify user complaints are being fetched correctly
"""

from database.firebase_models import User, Complaint
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_profile_data():
    """Test profile data retrieval"""
    print("=" * 60)
    print("TESTING PROFILE DATA")
    print("=" * 60)
    print()
    
    # Get all users
    try:
        from firebase_admin import firestore
        db = firestore.client()
        users = list(db.collection('users').stream())
        
        print(f"Found {len(users)} users in database")
        print()
        
        if not users:
            print("⚠️  No users found! Register first.")
            return
        
        # Test each user's complaints
        for user_doc in users:
            user = user_doc.to_dict()
            user['id'] = user_doc.id
            
            print(f"User: {user['name']} ({user['email']})")
            print(f"User ID: {user['id']}")
            print()
            
            # Method 1: Get all complaints and filter
            print("Method 1: Filter all complaints by user_id")
            all_complaints = Complaint.get_all()
            user_complaints = [c for c in all_complaints if c.get('user_id') == user['id']]
            print(f"  Found {len(user_complaints)} complaints")
            
            if user_complaints:
                for i, complaint in enumerate(user_complaints, 1):
                    print(f"  {i}. {complaint.get('category')} - {complaint.get('severity')}")
                    print(f"     Text: {complaint.get('rewritten_text', '')[:50]}...")
            
            print()
            
            # Check why complaints might be missing
            print("Checking all complaints for user_id match:")
            for complaint in all_complaints[:5]:  # Just first 5
                print(f"  - Complaint user_id: {complaint.get('user_id')}")
                print(f"    Matches: {complaint.get('user_id') == user['id']}")
            
            print()
            print("-" * 60)
            print()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def check_complaint_user_ids():
    """Check all complaint user_ids"""
    print("=" * 60)
    print("CHECKING COMPLAINT USER IDs")
    print("=" * 60)
    print()
    
    try:
        all_complaints = Complaint.get_all()
        
        print(f"Total complaints: {len(all_complaints)}")
        print()
        
        user_id_stats = {}
        for complaint in all_complaints:
            user_id = complaint.get('user_id')
            if user_id:
                user_id_stats[user_id] = user_id_stats.get(user_id, 0) + 1
            else:
                user_id_stats['None'] = user_id_stats.get('None', 0) + 1
        
        print("Complaints by user_id:")
        for user_id, count in user_id_stats.items():
            print(f"  {user_id}: {count} complaints")
        
        print()
        
        if 'None' in user_id_stats:
            print(f"⚠️  {user_id_stats['None']} complaints have no user_id!")
            print("This means they were submitted anonymously or before login.")
            print()
            
            # Show these complaints
            print("Complaints without user_id:")
            for complaint in all_complaints:
                if not complaint.get('user_id'):
                    print(f"  - {complaint.get('id')}: {complaint.get('category')}")
                    print(f"    Student ID: {complaint.get('student_id')}")
                    print(f"    Timestamp: {complaint.get('timestamp')}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_profile_data()
    print()
    check_complaint_user_ids()
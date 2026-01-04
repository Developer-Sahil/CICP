"""
Debug script to check complaints in Firestore
FIXED: Uses existing Firebase initialization
"""

from database.firebase_models import Complaint, IssueCluster, Category, db
from utils.firebase_helpers import get_dashboard_stats, get_recent_complaints
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_complaints():
    """Check all complaints in database"""
    print("=" * 60)
    print("CHECKING COMPLAINTS IN FIRESTORE")
    print("=" * 60)
    print()
    
    # Method 1: Using Complaint.get_all()
    print("Method 1: Using Complaint.get_all()")
    print("-" * 60)
    try:
        complaints = Complaint.get_all()
        print(f"✓ Found {len(complaints)} complaints")
        
        if complaints:
            print("\nFirst 5 complaints:")
            for i, complaint in enumerate(complaints[:5], 1):
                print(f"\n{i}. ID: {complaint.get('id')}")
                print(f"   Category: {complaint.get('category')}")
                print(f"   Severity: {complaint.get('severity')}")
                print(f"   Text: {complaint.get('rewritten_text', '')[:50]}...")
                print(f"   Timestamp: {complaint.get('timestamp')}")
                print(f"   Student ID: {complaint.get('student_id')}")
                print(f"   Upvotes: {complaint.get('upvotes', 0)}")
        else:
            print("⚠️  No complaints found!")
    except Exception as e:
        print(f"✗ Error using Complaint.get_all(): {e}")
    
    print()
    
    # Method 2: Direct Firestore query using existing db
    print("Method 2: Direct Firestore query")
    print("-" * 60)
    try:
        docs = list(db.collection('complaints').stream())
        print(f"✓ Found {len(docs)} complaint documents")
        
        if docs:
            print("\nFirst 5 documents:")
            for i, doc in enumerate(docs[:5], 1):
                data = doc.to_dict()
                print(f"\n{i}. Document ID: {doc.id}")
                print(f"   Fields: {list(data.keys())}")
                print(f"   Category: {data.get('category')}")
                print(f"   Severity: {data.get('severity')}")
        else:
            print("⚠️  No complaint documents found!")
    except Exception as e:
        print(f"✗ Error querying Firestore: {e}")
    
    print()
    
    # Method 3: Check dashboard stats
    print("Method 3: Dashboard statistics")
    print("-" * 60)
    try:
        stats = get_dashboard_stats()
        print(f"✓ Total complaints: {stats.get('total_complaints', 0)}")
        print(f"✓ High severity: {stats.get('severity_stats', {}).get('high', 0)}")
        print(f"✓ Medium severity: {stats.get('severity_stats', {}).get('medium', 0)}")
        print(f"✓ Low severity: {stats.get('severity_stats', {}).get('low', 0)}")
        print(f"✓ Total clusters: {stats.get('total_clusters', 0)}")
        print(f"✓ Recent (7 days): {stats.get('recent_complaints', 0)}")
        
        if stats.get('category_stats'):
            print("\nCategory breakdown:")
            for category, count in stats.get('category_stats', {}).items():
                print(f"  - {category}: {count}")
    except Exception as e:
        print(f"✗ Error getting stats: {e}")
    
    print()
    
    # Method 4: Check recent complaints
    print("Method 4: Recent complaints")
    print("-" * 60)
    try:
        recent = get_recent_complaints(limit=5)
        print(f"✓ Found {len(recent)} recent complaints")
        
        if recent:
            print("\nRecent complaints:")
            for i, complaint in enumerate(recent, 1):
                print(f"\n{i}. {complaint.get('category')} - {complaint.get('severity')}")
                print(f"   Text: {complaint.get('rewritten_text', '')[:50]}...")
                print(f"   Time: {complaint.get('timestamp')}")
    except Exception as e:
        print(f"✗ Error getting recent: {e}")
    
    print()
    
    # Check clusters
    print("Method 5: Check clusters")
    print("-" * 60)
    try:
        clusters = IssueCluster.get_all()
        print(f"✓ Found {len(clusters)} clusters")
        
        if clusters:
            print("\nClusters:")
            for i, cluster in enumerate(clusters, 1):
                print(f"\n{i}. {cluster.get('cluster_name')}")
                print(f"   Category: {cluster.get('category')}")
                print(f"   Severity: {cluster.get('severity')}")
                print(f"   Count: {cluster.get('count', 0)}")
    except Exception as e:
        print(f"✗ Error getting clusters: {e}")
    
    print()
    print("=" * 60)
    print("DIAGNOSIS")
    print("=" * 60)
    
    # Count total using existing db
    try:
        total = len(list(db.collection('complaints').stream()))
        
        if total == 0:
            print("⚠️  NO COMPLAINTS IN DATABASE")
            print()
            print("Possible reasons:")
            print("1. Complaints were not actually saved during submission")
            print("2. Firestore rules are blocking reads")
            print("3. Wrong collection name being used")
            print()
            print("Next steps:")
            print("1. Try submitting a new complaint at http://localhost:5000/submit")
            print("2. Check Flask console for errors during submission")
            print("3. Check Firestore Console: https://console.firebase.google.com")
            print("4. Verify Firestore rules allow reads")
        else:
            print(f"✓ Database has {total} complaints")
            print()
            if total > 0:
                print("Dashboard should show these complaints!")
                print()
                print("If dashboard is still empty:")
                print("1. Check browser console (F12) for JavaScript errors")
                print("2. Check Flask logs when loading /dashboard")
                print("3. Try hard refresh (Ctrl+Shift+R)")
            else:
                print("Dashboard is correctly showing 0 complaints.")
    except Exception as e:
        print(f"✗ Error checking database: {e}")


def test_complaint_submission():
    """Test creating a complaint"""
    print()
    print("=" * 60)
    print("TESTING COMPLAINT CREATION")
    print("=" * 60)
    print()
    
    try:
        test_complaint = {
            'user_id': None,
            'student_id': 'TEST123',
            'raw_text': 'This is a test complaint for debugging',
            'rewritten_text': 'This is a professionally rewritten test complaint for debugging purposes.',
            'category': 'Other',
            'severity': 'low',
            'cluster_id': None,
            'upvotes': 0
        }
        
        print("Creating test complaint...")
        complaint = Complaint.create(test_complaint)
        
        if complaint:
            print(f"✓ Test complaint created with ID: {complaint['id']}")
            print()
            print("Now:")
            print("1. Go to http://localhost:5000/dashboard")
            print("2. You should see 1 complaint")
            print("3. Check Firestore Console to verify")
            return True
        else:
            print("✗ Failed to create test complaint")
            return False
    except Exception as e:
        print(f"✗ Error creating test complaint: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Check existing complaints
    check_complaints()
    
    # Ask if user wants to create test complaint
    print()
    response = input("Create a test complaint? (y/n): ").lower()
    if response == 'y':
        if test_complaint_submission():
            print()
            print("Checking database again...")
            check_complaints()
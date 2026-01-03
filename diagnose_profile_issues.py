"""
Diagnostic script to check profile-related database issues
"""
from app import app, db
from sqlalchemy import inspect, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def diagnose_profile_issues():
    """Diagnose profile-related issues"""
    with app.app_context():
        print("=" * 70)
        print("PROFILE ISSUES DIAGNOSTIC")
        print("=" * 70)
        print()
        
        # Check 1: Verify users table structure
        print("1. Checking Users Table Structure...")
        try:
            inspector = inspect(db.engine)
            
            if 'users' not in inspector.get_table_names():
                print("  ✗ CRITICAL: Users table does not exist!")
                print("  → Run: python migrate_add_users.py migrate")
                return False
            
            user_columns = [col['name'] for col in inspector.get_columns('users')]
            required_cols = ['id', 'student_id', 'email', 'password_hash', 'name', 
                           'is_admin', 'is_active', 'created_at']
            
            missing = [col for col in required_cols if col not in user_columns]
            
            if missing:
                print(f"  ✗ Missing columns in users table: {missing}")
                return False
            else:
                print(f"  ✓ Users table has all required columns ({len(user_columns)} total)")
            
        except Exception as e:
            print(f"  ✗ Error checking users table: {e}")
            return False
        print()
        
        # Check 2: Count users
        print("2. Checking User Records...")
        try:
            user_count = User.query.count()
            print(f"  Total users: {user_count}")
            
            if user_count == 0:
                print("  ⚠ No users found!")
                print("  → Create a user: python create_admin.py")
                print("  → Or register at: http://localhost:5000/register")
                return False
            else:
                print("  ✓ Users exist in database")
                
                # Show first user
                first_user = User.query.first()
                print(f"\n  Sample user:")
                print(f"    ID: {first_user.id}")
                print(f"    Student ID: {first_user.student_id}")
                print(f"    Email: {first_user.email}")
                print(f"    Name: {first_user.name}")
                print(f"    Is Admin: {first_user.is_admin}")
                print(f"    Is Active: {first_user.is_active}")
                
        except Exception as e:
            print(f"  ✗ Error querying users: {e}")
            return False
        print()
        
        # Check 3: Verify complaints relationship
        print("3. Checking User-Complaint Relationship...")
        try:
            inspector = inspect(db.engine)
            complaint_columns = [col['name'] for col in inspector.get_columns('complaints')]
            
            if 'user_id' not in complaint_columns:
                print("  ✗ user_id column missing in complaints table!")
                print("  → Run: python fix_all_database_issues.py")
                return False
            else:
                print("  ✓ user_id column exists in complaints table")
            
            # Test relationship
            first_user = User.query.first()
            try:
                complaint_count = first_user.complaints.count()
                print(f"  ✓ User relationship works (user has {complaint_count} complaints)")
            except Exception as e:
                print(f"  ✗ Error accessing user.complaints: {e}")
                return False
                
        except Exception as e:
            print(f"  ✗ Error checking relationship: {e}")
            return False
        print()
        
        # Check 4: Test complaint queries
        print("4. Testing Complaint Queries...")
        try:
            first_user = User.query.first()
            
            # Test severity counts
            high = first_user.complaints.filter_by(severity='high').count()
            medium = first_user.complaints.filter_by(severity='medium').count()
            low = first_user.complaints.filter_by(severity='low').count()
            
            print(f"  ✓ Severity counts: High={high}, Medium={medium}, Low={low}")
            
            # Test recent complaints
            recent = first_user.complaints.order_by(
                Complaint.timestamp.desc()
            ).limit(5).all()
            
            print(f"  ✓ Recent complaints query works ({len(recent)} found)")
            
            # Test category breakdown
            from sqlalchemy import func
            breakdown = dict(
                db.session.query(
                    Complaint.category,
                    func.count(Complaint.id)
                ).filter(
                    Complaint.user_id == first_user.id
                ).group_by(
                    Complaint.category
                ).all()
            )
            
            print(f"  ✓ Category breakdown works ({len(breakdown)} categories)")
            
        except Exception as e:
            print(f"  ✗ Error testing queries: {e}")
            import traceback
            traceback.print_exc()
            return False
        print()
        
        # Check 5: Test profile template requirements
        print("5. Checking Profile Data Requirements...")
        try:
            first_user = User.query.first()
            
            # Check all fields that profile.html needs
            required_fields = {
                'id': first_user.id,
                'student_id': first_user.student_id,
                'email': first_user.email,
                'name': first_user.name,
                'department': first_user.department,
                'year': first_user.year,
                'hostel': first_user.hostel,
                'room_number': first_user.room_number,
                'is_admin': first_user.is_admin,
                'created_at': first_user.created_at
            }
            
            print("  User fields:")
            for field, value in required_fields.items():
                print(f"    {field}: {value if value is not None else 'None'}")
            
            print("  ✓ All required fields accessible")
            
        except Exception as e:
            print(f"  ✗ Error accessing user fields: {e}")
            import traceback
            traceback.print_exc()
            return False
        print()
        
        # Check 6: Verify upvotes column
        print("6. Checking Upvotes Column...")
        try:
            inspector = inspect(db.engine)
            complaint_columns = [col['name'] for col in inspector.get_columns('complaints')]
            
            if 'upvotes' not in complaint_columns:
                print("  ✗ upvotes column missing!")
                print("  → Run: python add_upvotes_column.py")
                return False
            else:
                print("  ✓ upvotes column exists")
                
                # Test upvotes
                complaint = Complaint.query.first()
                if complaint:
                    print(f"  ✓ Sample complaint upvotes: {complaint.upvotes}")
                
        except Exception as e:
            print(f"  ✗ Error checking upvotes: {e}")
            return False
        print()
        
        print("=" * 70)
        print("DIAGNOSTIC SUMMARY")
        print("=" * 70)
        print("✓ All checks passed!")
        print()
        print("If profile still doesn't work, try:")
        print("1. Clear browser cache and cookies")
        print("2. Logout and login again")
        print("3. Check browser console for JavaScript errors")
        print("4. Check app.log for detailed error messages")
        print()
        
        return True

if __name__ == '__main__':
    try:
        success = diagnose_profile_issues()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Critical error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

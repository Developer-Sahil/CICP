"""
Database migration script to add User model and user_id to complaints
Run this after updating models.py
"""
from app import app, db
from database.models import User, Complaint, Category, IssueCluster
from sqlalchemy import inspect, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        logger.error(f"Error checking column: {e}")
        return False

def check_table_exists(table_name):
    """Check if a table exists"""
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        return table_name in tables
    except Exception as e:
        logger.error(f"Error checking table: {e}")
        return False

def migrate():
    """Run migration"""
    print("=" * 70)
    print("DATABASE MIGRATION: Adding User Authentication")
    print("=" * 70)
    print()
    
    with app.app_context():
        try:
            # Step 1: Create all tables (will create users table if not exists)
            print("Step 1: Creating tables...")
            db.create_all()
            print("✓ All tables created/verified")
            print()
            
            # Step 2: Check if users table exists
            print("Step 2: Checking users table...")
            if check_table_exists('users'):
                user_count = User.query.count()
                print(f"✓ Users table exists with {user_count} users")
            else:
                print("✗ Users table not found - this shouldn't happen after create_all()")
                return False
            print()
            
            # Step 3: Add user_id column to complaints if it doesn't exist
            print("Step 3: Checking complaints table...")
            if check_column_exists('complaints', 'user_id'):
                print("✓ user_id column already exists in complaints table")
            else:
                print("Adding user_id column to complaints table...")
                try:
                    # SQLite-compatible way to add column
                    with db.engine.connect() as conn:
                        conn.execute(text('ALTER TABLE complaints ADD COLUMN user_id INTEGER'))
                        conn.commit()
                    print("✓ user_id column added successfully")
                    
                    # Try to add index (might fail on SQLite, that's OK)
                    try:
                        with db.engine.connect() as conn:
                            conn.execute(text('CREATE INDEX ix_complaints_user_id ON complaints(user_id)'))
                            conn.commit()
                        print("✓ Index created on user_id")
                    except Exception as e:
                        print(f"Note: Could not create index (not critical): {e}")
                        
                except Exception as e:
                    logger.error(f"Error adding user_id column: {e}")
                    print(f"✗ Error: {e}")
                    print("\nIf using SQLite, you may need to recreate the database.")
                    print("To preserve data, export complaints first.")
                    return False
            print()
            
            # Step 4: Verify all tables
            print("Step 4: Verifying database structure...")
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = ['users', 'complaints', 'categories', 'issue_clusters']
            for table in required_tables:
                if table in tables:
                    print(f"✓ {table} table exists")
                else:
                    print(f"✗ {table} table missing!")
                    return False
            print()
            
            # Step 5: Show complaints table structure
            print("Step 5: Complaints table structure:")
            complaint_columns = inspector.get_columns('complaints')
            for col in complaint_columns:
                print(f"  - {col['name']}: {col['type']}")
            print()
            
            # Step 6: Statistics
            print("Step 6: Database statistics:")
            print(f"  Users: {User.query.count()}")
            print(f"  Complaints: {Complaint.query.count()}")
            print(f"  Categories: {Category.query.count()}")
            print(f"  Clusters: {IssueCluster.query.count()}")
            print()
            
            # Step 7: Check for orphaned complaints
            print("Step 7: Checking data integrity...")
            total_complaints = Complaint.query.count()
            complaints_with_users = Complaint.query.filter(Complaint.user_id.isnot(None)).count()
            orphaned = total_complaints - complaints_with_users
            
            print(f"  Total complaints: {total_complaints}")
            print(f"  Linked to users: {complaints_with_users}")
            print(f"  Without user link: {orphaned}")
            
            if orphaned > 0:
                print(f"\n  Note: {orphaned} complaints were submitted before user system")
                print("  These will continue to work as anonymous complaints")
            print()
            
            print("=" * 70)
            print("✓ MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print()
            print("Next steps:")
            print("1. Restart your Flask application")
            print("2. Test registration at /register")
            print("3. Test login at /login")
            print("4. Create admin user: python create_admin.py")
            print()
            
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            print(f"\n✗ Migration failed: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure models.py is updated with User model")
            print("2. Check that Flask app is configured correctly")
            print("3. Verify database file permissions")
            print("4. Try: python repair_database.py")
            return False

def rollback():
    """
    Rollback migration (remove user_id column)
    WARNING: This will break authentication!
    """
    print("=" * 70)
    print("ROLLBACK: Removing User Authentication")
    print("=" * 70)
    print()
    print("⚠️  WARNING: This will remove all user data and break authentication!")
    confirm = input("Type 'ROLLBACK' to confirm: ")
    
    if confirm != 'ROLLBACK':
        print("Cancelled.")
        return
    
    with app.app_context():
        try:
            # Drop users table
            if check_table_exists('users'):
                User.__table__.drop(db.engine)
                print("✓ Dropped users table")
            
            # Remove user_id column from complaints
            if check_column_exists('complaints', 'user_id'):
                # Note: SQLite doesn't support DROP COLUMN
                print("✗ Cannot drop user_id column in SQLite")
                print("You'll need to recreate the complaints table manually")
            
            print("\n✓ Rollback completed")
            
        except Exception as e:
            print(f"✗ Rollback failed: {e}")

def fresh_start():
    """
    Create fresh database with all tables
    WARNING: This deletes all existing data!
    """
    print("=" * 70)
    print("FRESH START: Creating New Database")
    print("=" * 70)
    print()
    print("⚠️  WARNING: This will DELETE ALL existing data!")
    confirm = input("Type 'DELETE ALL DATA' to confirm: ")
    
    if confirm != 'DELETE ALL DATA':
        print("Cancelled.")
        return
    
    with app.app_context():
        try:
            # Drop all tables
            print("Dropping all tables...")
            db.drop_all()
            print("✓ All tables dropped")
            
            # Create all tables
            print("Creating all tables...")
            db.create_all()
            print("✓ All tables created")
            
            # Initialize categories
            print("Initializing categories...")
            categories = [
                'Mess Food Quality',
                'Campus Wi-Fi',
                'Medical Center',
                'Placement/CDC',
                'Faculty Concerns',
                'Hostel Maintenance',
                'Other'
            ]
            
            for cat_name in categories:
                category = Category(name=cat_name)
                db.session.add(category)
            
            db.session.commit()
            print(f"✓ Initialized {len(categories)} categories")
            
            print("\n✓ Fresh start completed!")
            print("\nNext steps:")
            print("1. Run: python create_admin.py")
            print("2. Register new users at /register")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Fresh start failed: {e}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'migrate':
            success = migrate()
            sys.exit(0 if success else 1)
        
        elif command == 'rollback':
            rollback()
        
        elif command == 'fresh':
            fresh_start()
        
        else:
            print(f"Unknown command: {command}")
            print("Usage: python migrate_add_users.py [migrate|rollback|fresh]")
            sys.exit(1)
    else:
        # Default: run migration
        success = migrate()
        sys.exit(0 if success else 1)
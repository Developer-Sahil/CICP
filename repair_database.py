"""
Database Repair and Verification Tool
Fixes common database issues including category loading errors
"""

import os
import sys
import shutil
from datetime import datetime

def backup_database():
    """Create backup of existing database"""
    db_file = 'complaints.db'
    
    if os.path.exists(db_file):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'complaints_backup_{timestamp}.db'
        
        try:
            shutil.copy2(db_file, backup_file)
            print(f"✓ Database backed up to: {backup_file}")
            return True
        except Exception as e:
            print(f"✗ Error backing up database: {e}")
            return False
    else:
        print("ℹ No existing database found")
        return True

def check_database_file():
    """Check if database file exists and is accessible"""
    db_file = 'complaints.db'
    
    if not os.path.exists(db_file):
        print(f"✗ Database file not found: {db_file}")
        return False
    
    # Check file permissions
    if not os.access(db_file, os.R_OK | os.W_OK):
        print(f"✗ Database file is not readable/writable")
        return False
    
    print(f"✓ Database file exists and is accessible")
    return True

def test_database_connection():
    """Test database connection"""
    try:
        from app import app, db
        from database.models import Category, Complaint, IssueCluster
        
        with app.app_context():
            # Test simple query
            db.session.execute('SELECT 1')
            print("✓ Database connection successful")
            
            # Check tables
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"✓ Found {len(tables)} tables: {', '.join(tables)}")
            
            return True
            
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def verify_categories():
    """Verify categories table"""
    try:
        from app import app, db
        from database.models import Category
        
        with app.app_context():
            categories = Category.query.all()
            
            if not categories:
                print("⚠ No categories found in database")
                return False
            
            print(f"✓ Found {len(categories)} categories:")
            for cat in categories:
                print(f"  - {cat.name}")
            
            return True
            
    except Exception as e:
        print(f"✗ Error verifying categories: {e}")
        return False

def reinitialize_categories():
    """Reinitialize categories"""
    try:
        from app import app, db
        from database.models import Category
        
        with app.app_context():
            # Clear existing categories
            Category.query.delete()
            db.session.commit()
            print("✓ Cleared existing categories")
            
            # Add default categories
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
            
            return True
            
    except Exception as e:
        print(f"✗ Error reinitializing categories: {e}")
        db.session.rollback()
        return False

def recreate_database():
    """Recreate database from scratch"""
    try:
        from app import app, db
        
        with app.app_context():
            # Drop all tables
            db.drop_all()
            print("✓ Dropped all tables")
            
            # Create all tables
            db.create_all()
            print("✓ Created all tables")
            
            return True
            
    except Exception as e:
        print(f"✗ Error recreating database: {e}")
        return False

def run_diagnostics():
    """Run comprehensive database diagnostics"""
    print("=" * 60)
    print("DATABASE DIAGNOSTICS")
    print("=" * 60)
    print()
    
    # 1. Check database file
    print("1. Checking database file...")
    file_ok = check_database_file()
    print()
    
    # 2. Test connection
    print("2. Testing database connection...")
    connection_ok = test_database_connection()
    print()
    
    # 3. Verify categories
    print("3. Verifying categories...")
    categories_ok = verify_categories()
    print()
    
    # Summary
    print("=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    print(f"Database File: {'✓ OK' if file_ok else '✗ ERROR'}")
    print(f"Connection: {'✓ OK' if connection_ok else '✗ ERROR'}")
    print(f"Categories: {'✓ OK' if categories_ok else '✗ ERROR'}")
    print()
    
    return file_ok and connection_ok and categories_ok

def repair_database():
    """Repair database issues"""
    print("=" * 60)
    print("DATABASE REPAIR")
    print("=" * 60)
    print()
    
    # 1. Backup
    print("Step 1: Backing up database...")
    if not backup_database():
        print("⚠ Backup failed, but continuing...")
    print()
    
    # 2. Test connection
    print("Step 2: Testing connection...")
    if not test_database_connection():
        print("Connection failed. Attempting to recreate database...")
        
        # Delete corrupted database
        if os.path.exists('complaints.db'):
            try:
                os.remove('complaints.db')
                print("✓ Removed corrupted database")
            except Exception as e:
                print(f"✗ Error removing database: {e}")
                return False
        
        # Recreate
        if not recreate_database():
            return False
    
    print()
    
    # 3. Reinitialize categories
    print("Step 3: Reinitializing categories...")
    if not reinitialize_categories():
        return False
    print()
    
    # 4. Verify
    print("Step 4: Verifying repair...")
    if not verify_categories():
        return False
    print()
    
    return True

def interactive_menu():
    """Interactive repair menu"""
    print()
    print("=" * 60)
    print("DATABASE REPAIR TOOL")
    print("=" * 60)
    print()
    print("What would you like to do?")
    print()
    print("1. Run diagnostics")
    print("2. Repair database")
    print("3. Reinitialize categories only")
    print("4. Recreate database (WARNING: deletes all data)")
    print("5. Exit")
    print()
    
    choice = input("Enter choice (1-5): ").strip()
    
    if choice == '1':
        print()
        if run_diagnostics():
            print("✓ All diagnostics passed!")
        else:
            print("✗ Some diagnostics failed. Run repair to fix.")
    
    elif choice == '2':
        print()
        confirm = input("This will repair the database. Continue? (yes/no): ").strip().lower()
        if confirm == 'yes':
            if repair_database():
                print("✓ Database repaired successfully!")
                print("✓ You can now run your application")
            else:
                print("✗ Repair failed. Please check errors above.")
    
    elif choice == '3':
        print()
        confirm = input("This will reset categories. Continue? (yes/no): ").strip().lower()
        if confirm == 'yes':
            if reinitialize_categories():
                print("✓ Categories reinitialized successfully!")
            else:
                print("✗ Failed to reinitialize categories")
    
    elif choice == '4':
        print()
        print("⚠ WARNING: This will delete ALL data including complaints!")
        confirm = input("Type 'DELETE ALL DATA' to confirm: ").strip()
        if confirm == 'DELETE ALL DATA':
            backup_database()
            if recreate_database() and reinitialize_categories():
                print("✓ Database recreated successfully!")
            else:
                print("✗ Failed to recreate database")
        else:
            print("Cancelled.")
    
    elif choice == '5':
        print("Goodbye!")
        return
    
    else:
        print("Invalid choice")
    
    print()
    input("Press Enter to continue...")
    interactive_menu()

if __name__ == '__main__':
    try:
        # Check if running from correct directory
        if not os.path.exists('app.py'):
            print("✗ Error: Please run this script from the project root directory")
            sys.exit(1)
        
        if len(sys.argv) > 1:
            # Command line mode
            command = sys.argv[1].lower()
            
            if command == 'diagnose':
                sys.exit(0 if run_diagnostics() else 1)
            
            elif command == 'repair':
                sys.exit(0 if repair_database() else 1)
            
            elif command == 'reinit-categories':
                sys.exit(0 if reinitialize_categories() else 1)
            
            else:
                print(f"Unknown command: {command}")
                print("Usage: python repair_database.py [diagnose|repair|reinit-categories]")
                sys.exit(1)
        else:
            # Interactive mode
            interactive_menu()
            
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
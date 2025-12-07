"""
Complete database fix script - fixes all known issues
"""
from app import app, db
from database.models import User, Complaint, Category, IssueCluster
from sqlalchemy import text, inspect
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backup_database():
    """Backup existing database"""
    if os.path.exists('complaints.db'):
        import shutil
        from datetime import datetime
        backup_name = f'complaints_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        shutil.copy2('complaints.db', backup_name)
        logger.info(f"✓ Database backed up to {backup_name}")
        return True
    return True

def check_and_add_column(table_name, column_name, column_type, default_value=None):
    """Check if column exists, add if not"""
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        
        if column_name in columns:
            logger.info(f"  ✓ {table_name}.{column_name} already exists")
            return True
        
        logger.info(f"  Adding {table_name}.{column_name}...")
        
        # Build ALTER TABLE statement
        alter_sql = f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}'
        if default_value is not None:
            alter_sql += f' DEFAULT {default_value}'
        
        with db.engine.connect() as conn:
            conn.execute(text(alter_sql))
            conn.commit()
        
        logger.info(f"  ✓ {table_name}.{column_name} added successfully")
        return True
        
    except Exception as e:
        logger.error(f"  ✗ Error with {table_name}.{column_name}: {e}")
        return False

def fix_all_issues():
    """Fix all database issues"""
    with app.app_context():
        print("=" * 70)
        print("COMPLETE DATABASE FIX")
        print("=" * 70)
        print()
        
        # Step 1: Backup
        print("Step 1: Backing up database...")
        backup_database()
        print()
        
        # Step 2: Create all tables
        print("Step 2: Creating/verifying tables...")
        try:
            db.create_all()
            logger.info("✓ All tables created/verified")
        except Exception as e:
            logger.error(f"✗ Error creating tables: {e}")
            return False
        print()
        
        # Step 3: Add missing columns
        print("Step 3: Adding missing columns...")
        
        # Add user_id to complaints if missing
        check_and_add_column('complaints', 'user_id', 'INTEGER', 'NULL')
        
        # Add upvotes to complaints if missing
        check_and_add_column('complaints', 'upvotes', 'INTEGER', 0)
        
        print()
        
        # Step 4: Initialize categories
        print("Step 4: Initializing categories...")
        try:
            category_count = Category.query.count()
            
            if category_count == 0:
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
                logger.info(f"✓ Initialized {len(categories)} categories")
            else:
                logger.info(f"✓ Categories already exist ({category_count} found)")
        except Exception as e:
            logger.error(f"✗ Error initializing categories: {e}")
            db.session.rollback()
        print()
        
        # Step 5: Update existing data
        print("Step 5: Updating existing data...")
        try:
            # Set default upvotes for existing complaints
            with db.engine.connect() as conn:
                result = conn.execute(text('UPDATE complaints SET upvotes = 0 WHERE upvotes IS NULL'))
                conn.commit()
                logger.info(f"✓ Updated {result.rowcount} complaints with default upvotes")
        except Exception as e:
            logger.error(f"Note: {e}")
        print()
        
        # Step 6: Verify database structure
        print("Step 6: Verifying database structure...")
        try:
            inspector = inspect(db.engine)
            
            # Check complaints table
            complaint_columns = [col['name'] for col in inspector.get_columns('complaints')]
            required_complaint_cols = ['id', 'user_id', 'student_id', 'raw_text', 'rewritten_text', 
                                       'category', 'severity', 'embedding', 'cluster_id', 'timestamp', 'upvotes']
            
            missing_cols = [col for col in required_complaint_cols if col not in complaint_columns]
            
            if missing_cols:
                logger.warning(f"Missing columns in complaints: {missing_cols}")
            else:
                logger.info("✓ All required columns present in complaints table")
            
            # Check users table
            if 'users' in inspector.get_table_names():
                user_columns = [col['name'] for col in inspector.get_columns('users')]
                logger.info(f"✓ Users table exists with {len(user_columns)} columns")
            else:
                logger.warning("✗ Users table does not exist")
            
        except Exception as e:
            logger.error(f"Error verifying structure: {e}")
        print()
        
        # Step 7: Statistics
        print("Step 7: Database statistics...")
        try:
            stats = {
                'Users': User.query.count() if 'users' in inspector.get_table_names() else 0,
                'Complaints': Complaint.query.count(),
                'Categories': Category.query.count(),
                'Clusters': IssueCluster.query.count()
            }
            
            for name, count in stats.items():
                logger.info(f"  {name}: {count}")
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
        print()
        
        print("=" * 70)
        print("✓ DATABASE FIX COMPLETED!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. Restart your Flask application: python app.py")
        print("2. Test submission: http://localhost:5000/submit")
        print("3. Test dashboard: http://localhost:5000/dashboard")
        print("4. Create admin user: python create_admin.py")
        print()
        
        return True

if __name__ == '__main__':
    try:
        success = fix_all_issues()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
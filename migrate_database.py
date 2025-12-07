"""
Database migration script to add authentication tables
"""
from app import app, db
from database.models import User, Complaint

def migrate():
    with app.app_context():
        # Create new tables
        db.create_all()
        print("✓ Created authentication tables")
        
        # Add user_id column to existing complaints if needed
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            complaint_columns = [col['name'] for col in inspector.get_columns('complaints')]
            
            if 'user_id' not in complaint_columns:
                # Add column using raw SQL
                db.session.execute('ALTER TABLE complaints ADD COLUMN user_id INTEGER')
                db.session.execute('CREATE INDEX ix_complaints_user_id ON complaints(user_id)')
                db.session.commit()
                print("✓ Added user_id column to complaints")
            else:
                print("✓ user_id column already exists")
                
        except Exception as e:
            print(f"Note: {e}")
            print("If using SQLite, you may need to recreate the database")
        
        print("\n✓ Migration complete!")

if __name__ == '__main__':
    migrate()
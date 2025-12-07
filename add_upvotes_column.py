"""
Add upvotes column to complaints table
"""
from app import app, db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_upvotes_column():
    """Add upvotes column to complaints table"""
    with app.app_context():
        try:
            # Check if column already exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('complaints')]
            
            if 'upvotes' in columns:
                logger.info("✓ upvotes column already exists")
                return True
            
            logger.info("Adding upvotes column to complaints table...")
            
            # Add column
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE complaints ADD COLUMN upvotes INTEGER DEFAULT 0 NOT NULL'))
                conn.commit()
            
            logger.info("✓ upvotes column added successfully")
            
            # Update existing complaints to have 0 upvotes
            with db.engine.connect() as conn:
                conn.execute(text('UPDATE complaints SET upvotes = 0 WHERE upvotes IS NULL'))
                conn.commit()
            
            logger.info("✓ Updated existing complaints with default upvotes")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Error adding upvotes column: {e}")
            return False

if __name__ == '__main__':
    print("=" * 70)
    print("Adding upvotes column to complaints table")
    print("=" * 70)
    print()
    
    success = add_upvotes_column()
    
    if success:
        print("\n✓ Migration completed successfully!")
        print("You can now restart your application.")
    else:
        print("\n✗ Migration failed. Check the errors above.")
        print("\nIf you continue to have issues, try:")
        print("1. python repair_database.py")
        print("2. Or delete complaints.db and start fresh")
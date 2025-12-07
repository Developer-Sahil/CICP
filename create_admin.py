"""
Script to create admin user
"""
from app import app, db
from database.models import User

def create_admin():
    with app.app_context():
        # Check if admin exists
        admin = User.query.filter_by(email='admin@campus.edu').first()
        
        if admin:
            print("Admin user already exists!")
            return
        
        # Create admin
        admin = User(
            name='Admin User',
            student_id='ADMIN001',
            email='sahilsharmamrp@gmail.com',
            is_admin=True,
            email_verified=True
        )
        admin.set_password('Sahil@123')  # Change this!
        
        db.session.add(admin)
        db.session.commit()
        
        print("✓ Admin user created!")
        print("Email: sahilsharmamrp@gmail.com")
        print("Password: Sahil@123")
        print("\n⚠️  IMPORTANT: Change the password after first login!")

if __name__ == '__main__':
    create_admin()
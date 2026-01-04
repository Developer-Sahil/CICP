"""
Debug script to test category loading
Run this to check if categories are properly initialized in Firebase
"""

from database.firebase_models import Category, initialize_categories
import logging

logging.basicConfig(level=logging.INFO)

def test_categories():
    print("=" * 60)
    print("TESTING CATEGORY INITIALIZATION")
    print("=" * 60)
    print()
    
    # Step 1: Check if categories exist
    print("Step 1: Checking existing categories...")
    count = Category.count()
    print(f"✓ Found {count} categories in database")
    print()
    
    # Step 2: Get all categories
    print("Step 2: Retrieving all categories...")
    categories = Category.get_all()
    
    if categories:
        print(f"✓ Successfully retrieved {len(categories)} categories:")
        for i, cat in enumerate(categories, 1):
            print(f"  {i}. {cat.get('name')} (ID: {cat.get('id')})")
    else:
        print("✗ No categories found!")
        print()
        print("Step 3: Initializing default categories...")
        initialize_categories()
        
        # Try again
        categories = Category.get_all()
        if categories:
            print(f"✓ Successfully initialized {len(categories)} categories:")
            for i, cat in enumerate(categories, 1):
                print(f"  {i}. {cat.get('name')} (ID: {cat.get('id')})")
        else:
            print("✗ Failed to initialize categories!")
    
    print()
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    
    return categories


if __name__ == "__main__":
    categories = test_categories()
    
    if not categories:
        print()
        print("⚠️  WARNING: Categories are not loading properly!")
        print()
        print("Troubleshooting steps:")
        print("1. Check your .env file has correct Firebase credentials")
        print("2. Check Firebase Console -> Firestore Database")
        print("3. Verify 'categories' collection exists")
        print("4. Check Firestore rules allow read/write")
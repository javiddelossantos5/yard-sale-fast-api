#!/usr/bin/env python3
"""
Debug script to test database operations
"""

from database import get_db, User, Item
from sqlalchemy.orm import Session

def test_database_operations():
    """Test basic database operations"""
    print("🔍 Testing database operations...")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Test user query
        print("1. Testing user query...")
        user = db.query(User).filter(User.username == "javiddelossantos").first()
        if user:
            print(f"✅ Found user: {user.username} (ID: {user.id})")
        else:
            print("❌ User not found")
            return False
        
        # Test item creation
        print("2. Testing item creation...")
        new_item = Item(
            name="Debug Test Item",
            description="A test item for debugging",
            price=19.99,
            is_available=True,
            owner_id=user.id
        )
        
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        print(f"✅ Created item: {new_item.name} (ID: {new_item.id})")
        
        # Test item query
        print("3. Testing item query...")
        items = db.query(Item).filter(Item.owner_id == user.id).all()
        print(f"✅ Found {len(items)} items for user")
        
        for item in items:
            print(f"   - {item.name}: ${item.price}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_database_operations()
    if success:
        print("\n🎉 All database operations successful!")
    else:
        print("\n❌ Database operations failed!")

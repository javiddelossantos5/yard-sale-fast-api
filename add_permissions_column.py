#!/usr/bin/env python3
"""
Database migration script to add permissions column to users table.
This script adds a 'permissions' column with default value 'user' to existing users.
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the current directory to Python path to import database module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DATABASE_URL

def add_permissions_column():
    """Add permissions column to users table"""
    
    # Create engine
    engine = create_engine(DATABASE_URL, echo=True)
    
    try:
        with engine.connect() as connection:
            # Check if permissions column already exists
            result = connection.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'fastapi_db' 
                AND TABLE_NAME = 'users' 
                AND COLUMN_NAME = 'permissions'
            """))
            
            if result.fetchone():
                print("Permissions column already exists in users table.")
                return
            
            # Add permissions column with default value 'user'
            connection.execute(text("""
                ALTER TABLE users 
                ADD COLUMN permissions VARCHAR(20) NOT NULL DEFAULT 'user'
            """))
            
            # Update any existing users to have 'user' permission (this is redundant but safe)
            connection.execute(text("""
                UPDATE users 
                SET permissions = 'user' 
                WHERE permissions IS NULL OR permissions = ''
            """))
            
            connection.commit()
            print("Successfully added permissions column to users table.")
            print("All existing users have been set to 'user' permission level.")
            
    except Exception as e:
        print(f"Error adding permissions column: {e}")
        raise

def create_admin_user():
    """Create an admin user for testing purposes"""
    
    engine = create_engine(DATABASE_URL, echo=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    try:
        db = SessionLocal()
        
        # Check if admin user already exists
        from database import User
        admin_user = db.query(User).filter(User.username == "admin").first()
        
        if admin_user:
            print("Admin user already exists.")
            return
        
        # Create admin user
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        admin_user = User(
            username="admin",
            email="admin@example.com",
            hashed_password=pwd_context.hash("admin123"),
            full_name="System Administrator",
            permissions="admin",
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("Admin user created successfully!")
        print("Username: admin")
        print("Password: admin123")
        print("Email: admin@example.com")
        print("Please change the password after first login!")
        
    except Exception as e:
        print(f"Error creating admin user: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting database migration...")
    
    try:
        # Add permissions column
        add_permissions_column()
        
        # Ask if user wants to create an admin user
        create_admin = input("\nDo you want to create an admin user? (y/n): ").lower().strip()
        if create_admin in ['y', 'yes']:
            create_admin_user()
        
        print("\nMigration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)

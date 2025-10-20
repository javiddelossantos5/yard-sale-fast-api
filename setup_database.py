#!/usr/bin/env python3
"""
Setup script for the FastAPI application with MySQL database
"""

import os
import sys

def main():
    print("🚀 Setting up FastAPI application with MySQL database...")
    
    # Step 1: Create database
    print("\n1. Creating database...")
    try:
        from create_database import create_database
        create_database()
        print("✅ Database setup completed")
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        print("Please make sure:")
        print("- MySQL server is running")
        print("- Root password is correct in create_database.py")
        print("- You have permission to create databases")
        return False
    
    # Step 2: Test database connection
    print("\n2. Testing database connection...")
    try:
        from database import engine
        with engine.connect() as connection:
            print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please check your MySQL connection settings in database.py")
        return False
    
    # Step 3: Create tables
    print("\n3. Creating database tables...")
    try:
        from database import create_tables
        create_tables()
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Update the password in database.py if needed")
    print("2. Run: python main.py")
    print("3. Visit: http://localhost:8000/docs")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

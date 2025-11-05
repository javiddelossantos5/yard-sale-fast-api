#!/usr/bin/env python3
"""
Quick script to test database connection from the container
"""
import os
import sys

# Add the current directory to path
sys.path.insert(0, '/app')

try:
    from database import engine, create_tables
    from sqlalchemy import text
    
    print("🔍 Testing database connection...")
    
    # Test basic connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 as test"))
        row = result.fetchone()
        if row and row[0] == 1:
            print("✅ Database connection successful!")
        else:
            print("❌ Database connection test failed")
            sys.exit(1)
    
    # Check if database exists
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DATABASE()"))
        db_name = result.fetchone()[0]
        print(f"✅ Connected to database: {db_name}")
    
    # Check if tables exist
    with engine.connect() as conn:
        result = conn.execute(text("SHOW TABLES"))
        tables = [row[0] for row in result.fetchall()]
        
        if tables:
            print(f"✅ Found {len(tables)} tables:")
            for table in tables:
                print(f"   - {table}")
        else:
            print("⚠️  No tables found. Creating tables...")
            create_tables()
            print("✅ Tables created successfully!")
    
    # Check if users table exists and has data
    if 'users' in tables:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.fetchone()[0]
            print(f"✅ Users table exists with {user_count} user(s)")
    
    print("\n🎉 Database connection and setup verified!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


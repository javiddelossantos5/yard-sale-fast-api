#!/usr/bin/env python3
"""
Migration script to add is_free column to items table.
Run this script to add the is_free column to existing databases.
"""

import mysql.connector
from database import get_db, DATABASE_URL
import re

def add_is_free_column():
    """Add is_free column to items table and set it based on price"""
    
    # Extract database connection info from DATABASE_URL
    # Format: mysql+mysqlconnector://user:password@host:port/database
    url_match = re.match(r'mysql\+mysqlconnector://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
    
    if not url_match:
        print("❌ Could not parse DATABASE_URL")
        return False
    
    username, password, host, port, database = url_match.groups()
    
    try:
        # Connect to database
        connection = mysql.connector.connect(
            host=host,
            port=int(port),
            user=username,
            password=password,
            database=database
        )
        
        cursor = connection.cursor()
        
        print("📋 Adding is_free column to items table...")
        
        # Check if column already exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'items' 
            AND COLUMN_NAME = 'is_free'
        """, (database,))
        
        if cursor.fetchone()[0] > 0:
            print("✅ Column 'is_free' already exists. Skipping creation.")
        else:
            # Add is_free column
            cursor.execute("""
                ALTER TABLE items 
                ADD COLUMN is_free BOOLEAN DEFAULT FALSE NOT NULL
            """)
            print("✅ Added is_free column")
        
        # Update existing items: set is_free = True where price = 0
        cursor.execute("""
            UPDATE items 
            SET is_free = TRUE 
            WHERE price = 0.0
        """)
        updated_count = cursor.rowcount
        print(f"✅ Updated {updated_count} items with price 0.0 to is_free = TRUE")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting migration to add is_free column...")
    success = add_is_free_column()
    if success:
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
        exit(1)


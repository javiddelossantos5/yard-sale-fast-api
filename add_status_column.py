#!/usr/bin/env python3
"""
Script to add the status column to existing yard sales in the database
"""

import mysql.connector
from mysql.connector import Error

def add_status_column():
    try:
        # Connect to MySQL
        connection = mysql.connector.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password=''
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Use the database
            cursor.execute("USE fastapi_db")
            
            # Add the status column if it doesn't exist
            try:
                cursor.execute("""
                    ALTER TABLE yard_sales 
                    ADD COLUMN status VARCHAR(20) DEFAULT 'active' NOT NULL
                """)
                print("✅ Added status column to yard_sales table")
            except Error as e:
                if "Duplicate column name" in str(e):
                    print("✅ Status column already exists")
                else:
                    print(f"❌ Error adding status column: {e}")
            
            # Update existing yard sales to have 'active' status
            cursor.execute("""
                UPDATE yard_sales 
                SET status = 'active' 
                WHERE status IS NULL OR status = ''
            """)
            
            affected_rows = cursor.rowcount
            print(f"✅ Updated {affected_rows} yard sales with 'active' status")
            
            connection.commit()
            
    except Error as e:
        print(f"❌ Database error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("✅ Database connection closed")

if __name__ == "__main__":
    add_status_column()

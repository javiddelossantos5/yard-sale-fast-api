#!/usr/bin/env python3
"""
Script to add the 'seller' column to the items table.
Uses the same database connection as the FastAPI app (from DATABASE_URL in .env).
Works even if mysql CLI is not in PATH.
"""

import os
import sys
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

# Load environment variables from .env file
load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    print("❌ DATABASE_URL environment variable not set.")
    print("💡 Please ensure you have a .env file with DATABASE_URL configured.")
    sys.exit(1)

# Parse database URL
# Format: mysql+mysqlconnector://root:Password@127.0.0.1:3306/fastapi_db_dev
try:
    # Remove the mysql+mysqlconnector:// prefix
    db_part = database_url.replace("mysql+mysqlconnector://", "")
    
    # Split by @ to separate credentials from host/db
    if "@" in db_part:
        creds, host_db = db_part.split("@", 1)
        # Handle username:password or just username
        if ":" in creds:
            username, password = creds.split(":", 1)
            password = password if password else None
        else:
            username = creds if creds else "root"
            password = None
    else:
        username = "root"
        password = None
        host_db = db_part
    
    # Split host/db by /
    if "/" in host_db:
        host_port, database = host_db.split("/", 1)
        if ":" in host_port:
            host, port = host_port.split(":")
        else:
            host = host_port
            port = "3306"  # Default MySQL port
    else:
        host = "127.0.0.1"  # Default host
        port = "3306"  # Default port
        database = host_db
    
    print(f"🚀 Adding 'seller' column to items table (LOCAL DEV)...")
    print(f"📋 Database: {database}")
    print(f"📋 Host: {host}:{port}")
    print(f"📋 Username: {username}")
    print("")
    
    # Connect to MySQL
    cnx = mysql.connector.connect(
        host=host,
        port=int(port),
        user=username,
        password=password,
        database=database
    )
    cursor = cnx.cursor()

    # Check if column exists
    cursor.execute(f"SHOW COLUMNS FROM items LIKE 'seller'")
    if cursor.fetchone():
        print("ℹ️  Column 'seller' already exists. Skipping.")
    else:
        # Add the column
        alter_table_sql = """
        ALTER TABLE items 
        ADD COLUMN seller VARCHAR(100) NULL COMMENT 'Seller name/contact name (optional)' 
        AFTER facebook_url;
        """
        cursor.execute(alter_table_sql)
        cnx.commit()
        print("✅ Column 'seller' added successfully.")

    cursor.close()
    cnx.close()
    print("\n✅ Script completed!")

except Error as err:
    print(f"❌ Database error: {err.errno} ({err.sqlstate}): {err.msg}")
    sys.exit(1)
except Exception as e:
    print(f"❌ An unexpected error occurred: {e}")
    sys.exit(1)


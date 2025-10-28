#!/usr/bin/env python3
"""
Database Setup Script for Docker MySQL
Run this to create tables and set up the database for your Docker setup
"""

import mysql.connector
from mysql.connector import Error
import sys

def setup_docker_database():
    """Setup the database for Docker MySQL"""
    try:
        print("🚀 Setting up database for Docker MySQL...")
        
        # Connect to Docker MySQL (using the same credentials as docker-compose.yml)
        connection = mysql.connector.connect(
            host='127.0.0.1',  # localhost since we're connecting from the host
            port=3306,
            user='root',
            password='password'  # Password from docker-compose.yml
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create database if it doesn't exist
            print("📁 Creating database 'fastapi_db'...")
            cursor.execute("CREATE DATABASE IF NOT EXISTS fastapi_db")
            print("✅ Database 'fastapi_db' created successfully or already exists")
            
            # Use the database
            cursor.execute("USE fastapi_db")
            print("✅ Using database 'fastapi_db'")
            
            # Create tables using the database.py models
            print("📋 Creating database tables...")
            
            # Import the database models
            sys.path.append('.')
            from database import Base, engine
            
            # Create all tables
            Base.metadata.create_all(bind=engine)
            print("✅ All database tables created successfully")
            
            # Show created tables
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"📊 Created {len(tables)} tables:")
            for table in tables:
                print(f"  - {table[0]}")
            
            print("\n🎉 Database setup completed successfully!")
            print("\n🔍 Next steps:")
            print("1. Start your Docker services: docker-compose up -d")
            print("2. Your backend will be available at: http://10.1.2.165:8000/")
            print("3. API docs will be available at: http://10.1.2.165:8000/docs")
            
    except Error as e:
        print(f"❌ Error setting up database: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure Docker MySQL is running: docker-compose ps")
        print("2. Check if MySQL container is accessible on port 3306")
        print("3. Verify the password 'password' matches docker-compose.yml")
        return False
        
    except ImportError as e:
        print(f"❌ Error importing database models: {e}")
        print("Make sure you're running this script from the project directory")
        return False
        
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("🔌 MySQL connection closed")
    
    return True

if __name__ == "__main__":
    success = setup_docker_database()
    sys.exit(0 if success else 1)

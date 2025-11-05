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
        
        # Connect to Docker MySQL (using root credentials from docker-compose.db.yml)
        connection = mysql.connector.connect(
            host='127.0.0.1',  # localhost since we're connecting from the host
            port=3306,
            user='root',
            password='rootpassword'  # Root password from docker-compose.db.yml
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Database already exists from docker-compose.db.yml, just verify
            print("📁 Verifying database 'yardsale' exists...")
            cursor.execute("SHOW DATABASES LIKE 'yardsale'")
            result = cursor.fetchone()
            if result:
                print("✅ Database 'yardsale' exists")
            else:
                print("⚠️  Database 'yardsale' not found, creating...")
                cursor.execute("CREATE DATABASE IF NOT EXISTS yardsale")
                print("✅ Database 'yardsale' created")
            
            # Use the database
            cursor.execute("USE yardsale")
            print("✅ Using database 'yardsale'")
            
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
        print("3. Verify the root password 'rootpassword' matches docker-compose.db.yml")
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

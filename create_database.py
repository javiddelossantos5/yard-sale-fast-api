#!/usr/bin/env python3
"""
Script to create the database if it doesn't exist
Run this before starting the FastAPI application
"""

import mysql.connector
from mysql.connector import Error

def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Connect to MySQL server (without specifying database)
        connection = mysql.connector.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password=''  # Empty password for root user
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS fastapi_db")
            print("Database 'fastapi_db' created successfully or already exists")
            
            # Use the database
            cursor.execute("USE fastapi_db")
            print("Using database 'fastapi_db'")
            
    except Error as e:
        print(f"Error creating database: {e}")
        
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection closed")

if __name__ == "__main__":
    create_database()

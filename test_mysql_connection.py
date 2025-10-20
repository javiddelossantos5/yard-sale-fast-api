#!/usr/bin/env python3
"""
Script to test MySQL connection with different password options
"""

import mysql.connector
from mysql.connector import Error

def test_connection(password):
    """Test MySQL connection with given password"""
    try:
        connection = mysql.connector.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password=password
        )
        
        if connection.is_connected():
            print(f"✅ SUCCESS: Connected with password '{password}'")
            cursor = connection.cursor()
            cursor.execute("SELECT VERSION();")
            version = cursor.fetchone()
            print(f"   MySQL version: {version[0]}")
            cursor.close()
            connection.close()
            return True
        else:
            print(f"❌ FAILED: Could not connect with password '{password}'")
            return False
            
    except Error as e:
        print(f"❌ FAILED: {e}")
        return False

def main():
    """Test common MySQL passwords"""
    print("🔍 Testing MySQL connection with common passwords...")
    print("=" * 60)
    
    # Common passwords to try
    passwords_to_try = [
        "",  # Empty password
        "root",
        "password",
        "admin",
        "123456",
        "mysql",
        "root123",
        "password123"
    ]
    
    successful_password = None
    
    for password in passwords_to_try:
        display_password = f"'{password}'" if password else "'(empty)'"
        print(f"Testing password: {display_password}")
        
        if test_connection(password):
            successful_password = password
            break
        print()
    
    print("=" * 60)
    
    if successful_password:
        print(f"🎉 Found working password: {successful_password}")
        print("\nNext steps:")
        print("1. Update database.py with the correct password:")
        print(f"   DATABASE_URL = \"mysql+mysqlconnector://root:{successful_password}@127.0.0.1:3306/fastapi_db\"")
        print("2. Update create_database.py with the correct password:")
        print(f"   password='{successful_password}'")
        print("3. Run: python main.py")
    else:
        print("❌ No working password found.")
        print("\nPlease check:")
        print("- MySQL server is running")
        print("- Try connecting with MySQL Workbench or command line")
        print("- Reset MySQL root password if needed")

if __name__ == "__main__":
    main()

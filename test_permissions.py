#!/usr/bin/env python3
"""
Test script to demonstrate the permissions system.
This script shows how to create users with different permission levels.
"""

import requests
import json

# API base URL
BASE_URL = "http://localhost:8000"

def test_user_registration():
    """Test user registration with different permission levels"""
    
    print("Testing User Registration with Permissions")
    print("=" * 50)
    
    # Test data for different user types
    test_users = [
        {
            "username": "regular_user",
            "email": "user@example.com",
            "password": "password123",
            "full_name": "Regular User",
            "permissions": "user"
        },
        {
            "username": "moderator_user",
            "email": "moderator@example.com", 
            "password": "password123",
            "full_name": "Moderator User",
            "permissions": "moderator"
        },
        {
            "username": "admin_user",
            "email": "admin@example.com",
            "password": "password123", 
            "full_name": "Admin User",
            "permissions": "admin"
        }
    ]
    
    for user_data in test_users:
        try:
            response = requests.post(f"{BASE_URL}/register", json=user_data)
            
            if response.status_code == 201:
                user_info = response.json()
                print(f"✅ Created {user_data['permissions']} user: {user_info['username']}")
                print(f"   ID: {user_info['id']}, Permissions: {user_info['permissions']}")
            else:
                print(f"❌ Failed to create {user_data['permissions']} user: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Could not connect to API. Make sure the server is running on localhost:8000")
            return
        except Exception as e:
            print(f"❌ Error creating user: {e}")
    
    print()

def test_login_and_permissions():
    """Test login and check user permissions"""
    
    print("Testing Login and Permission Checking")
    print("=" * 50)
    
    # Test login for different users
    test_logins = [
        {"username": "regular_user", "password": "password123"},
        {"username": "moderator_user", "password": "password123"},
        {"username": "admin_user", "password": "password123"}
    ]
    
    tokens = {}
    
    for login_data in test_logins:
        try:
            response = requests.post(f"{BASE_URL}/api/login", json=login_data)
            
            if response.status_code == 200:
                token_info = response.json()
                tokens[login_data['username']] = token_info['access_token']
                print(f"✅ {login_data['username']} logged in successfully")
            else:
                print(f"❌ Failed to login {login_data['username']}: {response.text}")
                
        except Exception as e:
            print(f"❌ Error logging in {login_data['username']}: {e}")
    
    print()
    
    # Test accessing user info with different permission levels
    print("Testing User Info Access")
    print("-" * 30)
    
    for username, token in tokens.items():
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"{BASE_URL}/api/me", headers=headers)
            
            if response.status_code == 200:
                user_info = response.json()
                print(f"✅ {username} can access their info: {user_info['permissions']}")
            else:
                print(f"❌ {username} cannot access their info: {response.text}")
                
        except Exception as e:
            print(f"❌ Error getting user info for {username}: {e}")
    
    print()
    
    # Test admin-only endpoints
    print("Testing Admin-Only Endpoints")
    print("-" * 30)
    
    for username, token in tokens.items():
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"{BASE_URL}/admin/users", headers=headers)
            
            if response.status_code == 200:
                print(f"✅ {username} can access admin endpoints")
            elif response.status_code == 403:
                print(f"❌ {username} cannot access admin endpoints (403 Forbidden)")
            else:
                print(f"❌ {username} got unexpected response: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error testing admin access for {username}: {e}")

def test_moderator_endpoints():
    """Test moderator-only endpoints"""
    
    print("Testing Moderator-Only Endpoints")
    print("=" * 50)
    
    # Login as moderator
    try:
        response = requests.post(f"{BASE_URL}/api/login", json={
            "username": "moderator_user",
            "password": "password123"
        })
        
        if response.status_code == 200:
            token_info = response.json()
            token = token_info['access_token']
            
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test moderator access to reports
            response = requests.get(f"{BASE_URL}/admin/reports", headers=headers)
            
            if response.status_code == 200:
                print("✅ Moderator can access reports endpoint")
            else:
                print(f"❌ Moderator cannot access reports: {response.status_code}")
                
        else:
            print("❌ Could not login as moderator")
            
    except Exception as e:
        print(f"❌ Error testing moderator endpoints: {e}")

if __name__ == "__main__":
    print("FastAPI Permissions System Test")
    print("=" * 50)
    print()
    
    # Run tests
    test_user_registration()
    test_login_and_permissions()
    test_moderator_endpoints()
    
    print("Test completed!")
    print()
    print("To run the migration script:")
    print("python add_permissions_column.py")
    print()
    print("To start the server:")
    print("python main.py")

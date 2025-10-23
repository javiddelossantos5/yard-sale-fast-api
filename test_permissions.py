#!/usr/bin/env python3
"""
Test script to demonstrate the permissions system with UUID support.
This script shows how to create users with different permission levels.
"""

import requests
import json
import uuid

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
                print(f"   UUID: {user_info['id']}, Permissions: {user_info['permissions']}")
                # Validate that the ID is a valid UUID
                try:
                    uuid.UUID(user_info['id'])
                    print(f"   ✅ Valid UUID format")
                except ValueError:
                    print(f"   ❌ Invalid UUID format")
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
                print(f"   UUID: {user_info['id']}")
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

def test_uuid_functionality():
    """Test UUID-specific functionality"""
    
    print("Testing UUID Functionality")
    print("=" * 50)
    
    # Login as admin to test UUID endpoints
    try:
        response = requests.post(f"{BASE_URL}/api/login", json={
            "username": "admin_user",
            "password": "password123"
        })
        
        if response.status_code == 200:
            token_info = response.json()
            token = token_info['access_token']
            headers = {"Authorization": f"Bearer {token}"}
            
            # Get all users to test UUID format
            response = requests.get(f"{BASE_URL}/admin/users", headers=headers)
            
            if response.status_code == 200:
                users = response.json()
                print(f"✅ Retrieved {len(users)} users")
                
                # Test UUID format for each user
                for user in users[:3]:  # Test first 3 users
                    try:
                        uuid.UUID(user['id'])
                        print(f"   ✅ User {user['username']} has valid UUID: {user['id']}")
                    except ValueError:
                        print(f"   ❌ User {user['username']} has invalid UUID: {user['id']}")
                
                # Test accessing a specific user by UUID
                if users:
                    test_user = users[0]
                    user_uuid = test_user['id']
                    
                    response = requests.get(f"{BASE_URL}/admin/users/{user_uuid}", headers=headers)
                    if response.status_code == 200:
                        print(f"✅ Successfully accessed user by UUID: {user_uuid}")
                    else:
                        print(f"❌ Failed to access user by UUID: {response.status_code}")
                
            else:
                print(f"❌ Failed to get users: {response.status_code}")
                
        else:
            print("❌ Could not login as admin")
            
    except Exception as e:
        print(f"❌ Error testing UUID functionality: {e}")
    
    print()
    
    # Test invalid UUID format
    print("Testing Invalid UUID Handling")
    print("-" * 30)
    
    try:
        response = requests.post(f"{BASE_URL}/api/login", json={
            "username": "admin_user",
            "password": "password123"
        })
        
        if response.status_code == 200:
            token_info = response.json()
            token = token_info['access_token']
            headers = {"Authorization": f"Bearer {token}"}
            
            # Try to access user with invalid UUID
            invalid_uuid = "12345"  # Not a valid UUID
            response = requests.get(f"{BASE_URL}/admin/users/{invalid_uuid}", headers=headers)
            
            if response.status_code == 404:
                print("✅ Invalid UUID properly returns 404")
            else:
                print(f"❌ Invalid UUID returned unexpected status: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Error testing invalid UUID: {e}")

if __name__ == "__main__":
    print("FastAPI Permissions System Test")
    print("=" * 50)
    print()
    
    # Run tests
    test_user_registration()
    test_login_and_permissions()
    test_moderator_endpoints()
    test_uuid_functionality()
    
    print("Test completed!")
    print()
    print("Migration scripts:")
    print("1. Add permissions column: python add_permissions_column.py")
    print("2. Migrate to UUIDs: python migrate_to_uuid.py")
    print()
    print("To start the server:")
    print("python main.py")

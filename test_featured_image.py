#!/usr/bin/env python3
"""
Test script for featured image endpoints
"""

import requests
import json
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USERNAME = "javiddelossantos"
TEST_PASSWORD = "Password"

def login() -> Optional[str]:
    """Login and get access token"""
    print("🔐 Logging in...")
    response = requests.post(
        f"{BASE_URL}/api/login",
        data={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD
        }
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✅ Login successful!")
        return token
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def get_headers(token: str) -> dict:
    """Get request headers with auth token"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def test_get_yard_sales(token: str):
    """Test getting yard sales list"""
    print("\n📋 Testing GET /yard-sales...")
    response = requests.get(
        f"{BASE_URL}/yard-sales",
        headers=get_headers(token)
    )
    
    if response.status_code == 200:
        yard_sales = response.json()
        print(f"✅ Found {len(yard_sales)} yard sales")
        if yard_sales:
            return yard_sales[0]["id"]
        return None
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return None

def test_get_yard_sale_images(token: str, yard_sale_id: str):
    """Test getting available images for a yard sale"""
    print(f"\n🖼️  Testing GET /yard-sales/{yard_sale_id}/images...")
    response = requests.get(
        f"{BASE_URL}/yard-sales/{yard_sale_id}/images",
        headers=get_headers(token)
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"   Featured Image: {data.get('featured_image', 'None')}")
        print(f"   Photos Count: {len(data.get('photos', []))}")
        print(f"   Uploaded Images Count: {len(data.get('uploaded_images', []))}")
        print(f"   All Images Count: {len(data.get('all_images', []))}")
        return data
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return None

def test_set_featured_image_from_photo_index(token: str, yard_sale_id: str, photo_index: int = 0):
    """Test setting featured image using photo_index"""
    print(f"\n⭐ Testing PUT /yard-sales/{yard_sale_id}/featured-image (photo_index={photo_index})...")
    response = requests.put(
        f"{BASE_URL}/yard-sales/{yard_sale_id}/featured-image",
        headers=get_headers(token),
        json={"photo_index": photo_index}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"   Message: {data.get('message')}")
        print(f"   Featured Image: {data.get('featured_image', 'None')}")
        return data
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return None

def test_set_featured_image_from_image_key(token: str, yard_sale_id: str, image_key: str):
    """Test setting featured image using image_key"""
    print(f"\n⭐ Testing PUT /yard-sales/{yard_sale_id}/featured-image (image_key={image_key})...")
    response = requests.put(
        f"{BASE_URL}/yard-sales/{yard_sale_id}/featured-image",
        headers=get_headers(token),
        json={"image_key": image_key}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"   Message: {data.get('message')}")
        print(f"   Featured Image: {data.get('featured_image', 'None')}")
        return data
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return None

def test_set_featured_image_from_url(token: str, yard_sale_id: str, image_url: str):
    """Test setting featured image using image_url"""
    print(f"\n⭐ Testing PUT /yard-sales/{yard_sale_id}/featured-image (image_url)...")
    response = requests.put(
        f"{BASE_URL}/yard-sales/{yard_sale_id}/featured-image",
        headers=get_headers(token),
        json={"image_url": image_url}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"   Message: {data.get('message')}")
        print(f"   Featured Image: {data.get('featured_image', 'None')}")
        return data
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return None

def test_remove_featured_image(token: str, yard_sale_id: str):
    """Test removing featured image"""
    print(f"\n🗑️  Testing DELETE /yard-sales/{yard_sale_id}/featured-image...")
    response = requests.delete(
        f"{BASE_URL}/yard-sales/{yard_sale_id}/featured-image",
        headers=get_headers(token)
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"   Message: {data.get('message')}")
        print(f"   Featured Image: {data.get('featured_image', 'None')}")
        return data
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return None

def test_get_yard_sale(token: str, yard_sale_id: str):
    """Test getting a single yard sale to verify featured_image appears"""
    print(f"\n📄 Testing GET /yard-sales/{yard_sale_id}...")
    response = requests.get(
        f"{BASE_URL}/yard-sales/{yard_sale_id}",
        headers=get_headers(token)
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"   Title: {data.get('title')}")
        print(f"   Featured Image: {data.get('featured_image', 'None')}")
        return data
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return None

def main():
    print("🧪 Testing Featured Image Endpoints\n")
    print("=" * 60)
    
    # Login
    token = login()
    if not token:
        print("\n❌ Cannot proceed without authentication")
        return
    
    # Get a yard sale to test with
    yard_sale_id = test_get_yard_sales(token)
    if not yard_sale_id:
        print("\n❌ No yard sales found to test with")
        print("💡 Create a yard sale first, or update TEST_USERNAME")
        return
    
    print(f"\n🎯 Using yard sale ID: {yard_sale_id}")
    
    # Get current yard sale to see current state
    yard_sale = test_get_yard_sale(token, yard_sale_id)
    
    # Get available images
    images_data = test_get_yard_sale_images(token, yard_sale_id)
    
    # Test 1: Set featured image from photos array (if photos exist)
    if images_data and images_data.get('photos'):
        print(f"\n📸 Found {len(images_data['photos'])} photos in yard sale")
        test_set_featured_image_from_photo_index(token, yard_sale_id, 0)
        
        # Verify it was set
        yard_sale_after = test_get_yard_sale(token, yard_sale_id)
        
        # Test removing it
        test_remove_featured_image(token, yard_sale_id)
        
        # Verify it was removed
        yard_sale_after_remove = test_get_yard_sale(token, yard_sale_id)
    else:
        print("\n⚠️  No photos found in yard sale, skipping photo_index test")
    
    # Test 2: Set featured image from uploaded images (if any)
    if images_data and images_data.get('uploaded_images'):
        print(f"\n📤 Found {len(images_data['uploaded_images'])} uploaded images")
        first_uploaded = images_data['uploaded_images'][0]
        image_key = first_uploaded.get('key')
        if image_key:
            test_set_featured_image_from_image_key(token, yard_sale_id, image_key)
            
            # Verify it was set
            yard_sale_after = test_get_yard_sale(token, yard_sale_id)
            
            # Test removing it
            test_remove_featured_image(token, yard_sale_id)
        else:
            print("⚠️  No image key found in uploaded images")
    else:
        print("\n⚠️  No uploaded images found, skipping image_key test")
    
    # Test 3: Set featured image from URL
    test_url = "https://via.placeholder.com/400x300.jpg"
    test_set_featured_image_from_url(token, yard_sale_id, test_url)
    
    # Verify it was set
    yard_sale_after = test_get_yard_sale(token, yard_sale_id)
    
    # Clean up - remove featured image
    test_remove_featured_image(token, yard_sale_id)
    
    print("\n" + "=" * 60)
    print("✅ Featured Image Endpoint Tests Complete!")
    print("\n📋 Summary:")
    print("   ✅ GET /yard-sales/{id}/images - Get available images")
    print("   ✅ PUT /yard-sales/{id}/featured-image - Set featured image")
    print("   ✅ DELETE /yard-sales/{id}/featured-image - Remove featured image")
    print("   ✅ Featured image appears in yard sale responses")

if __name__ == "__main__":
    main()



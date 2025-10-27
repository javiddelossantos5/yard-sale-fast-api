#!/usr/bin/env python3

"""
Test script to verify Garage S3 connection and image upload functionality
Run this script to test the connection to your Garage instance
"""

import boto3
from botocore.exceptions import ClientError
import uuid
import io

# Garage S3 Configuration
GARAGE_ENDPOINT_URL = "http://10.1.2.165:3900"
GARAGE_ACCESS_KEY_ID = "GKdfa877679e4f9f1c89612285"
GARAGE_SECRET_ACCESS_KEY = "514fc1f21b01269ec46d9157a5e2eeabcb03a4b9733cfa1e5945dfc388f8a980"
GARAGE_BUCKET_NAME = "nextcloud-bucket"
GARAGE_REGION = "garage"

def test_garage_connection():
    """Test connection to Garage S3"""
    print("🔧 Testing Garage S3 Connection...")
    
    try:
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            endpoint_url=GARAGE_ENDPOINT_URL,
            aws_access_key_id=GARAGE_ACCESS_KEY_ID,
            aws_secret_access_key=GARAGE_SECRET_ACCESS_KEY,
            region_name=GARAGE_REGION
        )
        
        # Test 1: List buckets
        print("📋 Test 1: Listing buckets...")
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        print(f"✅ Available buckets: {buckets}")
        
        if GARAGE_BUCKET_NAME not in buckets:
            print(f"❌ Bucket '{GARAGE_BUCKET_NAME}' not found!")
            return False
        
        # Test 2: Check bucket access
        print(f"📋 Test 2: Checking bucket '{GARAGE_BUCKET_NAME}' access...")
        s3_client.head_bucket(Bucket=GARAGE_BUCKET_NAME)
        print("✅ Bucket access confirmed")
        
        # Test 3: Upload test file
        print("📋 Test 3: Uploading test file...")
        test_key = f"test/{uuid.uuid4()}.txt"
        test_content = f"Test file created at {__import__('datetime').datetime.now()}"
        
        s3_client.put_object(
            Bucket=GARAGE_BUCKET_NAME,
            Key=test_key,
            Body=test_content.encode('utf-8'),
            ContentType='text/plain'
        )
        print(f"✅ Test file uploaded: {test_key}")
        
        # Test 4: Download test file
        print("📋 Test 4: Downloading test file...")
        response = s3_client.get_object(Bucket=GARAGE_BUCKET_NAME, Key=test_key)
        downloaded_content = response['Body'].read().decode('utf-8')
        print(f"✅ Test file downloaded: {downloaded_content[:50]}...")
        
        # Test 5: Delete test file
        print("📋 Test 5: Deleting test file...")
        s3_client.delete_object(Bucket=GARAGE_BUCKET_NAME, Key=test_key)
        print("✅ Test file deleted")
        
        # Test 6: Test image upload simulation
        print("📋 Test 6: Testing image upload simulation...")
        test_image_key = f"images/test-user/{uuid.uuid4()}.jpg"
        
        # Create a simple test image (1x1 pixel JPEG)
        test_image_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
        
        s3_client.put_object(
            Bucket=GARAGE_BUCKET_NAME,
            Key=test_image_key,
            Body=test_image_data,
            ContentType='image/jpeg',
            Metadata={
                'uploaded_by': 'test-user',
                'test': 'true'
            }
        )
        print(f"✅ Test image uploaded: {test_image_key}")
        
        # Test 7: Generate public URL
        print("📋 Test 7: Testing public URL generation...")
        public_url = f"{GARAGE_ENDPOINT_URL}/{GARAGE_BUCKET_NAME}/{test_image_key}"
        print(f"✅ Public URL: {public_url}")
        
        # Clean up test image
        s3_client.delete_object(Bucket=GARAGE_BUCKET_NAME, Key=test_image_key)
        print("✅ Test image cleaned up")
        
        print("\n🎉 All tests passed! Garage S3 is working correctly.")
        return True
        
    except ClientError as e:
        print(f"❌ Garage S3 error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_fastapi_endpoints():
    """Test FastAPI endpoints (requires server to be running)"""
    print("\n🌐 Testing FastAPI Endpoints...")
    
    import requests
    
    try:
        # Test login
        print("📋 Testing login endpoint...")
        login_response = requests.post(
            "http://localhost:8000/api/login",
            json={"username": "javiddelossantos", "password": "Password"}
        )
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            print("✅ Login successful")
            
            # Test image list endpoint
            print("📋 Testing image list endpoint...")
            headers = {"Authorization": f"Bearer {token}"}
            images_response = requests.get("http://localhost:8000/images", headers=headers)
            
            if images_response.status_code == 200:
                print("✅ Image list endpoint working")
                print(f"📊 Current images: {len(images_response.json()['images'])}")
            else:
                print(f"❌ Image list endpoint failed: {images_response.status_code}")
                
        else:
            print(f"❌ Login failed: {login_response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to FastAPI server. Make sure it's running on localhost:8000")
    except Exception as e:
        print(f"❌ FastAPI test error: {e}")

if __name__ == "__main__":
    print("🧪 Garage S3 + FastAPI Image Upload Test Suite")
    print("=" * 50)
    
    # Test Garage connection
    garage_ok = test_garage_connection()
    
    if garage_ok:
        # Test FastAPI endpoints
        test_fastapi_endpoints()
        
        print("\n📋 Next Steps:")
        print("1. Deploy to your Ubuntu server using deploy_to_server.sh")
        print("2. Access the frontend at http://10.1.2.165/")
        print("3. Upload images and test the functionality")
    else:
        print("\n❌ Garage S3 connection failed. Please check your configuration.")
        print("Make sure:")
        print("- Garage is running on http://10.1.2.165:3900")
        print("- The bucket 'nextcloud-bucket' exists")
        print("- Your credentials are correct")

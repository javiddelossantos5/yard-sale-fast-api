#!/usr/bin/env python3
"""
Test backend's MinIO connection using the same configuration as main.py
This script can be run inside the Docker container to verify MinIO connectivity
"""
import sys
import os

# Add the current directory to path
sys.path.insert(0, '/app')

try:
    from main import s3_client, MINIO_ENDPOINT_URL, MINIO_BUCKET_NAME, MINIO_ACCESS_KEY_ID
    from botocore.exceptions import ClientError
    import traceback
    
    print("=" * 60)
    print("🔍 Testing Backend MinIO Connection")
    print("=" * 60)
    print(f"📍 Endpoint: {MINIO_ENDPOINT_URL}")
    print(f"📦 Bucket: {MINIO_BUCKET_NAME}")
    print(f"🔑 Access Key: {MINIO_ACCESS_KEY_ID[:10]}...")
    print()
    
    # Test 1: Basic connection test
    print("1️⃣ Testing basic connection...")
    try:
        # Try to list buckets (tests basic connectivity)
        response = s3_client.list_buckets()
        print("✅ Connection successful!")
        buckets = [b['Name'] for b in response.get('Buckets', [])]
        print(f"   Found {len(buckets)} bucket(s)")
        if buckets:
            print(f"   Buckets: {', '.join(buckets)}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)
    
    # Test 2: Bucket access test
    print(f"\n2️⃣ Testing bucket '{MINIO_BUCKET_NAME}' access...")
    try:
        response = s3_client.head_bucket(Bucket=MINIO_BUCKET_NAME)
        print("✅ Bucket access confirmed!")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"❌ Bucket '{MINIO_BUCKET_NAME}' does not exist")
            print("💡 Create the bucket in MinIO web UI at http://10.1.2.165:9001")
            sys.exit(1)
        elif error_code == '403':
            print("❌ Access denied - check credentials")
            sys.exit(1)
        else:
            print(f"❌ Error accessing bucket: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)
    
    # Test 3: List objects in bucket
    print(f"\n3️⃣ Listing objects in bucket '{MINIO_BUCKET_NAME}'...")
    try:
        response = s3_client.list_objects_v2(Bucket=MINIO_BUCKET_NAME)
        
        if 'Contents' in response:
            print(f"✅ Found {len(response['Contents'])} object(s):")
            for obj in response['Contents'][:10]:  # Show first 10
                size_kb = obj['Size'] / 1024
                print(f"   - {obj['Key']} ({size_kb:.2f} KB)")
            if len(response['Contents']) > 10:
                print(f"   ... and {len(response['Contents']) - 10} more")
        else:
            print("📁 Bucket is empty (no objects yet)")
    except Exception as e:
        print(f"❌ Error listing objects: {e}")
        traceback.print_exc()
    
    # Test 4: Test write permission (create a test file)
    print(f"\n4️⃣ Testing write permission...")
    try:
        test_key = "test/connection-test.txt"
        test_content = b"This is a test file to verify write permissions"
        
        s3_client.put_object(
            Bucket=MINIO_BUCKET_NAME,
            Key=test_key,
            Body=test_content,
            ContentType='text/plain'
        )
        print("✅ Write permission confirmed!")
        
        # Clean up test file
        s3_client.delete_object(Bucket=MINIO_BUCKET_NAME, Key=test_key)
        print("✅ Test file created and cleaned up successfully")
    except Exception as e:
        print(f"❌ Write test failed: {e}")
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎉 All MinIO connection tests passed!")
    print("=" * 60)
    print("\n✅ Backend is ready to upload images to MinIO")
    print(f"📍 MinIO endpoint: {MINIO_ENDPOINT_URL}")
    print(f"📦 Bucket: {MINIO_BUCKET_NAME}")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you're running this from the container or with proper PYTHONPATH")
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    traceback.print_exc()
    sys.exit(1)


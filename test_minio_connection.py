#!/usr/bin/env python3
"""
Test MinIO connection and bucket operations
"""

import boto3
from botocore.exceptions import ClientError
import os

# MinIO Configuration
# Use environment variables if set, otherwise use defaults
# MinIO uses port 9000 for S3 API, port 9001 for web console
MINIO_ENDPOINT_URL = os.getenv("MINIO_ENDPOINT_URL", "http://10.1.2.165:9000")
MINIO_ACCESS_KEY_ID = os.getenv("MINIO_ACCESS_KEY_ID", "minioadmin")
MINIO_SECRET_ACCESS_KEY = os.getenv("MINIO_SECRET_ACCESS_KEY", "minioadmin")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "yardsale")
MINIO_REGION = os.getenv("MINIO_REGION", "us-east-1")

def test_minio_connection():
    """Test MinIO connection and basic operations"""
    print("🔧 Testing MinIO connection...")
    
    try:
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            endpoint_url=MINIO_ENDPOINT_URL,
            aws_access_key_id=MINIO_ACCESS_KEY_ID,
            aws_secret_access_key=MINIO_SECRET_ACCESS_KEY,
            region_name=MINIO_REGION
        )
        
        print("✅ S3 client initialized successfully")
        
        # Test bucket access
        print(f"📦 Testing bucket '{MINIO_BUCKET_NAME}' access...")
        response = s3_client.head_bucket(Bucket=MINIO_BUCKET_NAME)
        print("✅ Bucket access confirmed")
        
        # List objects in bucket
        print(f"📋 Listing objects in bucket '{MINIO_BUCKET_NAME}'...")
        response = s3_client.list_objects_v2(Bucket=MINIO_BUCKET_NAME)
        
        if 'Contents' in response:
            print(f"📁 Found {len(response['Contents'])} objects:")
            for obj in response['Contents']:
                print(f"   - {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("📁 Bucket is empty")
        
        # Test pre-signed URL generation
        if 'Contents' in response and response['Contents']:
            first_object = response['Contents'][0]['Key']
            print(f"🔗 Testing pre-signed URL for '{first_object}'...")
            
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': MINIO_BUCKET_NAME, 'Key': first_object},
                ExpiresIn=3600
            )
            print(f"✅ Pre-signed URL generated: {url[:100]}...")
        
        print("\n🎉 MinIO integration test completed successfully!")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            print(f"❌ Bucket '{MINIO_BUCKET_NAME}' does not exist")
            print("💡 Create the bucket in MinIO web UI first")
        elif error_code == 'AccessDenied':
            print("❌ Access denied - check credentials")
        else:
            print(f"❌ ClientError: {e}")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_minio_connection()

#!/bin/bash

# Test script for FastAPI Image Upload System
# Tests both local and remote deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
LOCAL_URL="http://localhost:8000"
REMOTE_URL="https://garage.javidscript.com"
TEST_USERNAME="javiddelossantos"
TEST_PASSWORD="Password"

echo -e "${BLUE}🧪 FastAPI Image Upload System Test Suite${NC}"
echo "================================================"

# Function to test endpoint
test_endpoint() {
    local url="$1"
    local expected_status="$2"
    local description="$3"
    
    echo -n "Testing $description... "
    
    status=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$status" = "$expected_status" ]; then
        echo -e "${GREEN}✅ PASS${NC} (Status: $status)"
        return 0
    else
        echo -e "${RED}❌ FAIL${NC} (Expected: $expected_status, Got: $status)"
        return 1
    fi
}

# Function to test POST endpoint
test_post_endpoint() {
    local url="$1"
    local data="$2"
    local expected_status="$3"
    local description="$4"
    
    echo -n "Testing $description... "
    
    response=$(curl -s -w "%{http_code}" -X POST "$url" \
        -H "Content-Type: application/json" \
        -d "$data")
    
    status="${response: -3}"
    body="${response%???}"
    
    if [ "$status" = "$expected_status" ]; then
        echo -e "${GREEN}✅ PASS${NC} (Status: $status)"
        echo "$body" | head -1
        return 0
    else
        echo -e "${RED}❌ FAIL${NC} (Expected: $expected_status, Got: $status)"
        echo "$body"
        return 1
    fi
}

# Function to test with authentication
test_auth_endpoint() {
    local url="$1"
    local token="$2"
    local expected_status="$3"
    local description="$4"
    
    echo -n "Testing $description... "
    
    status=$(curl -s -o /dev/null -w "%{http_code}" "$url" \
        -H "Authorization: Bearer $token")
    
    if [ "$status" = "$expected_status" ]; then
        echo -e "${GREEN}✅ PASS${NC} (Status: $status)"
        return 0
    else
        echo -e "${RED}❌ FAIL${NC} (Expected: $expected_status, Got: $status)"
        return 1
    fi
}

# Test local deployment
echo -e "\n${YELLOW}🏠 Testing Local Deployment${NC}"
echo "=========================="

# Start local server in background
echo "Starting local FastAPI server..."
source venv/bin/activate
python -c "
import uvicorn
from main import app
uvicorn.run(app, host='0.0.0.0', port=8000, log_level='error')
" &
SERVER_PID=$!

# Wait for server to start
sleep 3

# Test basic endpoints
test_endpoint "$LOCAL_URL/" "200" "Frontend (/)"
test_endpoint "$LOCAL_URL/docs" "200" "API Documentation (/docs)"
test_endpoint "$LOCAL_URL/api/login" "405" "Login endpoint exists (GET should fail)"

# Test login
echo -e "\n${BLUE}🔐 Testing Authentication${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$LOCAL_URL/api/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$TEST_USERNAME\", \"password\": \"$TEST_PASSWORD\"}")

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✅ Login successful${NC}"
    TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    echo "Token: ${TOKEN:0:50}..."
else
    echo -e "${RED}❌ Login failed${NC}"
    echo "$LOGIN_RESPONSE"
    TOKEN=""
fi

# Test authenticated endpoints
if [ -n "$TOKEN" ]; then
    echo -e "\n${BLUE}🔒 Testing Authenticated Endpoints${NC}"
    test_auth_endpoint "$LOCAL_URL/api/me" "$TOKEN" "200" "User profile (/api/me)"
    test_auth_endpoint "$LOCAL_URL/images" "$TOKEN" "200" "Image list (/images)"
    test_auth_endpoint "$LOCAL_URL/yard-sales" "$TOKEN" "200" "Yard sales list (/yard-sales)"
fi

# Stop local server
echo -e "\nStopping local server..."
kill $SERVER_PID 2>/dev/null || true
sleep 2

# Test remote deployment
echo -e "\n${YELLOW}🌐 Testing Remote Deployment${NC}"
echo "============================="

# Test basic endpoints
test_endpoint "$REMOTE_URL/" "200" "Frontend (/)"
test_endpoint "$REMOTE_URL/docs" "200" "API Documentation (/docs)"
test_endpoint "$REMOTE_URL/api/login" "405" "Login endpoint exists (GET should fail)"

# Test login
echo -e "\n${BLUE}🔐 Testing Remote Authentication${NC}"
REMOTE_LOGIN_RESPONSE=$(curl -s -X POST "$REMOTE_URL/api/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$TEST_USERNAME\", \"password\": \"$TEST_PASSWORD\"}")

if echo "$REMOTE_LOGIN_RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✅ Remote login successful${NC}"
    REMOTE_TOKEN=$(echo "$REMOTE_LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    echo "Token: ${REMOTE_TOKEN:0:50}..."
else
    echo -e "${RED}❌ Remote login failed${NC}"
    echo "$REMOTE_LOGIN_RESPONSE"
    REMOTE_TOKEN=""
fi

# Test authenticated endpoints
if [ -n "$REMOTE_TOKEN" ]; then
    echo -e "\n${BLUE}🔒 Testing Remote Authenticated Endpoints${NC}"
    test_auth_endpoint "$REMOTE_URL/api/me" "$REMOTE_TOKEN" "200" "User profile (/api/me)"
    test_auth_endpoint "$REMOTE_URL/images" "$REMOTE_TOKEN" "200" "Image list (/images)"
    test_auth_endpoint "$REMOTE_URL/yard-sales" "$REMOTE_TOKEN" "200" "Yard sales list (/yard-sales)"
fi

# Test image upload (if token available)
if [ -n "$REMOTE_TOKEN" ]; then
    echo -e "\n${BLUE}📸 Testing Image Upload${NC}"
    
    # Create a test image
    echo "Creating test image..."
    convert -size 100x100 xc:red test_image.png 2>/dev/null || \
    python3 -c "
from PIL import Image
img = Image.new('RGB', (100, 100), color='red')
img.save('test_image.png')
" 2>/dev/null || \
    echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==" | base64 -d > test_image.png
    
    if [ -f "test_image.png" ]; then
        echo -n "Testing image upload... "
        UPLOAD_RESPONSE=$(curl -s -X POST "$REMOTE_URL/upload/image" \
            -H "Authorization: Bearer $REMOTE_TOKEN" \
            -F "file=@test_image.png")
        
        if echo "$UPLOAD_RESPONSE" | grep -q "success.*true"; then
            echo -e "${GREEN}✅ Upload successful${NC}"
            echo "$UPLOAD_RESPONSE" | head -1
        else
            echo -e "${RED}❌ Upload failed${NC}"
            echo "$UPLOAD_RESPONSE"
        fi
        
        # Clean up test image
        rm -f test_image.png
    else
        echo -e "${YELLOW}⚠️  Could not create test image${NC}"
    fi
fi

echo -e "\n${GREEN}🎉 Test Suite Complete!${NC}"
echo "=========================="
echo -e "Local URL: ${BLUE}$LOCAL_URL${NC}"
echo -e "Remote URL: ${BLUE}$REMOTE_URL${NC}"
echo ""
echo "If all tests passed, your deployment is working correctly!"
echo "You can now access your image upload system at:"
echo -e "  🌐 Frontend: ${BLUE}$REMOTE_URL/${NC}"
echo -e "  📚 API Docs: ${BLUE}$REMOTE_URL/docs${NC}"
echo -e "  🔧 API Base: ${BLUE}$REMOTE_URL/api/${NC}"

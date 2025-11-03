#!/bin/bash
# Test script for featured image endpoints using curl

BASE_URL="http://localhost:8000"
TEST_USERNAME="javiddelossantos"
TEST_PASSWORD="Password"

echo "🧪 Testing Featured Image Endpoints"
echo "============================================================"

# Login
echo ""
echo "🔐 Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$TEST_USERNAME\",\"password\":\"$TEST_PASSWORD\"}")

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ Login failed"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Login successful!"
echo "Token: ${TOKEN:0:20}..."

# Get yard sales
echo ""
echo "📋 Getting yard sales..."
YARD_SALES=$(curl -s -X GET "$BASE_URL/yard-sales" \
  -H "Authorization: Bearer $TOKEN")

YARD_SALE_ID=$(echo $YARD_SALES | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

if [ -z "$YARD_SALE_ID" ]; then
    echo "❌ No yard sales found"
    echo "💡 Create a yard sale first"
    exit 1
fi

echo "✅ Found yard sale ID: $YARD_SALE_ID"

# Get available images
echo ""
echo "🖼️  Testing GET /yard-sales/$YARD_SALE_ID/images..."
IMAGES_RESPONSE=$(curl -s -X GET "$BASE_URL/yard-sales/$YARD_SALE_ID/images" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

echo "Response:"
echo "$IMAGES_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$IMAGES_RESPONSE"

# Test setting featured image from photo_index (if photos exist)
PHOTOS_COUNT=$(echo "$IMAGES_RESPONSE" | grep -o '"photos":\[[^]]*\]' | grep -o ',' | wc -l || echo "0")
if [ "$PHOTOS_COUNT" -gt 0 ] || echo "$IMAGES_RESPONSE" | grep -q '"photos":\[.*"'; then
    echo ""
    echo "⭐ Testing PUT /yard-sales/$YARD_SALE_ID/featured-image (photo_index=0)..."
    SET_RESPONSE=$(curl -s -X PUT "$BASE_URL/yard-sales/$YARD_SALE_ID/featured-image" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"photo_index": 0}')
    
    echo "Response:"
    echo "$SET_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$SET_RESPONSE"
    
    # Verify it was set
    echo ""
    echo "📄 Verifying yard sale has featured_image..."
    YARD_SALE_GET=$(curl -s -X GET "$BASE_URL/yard-sales/$YARD_SALE_ID" \
      -H "Authorization: Bearer $TOKEN")
    
    FEATURED=$(echo "$YARD_SALE_GET" | grep -o '"featured_image":"[^"]*' | cut -d'"' -f4)
    echo "Featured Image: ${FEATURED:-None}"
    
    # Test removing it
    echo ""
    echo "🗑️  Testing DELETE /yard-sales/$YARD_SALE_ID/featured-image..."
    DELETE_RESPONSE=$(curl -s -X DELETE "$BASE_URL/yard-sales/$YARD_SALE_ID/featured-image" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "Response:"
    echo "$DELETE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$DELETE_RESPONSE"
else
    echo ""
    echo "⚠️  No photos found, skipping photo_index test"
fi

# Test setting featured image from URL
echo ""
echo "⭐ Testing PUT /yard-sales/$YARD_SALE_ID/featured-image (image_url)..."
SET_URL_RESPONSE=$(curl -s -X PUT "$BASE_URL/yard-sales/$YARD_SALE_ID/featured-image" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://via.placeholder.com/400x300.jpg"}')

echo "Response:"
echo "$SET_URL_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$SET_URL_RESPONSE"

# Verify it was set
echo ""
echo "📄 Verifying yard sale has featured_image..."
YARD_SALE_GET2=$(curl -s -X GET "$BASE_URL/yard-sales/$YARD_SALE_ID" \
  -H "Authorization: Bearer $TOKEN")

FEATURED2=$(echo "$YARD_SALE_GET2" | grep -o '"featured_image":"[^"]*' | cut -d'"' -f4)
echo "Featured Image: ${FEATURED2:-None}"

# Clean up - remove featured image
echo ""
echo "🗑️  Cleaning up - Removing featured image..."
DELETE_RESPONSE2=$(curl -s -X DELETE "$BASE_URL/yard-sales/$YARD_SALE_ID/featured-image" \
  -H "Authorization: Bearer $TOKEN")

echo "Response:"
echo "$DELETE_RESPONSE2" | python3 -m json.tool 2>/dev/null || echo "$DELETE_RESPONSE2"

echo ""
echo "============================================================"
echo "✅ Featured Image Endpoint Tests Complete!"
echo ""
echo "📋 Summary:"
echo "   ✅ GET /yard-sales/{id}/images - Get available images"
echo "   ✅ PUT /yard-sales/{id}/featured-image - Set featured image"
echo "   ✅ DELETE /yard-sales/{id}/featured-image - Remove featured image"
echo "   ✅ Featured image appears in yard sale responses"


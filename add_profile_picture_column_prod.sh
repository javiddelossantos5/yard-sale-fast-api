#!/bin/bash

# Script to add profile_picture column to users table in production Docker MySQL container
# This script connects to the MySQL container and adds the column

set -e  # Exit on error

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Try to detect container name from docker-compose.yml
if [ -f "docker-compose.yml" ]; then
    # Extract container_name from docker-compose.yml for db service
    CONTAINER_NAME=$(grep -A 20 "^  db:" docker-compose.yml | grep "container_name:" | awk '{print $2}' | tr -d '"' || echo "")
    
    # If not found, try to get it from running containers
    if [ -z "$CONTAINER_NAME" ]; then
        CONTAINER_NAME=$(docker-compose ps -q db 2>/dev/null | xargs docker inspect --format '{{.Name}}' 2>/dev/null | sed 's/\///' || echo "")
    fi
fi

# Fallback: try common container names
if [ -z "$CONTAINER_NAME" ]; then
    # Check for mysql-db (from docker-compose.yml)
    if docker ps --format '{{.Names}}' | grep -q "^mysql-db$"; then
        CONTAINER_NAME="mysql-db"
    # Check for fast-api-test-db-1 (old naming)
    elif docker ps --format '{{.Names}}' | grep -q "^fast-api-test-db-1$"; then
        CONTAINER_NAME="fast-api-test-db-1"
    # Try to find any mysql container
    else
        CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep -i mysql | head -1 || echo "")
    fi
fi

# Database credentials (from docker-compose.yml)
DATABASE_NAME="fastapi_db"  # From docker-compose.yml
MYSQL_USER="root"
MYSQL_PASSWORD="password"  # From docker-compose.yml MYSQL_ROOT_PASSWORD

echo "🚀 Adding profile_picture column to users table (production)..."
echo ""

# Check if container is running
if [ -z "$CONTAINER_NAME" ]; then
    echo "❌ Error: Could not find MySQL container"
    echo "   Please make sure docker-compose is running:"
    echo "   docker-compose up -d"
    echo ""
    echo "   Available containers:"
    docker ps --format "   - {{.Names}}" || echo "   (no containers running)"
    exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Error: Docker container '${CONTAINER_NAME}' is not running"
    echo "   Please start the container first:"
    echo "   docker-compose up -d"
    echo ""
    echo "   Available containers:"
    docker ps --format "   - {{.Names}}" || echo "   (no containers running)"
    exit 1
fi

echo "✅ Found MySQL container: ${CONTAINER_NAME}"
echo ""

echo "🔍 Checking if profile_picture column already exists..."

# Check if column exists
COLUMN_EXISTS=$(docker exec ${CONTAINER_NAME} mysql -u${MYSQL_USER} -p${MYSQL_PASSWORD} ${DATABASE_NAME} -sN -e "
    SELECT COUNT(*) 
    FROM information_schema.COLUMNS 
    WHERE TABLE_SCHEMA = '${DATABASE_NAME}' 
    AND TABLE_NAME = 'users' 
    AND COLUMN_NAME = 'profile_picture';
" 2>/dev/null || echo "0")

if [ "$COLUMN_EXISTS" = "1" ]; then
    echo "✅ Column 'profile_picture' already exists in 'users' table"
    exit 0
fi

echo "➕ Adding profile_picture column to users table..."

# Add the column
docker exec ${CONTAINER_NAME} mysql -u${MYSQL_USER} -p${MYSQL_PASSWORD} ${DATABASE_NAME} -e "
    ALTER TABLE users 
    ADD COLUMN profile_picture VARCHAR(500) NULL 
    COMMENT 'URL to profile picture (optional)' 
    AFTER zip_code;
" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Successfully added profile_picture column to users table"
    
    # Verify the column was added
    echo ""
    echo "🔍 Verifying column was added..."
    docker exec ${CONTAINER_NAME} mysql -u${MYSQL_USER} -p${MYSQL_PASSWORD} ${DATABASE_NAME} -e "
        DESCRIBE users;
    " 2>/dev/null | grep -i profile_picture && echo "✅ Verification successful!" || echo "⚠️  Column may not be visible in DESCRIBE output"
else
    echo "❌ Error: Failed to add profile_picture column"
    echo ""
    echo "📋 Manual SQL (run this in your MySQL client):"
    echo "   ALTER TABLE users ADD COLUMN profile_picture VARCHAR(500) NULL COMMENT 'URL to profile picture (optional)' AFTER zip_code;"
    exit 1
fi

echo ""
echo "✅ Migration complete!"


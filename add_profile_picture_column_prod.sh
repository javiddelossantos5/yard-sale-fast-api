#!/bin/bash

# Script to add profile_picture column to users table in production Docker MySQL container
# This script connects to the MySQL container and adds the column

set -e  # Exit on error

CONTAINER_NAME="fast-api-test-db-1"  # Adjust if your container name is different
DATABASE_NAME="yardsale"  # Adjust if your database name is different
MYSQL_USER="root"
MYSQL_PASSWORD="supersecretpassword"  # Adjust to match your MySQL password

echo "🚀 Adding profile_picture column to users table (production)..."
echo ""

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Error: Docker container '${CONTAINER_NAME}' is not running"
    echo "   Please start the container first:"
    echo "   docker-compose up -d"
    exit 1
fi

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


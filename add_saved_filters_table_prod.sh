#!/bin/bash
# Script to add saved_filters table to production database
# Uses root password: supersecretpassword (from docker-compose)
# Database: yardsale
# Container: yard-sale-db

echo "🚀 Creating saved_filters table (PRODUCTION)..."
echo "📋 Database: yardsale"
echo "📋 Container: yard-sale-db"
echo ""

# Check if Docker container exists
if ! docker ps | grep -q yard-sale-db; then
    echo "❌ Docker container 'yard-sale-db' is not running"
    echo "💡 Please make sure your database container is running"
    exit 1
fi

# Check what type users.id is
echo "📋 Checking users.id column type..."
USER_ID_TYPE=$(docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale -sN -e "SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='yardsale' AND TABLE_NAME='users' AND COLUMN_NAME='id';" 2>/dev/null)

if [ -z "$USER_ID_TYPE" ]; then
    echo "⚠️  Could not determine users.id type, defaulting to CHAR(36)"
    USER_ID_TYPE="CHAR(36)"
else
    echo "✅ Found users.id type: $USER_ID_TYPE"
fi

# Get full column definition including character set and collation
echo "🔍 Getting full users.id column definition..."
USER_ID_DEF=$(docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale -sN -e "SELECT CONCAT(COLUMN_TYPE, ' CHARACTER SET ', CHARACTER_SET_NAME, ' COLLATE ', COLLATION_NAME) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='yardsale' AND TABLE_NAME='users' AND COLUMN_NAME='id';" 2>/dev/null)

if [ -z "$USER_ID_DEF" ]; then
    echo "⚠️  Could not determine users.id full definition, using CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    USER_ID_DEF="CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
else
    echo "✅ Found users.id definition: $USER_ID_DEF"
fi

# Create saved_filters table
echo "📋 Creating 'saved_filters' table..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<EOF 2>/dev/null
CREATE TABLE IF NOT EXISTS saved_filters (
    id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci PRIMARY KEY,
    user_id $USER_ID_DEF NOT NULL,
    filter_type VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    filters JSON NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    
    INDEX idx_user_id (user_id),
    INDEX idx_filter_type (filter_type),
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
EOF

if [ $? -eq 0 ]; then
    echo "✅ saved_filters table created successfully"
    
    # Add foreign key constraint separately
    echo "📋 Adding foreign key constraint..."
    docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'EOF' 2>/dev/null
ALTER TABLE saved_filters 
ADD CONSTRAINT saved_filters_ibfk_user 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
EOF
    
    if [ $? -eq 0 ]; then
        echo "✅ Foreign key constraint added successfully"
    else
        echo "ℹ️  Foreign key constraint may already exist (this is okay)"
    fi
else
    echo "❌ Error creating saved_filters table"
    exit 1
fi

echo ""
echo "💡 Verifying table was created..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale -e "SHOW TABLES LIKE 'saved_filters';" 2>/dev/null
echo ""
echo "✅ Migration completed successfully!"
echo ""
echo "📝 Next steps:"
echo "   1. Deploy the updated code: ./deploy.sh"
echo "   2. Restart the backend container if needed"
echo ""
echo "💡 To verify the table exists, run:"
echo "   docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale -e \"DESCRIBE saved_filters;\""


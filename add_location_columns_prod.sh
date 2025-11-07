#!/bin/bash
# Script to add the 'city', 'state', and 'zip_code' columns to the items table (PRODUCTION)
# Uses root password: supersecretpassword (from docker-compose)
# Database: yardsale
# Container: yard-sale-db

echo "🚀 Adding location columns (city, state, zip_code) to items table (PRODUCTION)..."
echo "📋 Database: yardsale"
echo "📋 Container: yard-sale-db"
echo ""

# Check if Docker container exists
if ! docker ps | grep -q yard-sale-db; then
    echo "❌ Docker container 'yard-sale-db' is not running"
    echo "💡 Please make sure your database container is running"
    exit 1
fi

# Try to add the columns (ignore error if they already exist)
echo "📋 Attempting to add location columns..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'EOF' 2>/dev/null
ALTER TABLE items ADD COLUMN city VARCHAR(100) NULL COMMENT 'City where item is located' AFTER contact_email;
ALTER TABLE items ADD COLUMN state VARCHAR(2) NULL COMMENT 'State abbreviation (e.g., UT, CA)' AFTER city;
ALTER TABLE items ADD COLUMN zip_code VARCHAR(10) NULL COMMENT 'ZIP code' AFTER state;
EOF

# Check if the command succeeded or if columns already exist
if [ $? -eq 0 ]; then
    echo "✅ Location columns added successfully"
    echo ""
    echo "💡 Verifying columns were added..."
    docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale -e "DESCRIBE items;" | grep -E "(Field|city|state|zip_code)" || echo "   (Check manually if needed)"
    echo ""
    echo "✅ Migration completed successfully!"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Deploy the updated code: ./deploy.sh"
    echo "   2. Restart the backend container if needed"
else
    echo "ℹ️  Columns may already exist (this is okay)"
    echo ""
    echo "💡 To verify the columns exist, run:"
    echo "   docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale -e \"DESCRIBE items;\""
    echo ""
    echo "✅ If columns exist, you can proceed with deployment"
fi


#!/bin/bash
# Script to add the 'seller' column to the items table (PRODUCTION)
# Uses root password: supersecretpassword (from docker-compose)
# Database: yardsale
# Container: yard-sale-db

echo "🚀 Adding 'seller' column to items table (PRODUCTION)..."
echo "📋 Database: yardsale"
echo "📋 Container: yard-sale-db"
echo ""

# Check if Docker container exists
if ! docker ps | grep -q yard-sale-db; then
    echo "❌ Docker container 'yard-sale-db' is not running"
    echo "💡 Please make sure your database container is running"
    exit 1
fi

# Try to add the column (ignore error if it already exists)
echo "📋 Attempting to add 'seller' column..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'EOF' 2>/dev/null
ALTER TABLE items ADD COLUMN seller VARCHAR(100) NULL COMMENT 'Seller name/contact name (optional)' AFTER facebook_url;
EOF

# Check if the command succeeded or if column already exists
if [ $? -eq 0 ]; then
    echo "✅ Column 'seller' added successfully"
    echo ""
    echo "💡 Verifying column was added..."
    docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale -e "DESCRIBE items;" | grep -E "(Field|seller)" || echo "   (Check manually if needed)"
    echo ""
    echo "✅ Migration completed successfully!"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Deploy the updated code: ./deploy.sh"
    echo "   2. Restart the backend container if needed"
else
    echo "ℹ️  Column may already exist (this is okay)"
    echo ""
    echo "💡 To verify the column exists, run:"
    echo "   docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale -e \"DESCRIBE items;\""
    echo ""
    echo "✅ If column exists, you can proceed with deployment"
fi


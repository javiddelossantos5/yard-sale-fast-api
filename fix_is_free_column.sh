#!/bin/bash
# Script to add is_free column to items table
# Uses root password: supersecretpassword (from docker-compose)

echo "🚀 Adding is_free column to items table..."

# Try to add the column (ignore error if it already exists)
echo "📋 Attempting to add is_free column..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'EOF' 2>/dev/null
ALTER TABLE items ADD COLUMN is_free BOOLEAN DEFAULT FALSE NOT NULL;
EOF

# Check if the command succeeded or if column already exists
if [ $? -eq 0 ]; then
    echo "✅ Column 'is_free' added successfully"
else
    echo "ℹ️  Column may already exist (this is okay)"
fi

# Update existing items with price = 0 to have is_free = TRUE
echo "🔄 Updating existing items with price 0.0..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'EOF'
UPDATE items SET is_free = TRUE WHERE price = 0.0;
SELECT CONCAT('Updated ', ROW_COUNT(), ' items') AS result;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Migration completed successfully!"
    echo ""
    echo "💡 You can verify by running:"
    echo "   docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale -e \"DESCRIBE items;\""
else
    echo "❌ Error updating items. Please check the error above."
    exit 1
fi


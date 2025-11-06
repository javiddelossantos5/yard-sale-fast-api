#!/bin/bash
# Script to add is_free column - tries multiple password options

echo "🔍 Checking MySQL container environment..."
docker exec yard-sale-db env | grep MYSQL

echo ""
echo "🔍 Trying to connect with yardsaleuser account..."
# Try with yardsaleuser account (from docker-compose.db.yml)
docker exec -i yard-sale-db mysql -uyardsaleuser -pyardpass yardsale <<'EOF'
ALTER TABLE items ADD COLUMN IF NOT EXISTS is_free BOOLEAN DEFAULT FALSE NOT NULL;
UPDATE items SET is_free = TRUE WHERE price = 0.0;
SELECT 'Migration completed successfully!' AS result;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Success! Column added using yardsaleuser account."
    exit 0
fi

echo ""
echo "⚠️  yardsaleuser failed, trying root with different passwords..."

# Try root with supersecretpassword (from earlier messages)
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'EOF'
ALTER TABLE items ADD COLUMN IF NOT EXISTS is_free BOOLEAN DEFAULT FALSE NOT NULL;
UPDATE items SET is_free = TRUE WHERE price = 0.0;
SELECT 'Migration completed successfully!' AS result;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Success! Column added using root with tpassworsupersecred."
    exit 0
fi

echo ""
echo "❌ All attempts failed. Please check your MySQL password."
echo "💡 You can check the password by running:"
echo "   docker exec yard-sale-db env | grep MYSQL_ROOT_PASSWORD"


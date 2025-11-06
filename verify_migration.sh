#!/bin/bash
# Script to verify the is_free column exists and check table structure

echo "🔍 Verifying is_free column exists in items table..."
echo ""

docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'EOF'
-- Show table structure
DESCRIBE items;

-- Show a sample of items with is_free status
SELECT id, name, price, is_free FROM items LIMIT 5;
EOF

echo ""
echo "✅ Verification complete!"


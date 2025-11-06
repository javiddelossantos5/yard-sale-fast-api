#!/bin/bash
# Script to add is_free column via Docker exec

echo "🚀 Adding is_free column to items table..."

# Run SQL commands directly via docker exec
docker exec -i yard-sale-db mysql -uroot -prootpassword yardsale <<EOF
ALTER TABLE items ADD COLUMN is_free BOOLEAN DEFAULT FALSE NOT NULL;
UPDATE items SET is_free = TRUE WHERE price = 0.0;
EOF

echo "✅ Migration completed!"


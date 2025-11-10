#!/bin/bash
# Script to create event_conversations and event_messages tables (PRODUCTION)
# Uses root password: supersecretpassword (from docker-compose)
# Database: yardsale
# Container: yard-sale-db

echo "🚀 Creating event_conversations and event_messages tables (PRODUCTION)..."
echo "📋 Database: yardsale"
echo "📋 Container: yard-sale-db"
echo ""

# Check if Docker container exists
if ! docker ps | grep -q yard-sale-db; then
    echo "❌ Docker container 'yard-sale-db' is not running"
    echo "💡 Please make sure your database container is running"
    exit 1
fi

# Detect the users.id column type dynamically
echo "🔍 Detecting users.id column type..."
USER_ID_TYPE=$(docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale -N -e "
    SELECT COLUMN_TYPE 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = 'yardsale' 
    AND TABLE_NAME = 'users' 
    AND COLUMN_NAME = 'id';
" 2>/dev/null)

if [ -z "$USER_ID_TYPE" ]; then
    echo "⚠️  Could not detect users.id type, defaulting to CHAR(36)"
    USER_ID_TYPE="CHAR(36)"
fi

echo "✅ Detected users.id type: $USER_ID_TYPE"
echo ""

# Create event_conversations table
echo "📋 Creating event_conversations table..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<EOF
CREATE TABLE IF NOT EXISTS event_conversations (
    id $USER_ID_TYPE PRIMARY KEY,
    event_id $USER_ID_TYPE NOT NULL,
    participant1_id $USER_ID_TYPE NOT NULL COMMENT 'Inquirer',
    participant2_id $USER_ID_TYPE NOT NULL COMMENT 'Event organizer',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    INDEX idx_event_id (event_id),
    INDEX idx_participant1 (participant1_id),
    INDEX idx_participant2 (participant2_id),
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (participant1_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (participant2_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
EOF

if [ $? -eq 0 ]; then
    echo "✅ event_conversations table created successfully"
else
    echo "⚠️  event_conversations table may already exist or there was an error"
fi

# Create event_messages table
echo ""
echo "📋 Creating event_messages table..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<EOF
CREATE TABLE IF NOT EXISTS event_messages (
    id $USER_ID_TYPE PRIMARY KEY,
    content TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at DATETIME NOT NULL,
    conversation_id $USER_ID_TYPE NOT NULL,
    sender_id $USER_ID_TYPE NOT NULL,
    recipient_id $USER_ID_TYPE NOT NULL,
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_sender_id (sender_id),
    INDEX idx_recipient_id (recipient_id),
    INDEX idx_is_read (is_read),
    FOREIGN KEY (conversation_id) REFERENCES event_conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
EOF

if [ $? -eq 0 ]; then
    echo "✅ event_messages table created successfully"
else
    echo "⚠️  event_messages table may already exist or there was an error"
fi

echo ""
echo "💡 Verifying tables were created..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale -e "SHOW TABLES LIKE 'event_%';" 2>/dev/null

echo ""
echo "✅ Migration completed!"
echo ""
echo "📝 Next steps:"
echo "   1. The tables should now be available"
echo "   2. Test the endpoints: /events/conversations and /events/messages/unread-count"


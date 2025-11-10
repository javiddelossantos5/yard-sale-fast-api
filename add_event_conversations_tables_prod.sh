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

# Check actual column definitions to ensure compatibility
echo "🔍 Checking column types for foreign key compatibility..."
USER_ID_DEF=$(docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale -sN -e "
    SELECT CONCAT(COLUMN_TYPE, ' ', IFNULL(CHARACTER_SET_NAME, ''), ' ', IFNULL(COLLATION_NAME, ''))
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = 'yardsale' 
    AND TABLE_NAME = 'users' 
    AND COLUMN_NAME = 'id';
" 2>/dev/null)

EVENT_ID_DEF=$(docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale -sN -e "
    SELECT CONCAT(COLUMN_TYPE, ' ', IFNULL(CHARACTER_SET_NAME, ''), ' ', IFNULL(COLLATION_NAME, ''))
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = 'yardsale' 
    AND TABLE_NAME = 'events' 
    AND COLUMN_NAME = 'id';
" 2>/dev/null)

echo "📋 users.id definition: $USER_ID_DEF"
echo "📋 events.id definition: $EVENT_ID_DEF"
echo ""

# Drop existing tables if they exist (in case of previous failed attempts)
echo "📋 Dropping existing tables if they exist..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'DROPEOF' 2>/dev/null
DROP TABLE IF EXISTS event_messages;
DROP TABLE IF EXISTS event_conversations;
DROPEOF

# Create event_conversations table (without foreign keys first)
# Note: participant columns use utf8mb4_0900_ai_ci to match users.id collation
echo "📋 Creating event_conversations table..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<EOF
CREATE TABLE event_conversations (
    id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci PRIMARY KEY,
    event_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    participant1_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'Inquirer',
    participant2_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'Event organizer',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    INDEX idx_event_id (event_id),
    INDEX idx_participant1 (participant1_id),
    INDEX idx_participant2 (participant2_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
EOF

if [ $? -eq 0 ]; then
    echo "✅ event_conversations table created successfully"
    
    # Add foreign key constraints separately
    echo "📋 Adding foreign key constraints to event_conversations..."
    docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'FKEOF' 2>/dev/null
ALTER TABLE event_conversations 
ADD CONSTRAINT event_conversations_ibfk_event 
FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE;

ALTER TABLE event_conversations 
ADD CONSTRAINT event_conversations_ibfk_participant1 
FOREIGN KEY (participant1_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE event_conversations 
ADD CONSTRAINT event_conversations_ibfk_participant2 
FOREIGN KEY (participant2_id) REFERENCES users(id) ON DELETE CASCADE;
FKEOF
    
    if [ $? -eq 0 ]; then
        echo "✅ Foreign key constraints added successfully"
    else
        echo "ℹ️  Foreign key constraints may already exist (this is okay)"
    fi
else
    echo "⚠️  event_conversations table may already exist or there was an error"
fi

# Create event_messages table (without foreign keys first)
# Note: sender_id and recipient_id use utf8mb4_0900_ai_ci to match users.id collation
echo ""
echo "📋 Creating event_messages table..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<EOF
CREATE TABLE event_messages (
    id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci PRIMARY KEY,
    content TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at DATETIME NOT NULL,
    conversation_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    sender_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    recipient_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_sender_id (sender_id),
    INDEX idx_recipient_id (recipient_id),
    INDEX idx_is_read (is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
EOF

if [ $? -eq 0 ]; then
    echo "✅ event_messages table created successfully"
    
    # Add foreign key constraints separately
    echo "📋 Adding foreign key constraints to event_messages..."
    docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'FKEOF' 2>/dev/null
ALTER TABLE event_messages 
ADD CONSTRAINT event_messages_ibfk_conversation 
FOREIGN KEY (conversation_id) REFERENCES event_conversations(id) ON DELETE CASCADE;

ALTER TABLE event_messages 
ADD CONSTRAINT event_messages_ibfk_sender 
FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE event_messages 
ADD CONSTRAINT event_messages_ibfk_recipient 
FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE;
FKEOF
    
    if [ $? -eq 0 ]; then
        echo "✅ Foreign key constraints added successfully"
    else
        echo "ℹ️  Foreign key constraints may already exist (this is okay)"
    fi
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


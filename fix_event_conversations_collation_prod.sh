#!/bin/bash
# Script to fix collation for event_conversations and event_messages tables (PRODUCTION)
# Fixes collation mismatch that prevents foreign key constraints

echo "🔧 Fixing collation for event conversation tables (PRODUCTION)..."
echo ""

# Check if Docker container exists
if ! docker ps | grep -q yard-sale-db; then
    echo "❌ Docker container 'yard-sale-db' is not running"
    exit 1
fi

echo "📋 Fixing event_conversations table collations..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'FIXEOF'
-- Fix participant columns to match users.id collation (utf8mb4_0900_ai_ci)
ALTER TABLE event_conversations 
MODIFY COLUMN participant1_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'Inquirer';

ALTER TABLE event_conversations 
MODIFY COLUMN participant2_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'Event organizer';

-- Fix event_id to match events.id collation (utf8mb4_unicode_ci)
ALTER TABLE event_conversations 
MODIFY COLUMN event_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
FIXEOF

if [ $? -eq 0 ]; then
    echo "✅ event_conversations collations fixed"
else
    echo "⚠️  Error fixing event_conversations collations"
fi

echo ""
echo "📋 Fixing event_messages table collations..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'FIXEOF'
-- Fix sender and recipient columns to match users.id collation (utf8mb4_0900_ai_ci)
ALTER TABLE event_messages 
MODIFY COLUMN sender_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL;

ALTER TABLE event_messages 
MODIFY COLUMN recipient_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL;
FIXEOF

if [ $? -eq 0 ]; then
    echo "✅ event_messages collations fixed"
else
    echo "⚠️  Error fixing event_messages collations"
fi

echo ""
echo "📋 Adding foreign key constraints..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'FKEOF' 2>&1
-- Add foreign key constraints to event_conversations
-- (If they already exist, MySQL will return an error which we'll ignore)
ALTER TABLE event_conversations 
ADD CONSTRAINT event_conversations_ibfk_event 
FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE;

ALTER TABLE event_conversations 
ADD CONSTRAINT event_conversations_ibfk_participant1 
FOREIGN KEY (participant1_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE event_conversations 
ADD CONSTRAINT event_conversations_ibfk_participant2 
FOREIGN KEY (participant2_id) REFERENCES users(id) ON DELETE CASCADE;

-- Add foreign key constraints to event_messages
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

FK_EXIT_CODE=$?
if [ $FK_EXIT_CODE -eq 0 ]; then
    echo "✅ Foreign key constraints added successfully"
else
    echo "ℹ️  Some foreign key constraints may already exist (this is okay)"
    echo "   Check the output above for any actual errors"
fi

echo ""
echo "✅ Collation fix completed!"
echo ""
echo "📝 Next steps:"
echo "   1. Test the endpoints: /events/conversations and /events/messages/unread-count"
echo "   2. Verify foreign keys were added: SHOW CREATE TABLE event_conversations;"


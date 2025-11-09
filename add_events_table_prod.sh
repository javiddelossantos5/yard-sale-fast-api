#!/bin/bash
# Script to add events and event_comments tables to production database
# Uses root password: supersecretpassword (from docker-compose)
# Database: yardsale
# Container: yard-sale-db

echo "🚀 Creating events and event_comments tables (PRODUCTION)..."
echo "📋 Database: yardsale"
echo "📋 Container: yard-sale-db"
echo ""

# Check if Docker container exists
if ! docker ps | grep -q yard-sale-db; then
    echo "❌ Docker container 'yard-sale-db' is not running"
    echo "💡 Please make sure your database container is running"
    exit 1
fi

# Create events table
echo "📋 Creating 'events' table..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'EOF'
CREATE TABLE IF NOT EXISTS events (
    id CHAR(36) PRIMARY KEY,
    type VARCHAR(20) NOT NULL DEFAULT 'event',
    title VARCHAR(150) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'upcoming',
    is_public BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Location & Time
    address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    zip VARCHAR(10),
    location_type VARCHAR(20),
    start_date DATE,
    end_date DATE,
    start_time TIME,
    end_time TIME,
    timezone VARCHAR(50),
    
    -- Pricing
    price DECIMAL(10, 2),
    is_free BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Filtering & Search
    tags JSON,
    age_restriction VARCHAR(20),
    
    -- Organizer
    organizer_id CHAR(36) NOT NULL,
    organizer_name VARCHAR(150),
    company VARCHAR(150),
    contact_phone VARCHAR(20),
    contact_email VARCHAR(150),
    facebook_url VARCHAR(255),
    instagram_url VARCHAR(255),
    website VARCHAR(255),
    
    -- Engagement
    comments_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Media
    gallery_urls JSON,
    featured_image VARCHAR(500),
    
    -- Metadata
    created_at DATETIME NOT NULL,
    last_updated DATETIME NOT NULL,
    
    FOREIGN KEY (organizer_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_organizer_id (organizer_id),
    INDEX idx_type (type),
    INDEX idx_status (status),
    INDEX idx_is_public (is_public),
    INDEX idx_is_free (is_free),
    INDEX idx_location_type (location_type),
    INDEX idx_city (city),
    INDEX idx_state (state),
    INDEX idx_start_date (start_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Events table created successfully"
else
    echo "❌ Error creating events table"
    exit 1
fi

# Create event_comments table
echo "📋 Creating 'event_comments' table..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'EOF'
CREATE TABLE IF NOT EXISTS event_comments (
    id CHAR(36) PRIMARY KEY,
    event_id CHAR(36) NOT NULL,
    user_id CHAR(36) NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_event_id (event_id),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Event comments table created successfully"
else
    echo "❌ Error creating event_comments table"
    exit 1
fi

echo ""
echo "✅ Migration completed successfully!"
echo ""
echo "📝 Next steps:"
echo "   1. Deploy the updated code: ./deploy.sh"
echo "   2. Restart the backend container if needed"
echo ""
echo "💡 To verify tables were created, run:"
echo "   docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale -e \"SHOW TABLES LIKE 'events%';\""


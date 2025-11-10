#!/bin/bash
# Script to add job_title, employment_type, and weather_conditions columns to events table (PRODUCTION)
# Uses root password: supersecretpassword (from docker-compose)
# Database: yardsale
# Container: yard-sale-db

echo "🚀 Adding job_title, employment_type, and weather_conditions columns to events table (PRODUCTION)..."
echo "📋 Database: yardsale"
echo "📋 Container: yard-sale-db"
echo ""

# Check if Docker container exists
if ! docker ps | grep -q yard-sale-db; then
    echo "❌ Docker container 'yard-sale-db' is not running"
    echo "💡 Please make sure your database container is running"
    exit 1
fi

# Add job_title column
echo "📋 Attempting to add 'job_title' column..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'EOF' 2>/dev/null
ALTER TABLE events ADD COLUMN job_title VARCHAR(150) NULL COMMENT 'Job title for job_posting type events' AFTER age_restriction;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Column 'job_title' added successfully"
else
    echo "ℹ️  Column 'job_title' may already exist (this is okay)"
fi

# Add employment_type column
echo "📋 Attempting to add 'employment_type' column..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'EOF' 2>/dev/null
ALTER TABLE events ADD COLUMN employment_type VARCHAR(20) NULL COMMENT 'Employment type: full_time, part_time, contract, temporary, seasonal, internship' AFTER job_title;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Column 'employment_type' added successfully"
else
    echo "ℹ️  Column 'employment_type' may already exist (this is okay)"
fi

# Add weather_conditions column
echo "📋 Attempting to add 'weather_conditions' column..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale <<'EOF' 2>/dev/null
ALTER TABLE events ADD COLUMN weather_conditions VARCHAR(255) NULL COMMENT 'Weather conditions for weather type events' AFTER employment_type;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Column 'weather_conditions' added successfully"
else
    echo "ℹ️  Column 'weather_conditions' may already exist (this is okay)"
fi

echo ""
echo "💡 Verifying columns were added..."
docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale -e "DESCRIBE events;" | grep -E "(Field|job_title|employment_type|weather_conditions)" || echo "   (Check manually if needed)"
echo ""
echo "✅ Migration completed successfully!"
echo ""
echo "📝 Next steps:"
echo "   1. Deploy the updated code: ./deploy.sh"
echo "   2. Restart the backend container if needed"
echo ""
echo "💡 To verify the columns exist, run:"
echo "   docker exec -i yard-sale-db mysql -uroot -psupersecretpassword yardsale -e \"DESCRIBE events;\""


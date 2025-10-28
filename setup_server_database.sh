#!/bin/bash

# Database Setup Script for Server
# Run this to set up your database on the server

echo "🗄️ Database Setup for Docker MySQL"
echo "=================================="
echo ""

# Copy database setup script to server
echo "📤 Copying database setup script to server..."
scp setup_docker_database.py javiddelossantos@10.1.2.165:/home/javiddelossantos/fast-api-test/

# Copy other necessary files
echo "📤 Copying database files to server..."
scp database.py javiddelossantos@10.1.2.165:/home/javiddelossantos/fast-api-test/

echo "✅ Files copied successfully!"
echo ""
echo "🚀 Next steps:"
echo "1. SSH to your server: ssh javiddelossantos@10.1.2.165"
echo "2. Navigate to project: cd /home/javiddelossantos/fast-api-test"
echo "3. Make sure Docker MySQL is running: docker-compose up -d db"
echo "4. Run database setup: python3 setup_docker_database.py"
echo ""
echo "🔍 If you get import errors, make sure you have the Python dependencies:"
echo "   pip install mysql-connector-python sqlalchemy"

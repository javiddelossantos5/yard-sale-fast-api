#!/bin/bash

# Copy All Updated Files to Server
# Run this to update your server with the latest code

echo "📥 Copying Updated Code to Server"
echo "================================"
echo ""

# Copy all Python files
echo "📄 Copying Python files..."
scp *.py javiddelossantos@10.1.2.165:/home/javiddelossantos/fast-api-test/

# Copy Docker files
echo "🐳 Copying Docker files..."
scp Dockerfile.* javiddelossantos@10.1.2.165:/home/javiddelossantos/fast-api-test/
scp docker-compose*.yml javiddelossantos@10.1.2.165:/home/javiddelossantos/fast-api-test/

# Copy requirements
echo "📦 Copying requirements..."
scp requirements.txt javiddelossantos@10.1.2.165:/home/javiddelossantos/fast-api-test/

# Copy scripts
echo "🔧 Copying scripts..."
scp *.sh javiddelossantos@10.1.2.165:/home/javiddelossantos/fast-api-test/

# Copy static files
echo "📁 Copying static files..."
scp -r static javiddelossantos@10.1.2.165:/home/javiddelossantos/fast-api-test/

echo "✅ All files copied successfully!"
echo ""
echo "🚀 Next steps:"
echo "1. SSH to server: ssh javiddelossantos@10.1.2.165"
echo "2. Navigate to project: cd /home/javiddelossantos/fast-api-test"
echo "3. Remove Nginx (if needed): sudo ./remove_nginx.sh"
echo "4. Start Docker MySQL: docker-compose up -d db"
echo "5. Setup database: python3 setup_docker_database.py"
echo "6. Run Svelte integration: ./server_svelte_integration.sh"
echo ""
echo "🎯 This will give you:"
echo "  🗄️ Database with all tables and UUID columns"
echo "  🎨 Svelte frontend on port 3000"
echo "  🔧 FastAPI backend on port 8000"

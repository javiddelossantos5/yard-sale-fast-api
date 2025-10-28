#!/bin/bash

# Docker Compose Deployment Script
# Run this on your server (10.1.2.165)

set -e

echo "🐳 Docker Compose Deployment for Image Upload System"
echo "===================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Installing..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "✅ Docker installed. Please log out and back in, then run this script again."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Installing..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose installed."
fi

# Create project directory
PROJECT_DIR="/home/javiddelossantos/fast-api-test"
echo "📁 Creating project directory: $PROJECT_DIR"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Copy files (you'll need to do this manually or via SCP)
echo "📤 Please copy your project files to: $PROJECT_DIR"
echo "   You can use: scp -r /path/to/local/project/* javiddelossantos@10.1.2.165:$PROJECT_DIR/"

# Wait for user to copy files
read -p "Press Enter after copying files to continue..."

# Create static directory
mkdir -p static
cp image_upload_frontend.html static/index.html

# Create SSL directory (for future SSL certificates)
mkdir -p ssl

# Build and start services
echo "🔨 Building Docker images..."
docker-compose -f docker-compose.simple.yml build

echo "🚀 Starting services..."
docker-compose -f docker-compose.simple.yml up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "📊 Service Status:"
docker-compose -f docker-compose.simple.yml ps

# Test backend
echo "🧪 Testing backend..."
if curl -f http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ Backend is running on port 8000"
else
    echo "❌ Backend is not responding on port 8000"
fi

# Test frontend
echo "🧪 Testing frontend..."
if curl -f http://localhost/ > /dev/null 2>&1; then
    echo "✅ Frontend is running on port 80"
else
    echo "❌ Frontend is not responding on port 80"
fi

echo ""
echo "🎉 Deployment Complete!"
echo "======================="
echo "Your services are now running:"
echo "  🌐 Frontend: http://10.1.2.165/"
echo "  🔧 Backend: http://10.1.2.165:8000/"
echo "  📚 API Docs: http://10.1.2.165:8000/docs"
echo "  🗄️  Database: localhost:3306"
echo ""
echo "To configure Nginx Proxy Manager:"
echo "  📍 Domain: garage.javidscript.com"
echo "  🔗 Forward to: 10.1.2.165:80 (or 10.1.2.165:8000 for direct backend)"
echo ""
echo "Useful commands:"
echo "  📊 Check status: docker-compose -f docker-compose.simple.yml ps"
echo "  📝 View logs: docker-compose -f docker-compose.simple.yml logs -f"
echo "  🔄 Restart: docker-compose -f docker-compose.simple.yml restart"
echo "  🛑 Stop: docker-compose -f docker-compose.simple.yml down"
echo "  🗑️  Clean up: docker-compose -f docker-compose.simple.yml down -v"

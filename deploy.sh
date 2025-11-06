#!/bin/bash
# Deployment script for yard-sale-backend
# Run this script on your server to pull latest code and restart the container

set -e  # Exit on any error

echo "🚀 Starting deployment..."
echo ""

# Configuration
CONTAINER_NAME="yard-sale-backend"
IMAGE_NAME="yard-sale-backend:latest"
DOCKERFILE="Dockerfile.backend"
PORT="8000:8000"
DATABASE_URL="mysql+mysqlconnector://root:supersecretpassword@10.1.2.165:3306/yardsale"
NETWORK="bridge"

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📂 Working directory: $(pwd)"
echo ""

# Step 1: Pull latest changes from GitHub
echo "📥 Pulling latest changes from GitHub..."
if git pull origin main; then
    echo "✅ Successfully pulled latest changes"
else
    echo "❌ Failed to pull from GitHub"
    exit 1
fi
echo ""

# Step 2: Stop and remove old container
echo "🛑 Stopping and removing old container..."
docker stop "$CONTAINER_NAME" 2>/dev/null || echo "   Container not running"
docker rm "$CONTAINER_NAME" 2>/dev/null || echo "   Container doesn't exist"
echo "✅ Old container removed"
echo ""

# Step 3: Build new Docker image
echo "🔨 Building new Docker image..."
if docker build --no-cache -f "$DOCKERFILE" -t "$IMAGE_NAME" .; then
    echo "✅ Docker image built successfully"
else
    echo "❌ Docker build failed"
    exit 1
fi
echo ""

# Step 4: Run new container
echo "🚀 Starting new container..."
if docker run -d \
  --name "$CONTAINER_NAME" \
  --restart always \
  -p "$PORT" \
  -e DATABASE_URL="$DATABASE_URL" \
  --network "$NETWORK" \
  "$IMAGE_NAME"; then
    echo "✅ Container started successfully"
else
    echo "❌ Failed to start container"
    exit 1
fi
echo ""

# Step 5: Show container status
echo "📊 Container status:"
docker ps | grep "$CONTAINER_NAME" || echo "   Container not found in running containers"
echo ""

# Step 6: Show recent logs
echo "📋 Recent container logs (last 20 lines):"
docker logs --tail 20 "$CONTAINER_NAME" 2>&1 || echo "   Could not retrieve logs"
echo ""

echo "✅ Deployment completed successfully!"
echo ""
echo "💡 Useful commands:"
echo "   View logs:    docker logs -f $CONTAINER_NAME"
echo "   Stop:         docker stop $CONTAINER_NAME"
echo "   Restart:      docker restart $CONTAINER_NAME"
echo "   Check status: docker ps | grep $CONTAINER_NAME"


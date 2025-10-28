#!/bin/bash

# Server-side Svelte Integration Script
# Run this directly on your server (10.1.2.165)

set -e

echo "🎨 Server-side Svelte Integration"
echo "================================="

# Check if we're on the server
if [ ! -d "/home/javiddelossantos" ]; then
    echo "❌ This script should be run on the server (10.1.2.165)"
    echo "Please SSH to the server first: ssh javiddelossantos@10.1.2.165"
    exit 1
fi

# Server paths
SVELTE_DIR="/home/javiddelossantos/yard-sale-svelte"
DOCKER_DIR="/home/javiddelossantos/fast-api-test"

echo "📁 Current directory: $(pwd)"
echo "📁 Svelte directory: $SVELTE_DIR"
echo "📁 Docker directory: $DOCKER_DIR"

# Check if Svelte frontend exists
if [ ! -d "$SVELTE_DIR" ]; then
    echo "❌ Svelte frontend not found at: $SVELTE_DIR"
    echo "Please copy your Svelte frontend to the server first."
    echo ""
    echo "From your local machine, run:"
    echo "scp -r /Users/javiddelossantos/Documents/Github/Strata/svelte-yard-sale/* javiddelossantos@10.1.2.165:/home/javiddelossantos/yard-sale-svelte/"
    exit 1
fi

echo "✅ Found Svelte frontend at: $SVELTE_DIR"

# Check if build directory exists
if [ ! -d "$SVELTE_DIR/build" ]; then
    echo "❌ Build directory not found at: $SVELTE_DIR/build"
    echo "Please build your Svelte app locally first."
    echo ""
    echo "From your local machine, run:"
    echo "cd /Users/javiddelossantos/Documents/Github/Strata/svelte-yard-sale"
    echo "npm run build"
    exit 1
fi

echo "✅ Found pre-built Svelte app at: $SVELTE_DIR/build"

# Check if Docker project exists
if [ ! -d "$DOCKER_DIR" ]; then
    echo "❌ Docker project not found at: $DOCKER_DIR"
    echo "Please copy your Docker project to the server first."
    exit 1
fi

echo "✅ Found Docker project at: $DOCKER_DIR"

# Navigate to Docker project
cd $DOCKER_DIR

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down 2>/dev/null || echo "No containers to stop"

# Create frontend directory
echo "📁 Creating frontend directory..."
mkdir -p frontend

# Copy Svelte frontend
echo "📤 Copying Svelte frontend..."
cp -r $SVELTE_DIR/* frontend/

echo "✅ Svelte frontend copied successfully!"

# Create new Dockerfile for Svelte frontend (pre-built approach)
echo "🐳 Creating Dockerfile for pre-built Svelte frontend..."
cat > Dockerfile.svelte << 'EOF'
FROM nginx:alpine

# Copy pre-built files
COPY frontend/build /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx-svelte.conf /etc/nginx/nginx.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
EOF

# Create nginx configuration for Svelte
echo "⚙️ Creating Nginx configuration for Svelte..."
cat > nginx-svelte.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # Logging
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Basic settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Upstream backend
    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;
        server_name garage.javidscript.com;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";

        # Serve Svelte frontend
        location / {
            root /usr/share/nginx/html;
            index index.html;
            try_files $uri $uri/ /index.html;
        }

        # API endpoints - proxy to FastAPI backend
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Upload endpoints
        location /upload/ {
            client_max_body_size 10M;
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Image proxy endpoints
        location /image-proxy/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Other API endpoints
        location ~ ^/(yard-sales|user|users|images|docs|redoc) {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            root /usr/share/nginx/html;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
EOF

# Update docker-compose.yml to use Svelte frontend
echo "🔧 Updating docker-compose.yml for Svelte frontend..."
cat > docker-compose.yml << 'EOF'
services:
  # FastAPI Backend
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: fastapi-backend
    ports:
      - 8000:8000
    environment:
      - DATABASE_URL=mysql+mysqlconnector://root:password@db:3306/fastapi_db
      - GARAGE_ENDPOINT_URL=http://10.1.2.165:3900
      - GARAGE_ACCESS_KEY_ID=GKdfa877679e4f9f1c89612285
      - GARAGE_SECRET_ACCESS_KEY=514fc1f21b01269ec46d9157a5e2eeabcb03a4b9733cfa1e5945dfc388f8a980
      - GARAGE_BUCKET_NAME=nextcloud-bucket
      - DOMAIN_NAME=https://garage.javidscript.com
    depends_on:
      - db
    volumes:
      - ./static:/app/static
    restart: unless-stopped
    networks:
      - app-network

  # Svelte Frontend (Nginx)
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.svelte
    container_name: svelte-frontend
    ports:
      - 80:80
      - 443:443
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - app-network

  # MySQL Database
  db:
    image: mysql:8.0
    container_name: mysql-db
    environment:
      - MYSQL_ROOT_PASSWORD=password
      - MYSQL_DATABASE=fastapi_db
      - MYSQL_USER=fastapi_user
      - MYSQL_PASSWORD=fastapi_password
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - 3306:3306
    restart: unless-stopped
    networks:
      - app-network

volumes:
  mysql_data:

networks:
  app-network:
    driver: bridge
EOF

echo "✅ Docker configuration updated for Svelte frontend!"

# Build and start services
echo "🔨 Building Docker images..."
docker-compose build

echo "🚀 Starting services with Svelte frontend..."
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 15

# Check service status
echo "📊 Service Status:"
docker-compose ps

# Test frontend
echo "🧪 Testing Svelte frontend..."
if curl -f http://localhost/ > /dev/null 2>&1; then
    echo "✅ Svelte frontend is running on port 80"
else
    echo "❌ Svelte frontend is not responding on port 80"
    echo "📝 Frontend logs:"
    docker-compose logs frontend
fi

# Test backend
echo "🧪 Testing backend..."
if curl -f http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ Backend is running on port 8000"
else
    echo "❌ Backend is not responding on port 8000"
    echo "📝 Backend logs:"
    docker-compose logs backend
fi

echo ""
echo "🎉 Svelte Frontend Integration Complete!"
echo "=========================================="
echo "Your services are now running:"
echo "  🎨 Svelte Frontend: http://10.1.2.165/"
echo "  🔧 FastAPI Backend: http://10.1.2.165:8000/"
echo "  📚 API Docs: http://10.1.2.165:8000/docs"
echo "  🗄️  Database: localhost:3306"
echo ""
echo "To configure Nginx Proxy Manager:"
echo "  📍 Domain: garage.javidscript.com"
echo "  🔗 Forward to: 10.1.2.165:80"
echo ""
echo "Useful commands:"
echo "  📊 Check status: docker-compose ps"
echo "  📝 View logs: docker-compose logs -f"
echo "  🔄 Restart: docker-compose restart"
echo "  🛑 Stop: docker-compose down"

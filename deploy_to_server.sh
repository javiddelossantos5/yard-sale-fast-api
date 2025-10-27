#!/bin/bash

# Image Upload Setup Script for Ubuntu Server
# This script helps deploy the FastAPI backend and frontend to your Ubuntu server

echo "🚀 Setting up Image Upload System on Ubuntu Server"
echo "=================================================="

# Configuration
SERVER_IP="10.1.2.165"
SERVER_USER="javiddelossantos"
SERVER_PASSWORD="Spiderm@n1995"
LOCAL_PROJECT_PATH="/Users/javiddelossantos/Documents/Github/Strata/fast-api-test"
REMOTE_PROJECT_PATH="/home/javiddelossantos/fast-api-test"

echo "📋 Configuration:"
echo "  Server IP: $SERVER_IP"
echo "  Server User: $SERVER_USER"
echo "  Local Path: $LOCAL_PROJECT_PATH"
echo "  Remote Path: $REMOTE_PROJECT_PATH"
echo ""

# Function to run commands on remote server
run_remote() {
    sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" "$1"
}

# Function to copy files to remote server
copy_to_remote() {
    sshpass -p "$SERVER_PASSWORD" scp -o StrictHostKeyChecking=no -r "$1" "$SERVER_USER@$SERVER_IP:$2"
}

echo "🔧 Step 1: Installing required packages on server..."
run_remote "sudo apt update && sudo apt install -y python3 python3-pip python3-venv nginx"

echo "📁 Step 2: Creating project directory on server..."
run_remote "mkdir -p $REMOTE_PROJECT_PATH"

echo "📤 Step 3: Copying project files to server..."
copy_to_remote "$LOCAL_PROJECT_PATH/main.py" "$REMOTE_PROJECT_PATH/"
copy_to_remote "$LOCAL_PROJECT_PATH/database.py" "$REMOTE_PROJECT_PATH/"
copy_to_remote "$LOCAL_PROJECT_PATH/image_upload_frontend.html" "$REMOTE_PROJECT_PATH/"

echo "🐍 Step 4: Setting up Python virtual environment on server..."
run_remote "cd $REMOTE_PROJECT_PATH && python3 -m venv venv"

echo "📦 Step 5: Installing Python dependencies on server..."
run_remote "cd $REMOTE_PROJECT_PATH && source venv/bin/activate && pip install fastapi uvicorn sqlalchemy mysql-connector-python python-jose passlib bcrypt python-multipart boto3 pytz"

echo "🌐 Step 6: Setting up Nginx configuration..."
run_remote "sudo tee /etc/nginx/sites-available/fastapi-image-upload > /dev/null << 'EOF'
server {
    listen 80;
    server_name $SERVER_IP;

    # Serve the HTML frontend
    location / {
        root $REMOTE_PROJECT_PATH;
        index image_upload_frontend.html;
        try_files \$uri \$uri/ =404;
    }

    # Proxy API requests to FastAPI
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Proxy upload and image endpoints
    location /upload/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /images {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Proxy image proxy endpoint (serves images with authentication)
    location /image-proxy/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Proxy other API endpoints
    location /yard-sales {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /user {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /users {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF"

echo "🔗 Step 7: Enabling Nginx site..."
run_remote "sudo ln -sf /etc/nginx/sites-available/fastapi-image-upload /etc/nginx/sites-enabled/"
run_remote "sudo nginx -t && sudo systemctl reload nginx"

echo "🚀 Step 8: Creating systemd service for FastAPI..."
run_remote "sudo tee /etc/systemd/system/fastapi-image-upload.service > /dev/null << 'EOF'
[Unit]
Description=FastAPI Image Upload Service
After=network.target

[Service]
Type=exec
User=$SERVER_USER
WorkingDirectory=$REMOTE_PROJECT_PATH
Environment=PATH=$REMOTE_PROJECT_PATH/venv/bin
ExecStart=$REMOTE_PROJECT_PATH/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF"

echo "🔄 Step 9: Starting FastAPI service..."
run_remote "sudo systemctl daemon-reload"
run_remote "sudo systemctl enable fastapi-image-upload"
run_remote "sudo systemctl start fastapi-image-upload"

echo "✅ Step 10: Checking service status..."
run_remote "sudo systemctl status fastapi-image-upload --no-pager"

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo "Your image upload system is now running on:"
echo "  Frontend: http://$SERVER_IP/"
echo "  API Docs: http://$SERVER_IP:8000/docs"
echo ""
echo "To check logs:"
echo "  sudo journalctl -u fastapi-image-upload -f"
echo ""
echo "To restart service:"
echo "  sudo systemctl restart fastapi-image-upload"
echo ""
echo "To update code:"
echo "  1. Copy new files to server"
echo "  2. sudo systemctl restart fastapi-image-upload"

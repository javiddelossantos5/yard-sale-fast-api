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

echo "🌐 Step 6: Skipping Nginx setup (using Nginx Proxy Manager)..."
echo "✅ Nginx Proxy Manager is handling SSL and proxying to garage.javidscript.com"
echo "✅ Your domain: https://garage.javidscript.com"
echo "✅ Backend will run on port 8000 for Nginx Proxy Manager to proxy"

echo "🌐 Step 7: Adding frontend serving to FastAPI..."
run_remote "cd $REMOTE_PROJECT_PATH && mkdir -p static"
run_remote "cd $REMOTE_PROJECT_PATH && cp image_upload_frontend.html static/index.html"

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
echo "  🌐 Frontend: https://garage.javidscript.com/"
echo "  📚 API Docs: https://garage.javidscript.com/docs"
echo "  🔧 Backend: https://garage.javidscript.com/api/"
echo ""
echo "Nginx Proxy Manager Configuration:"
echo "  📍 Domain: garage.javidscript.com"
echo "  🔗 Forward to: 10.1.2.165:8000"
echo "  🔒 SSL: Enabled (Let's Encrypt)"
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

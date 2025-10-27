# 🖼️ Image Upload System with Garage S3

A complete image upload system using FastAPI backend and Garage S3-compatible storage, with a modern HTML frontend.

## 🏗️ Architecture

- **Backend**: FastAPI with JWT authentication
- **Storage**: Garage S3-compatible storage (self-hosted)
- **Frontend**: HTML/JavaScript with drag-and-drop upload
- **Server**: Ubuntu with Nginx reverse proxy

## 🚀 Quick Start

### 1. Test Local Setup

```bash
# Test Garage S3 connection
python test_garage_connection.py

# Start FastAPI server
python main.py

# Open frontend
open image_upload_frontend.html
```

### 2. Deploy to Ubuntu Server

```bash
# Make deployment script executable
chmod +x deploy_to_server.sh

# Deploy to your server
./deploy_to_server.sh
```

### 3. Access Your System

- **Frontend**: http://10.1.2.165/
- **API Docs**: http://10.1.2.165:8000/docs
- **Direct API**: http://10.1.2.165:8000/

## 📋 Features

### Backend API Endpoints

- `POST /upload/image` - Upload image to Garage S3
- `GET /images` - List user's uploaded images
- `DELETE /images/{image_key}` - Delete specific image
- `POST /api/login` - User authentication
- `GET /api/me` - Get current user info

### Frontend Features

- 🔐 **User Authentication** - Login with username/password
- 📤 **Drag & Drop Upload** - Intuitive file upload interface
- 🖼️ **Image Gallery** - View all uploaded images
- 🗑️ **Image Management** - Delete images with confirmation
- 📱 **Responsive Design** - Works on desktop and mobile
- ⚡ **Real-time Feedback** - Upload progress and status messages

### Security Features

- JWT token authentication (3-hour expiration)
- User-specific image isolation
- File type validation (images only)
- File size limits (10MB max)
- Secure S3 credentials

## 🔧 Configuration

### Garage S3 Settings

```python
GARAGE_ENDPOINT_URL = "http://10.1.2.165:3900"
GARAGE_ACCESS_KEY_ID = "GKdfa877679e4f9f1c89612285"
GARAGE_SECRET_ACCESS_KEY = "514fc1f21b01269ec46d9157a5e2eeabcb03a4b9733cfa1e5945dfc388f8a980"
GARAGE_BUCKET_NAME = "nextcloud-bucket"
```

### Server Configuration

- **Server IP**: 10.1.2.165
- **SSH User**: javiddelossantos
- **SSH Password**: Spiderm@n1995
- **Nginx Port**: 80 (frontend)
- **FastAPI Port**: 8000 (backend)

## 📁 File Structure

```
fast-api-test/
├── main.py                          # FastAPI backend with image upload endpoints
├── database.py                      # Database models and configuration
├── image_upload_frontend.html      # HTML frontend for image uploads
├── deploy_to_server.sh             # Deployment script for Ubuntu server
├── test_garage_connection.py       # Test script for Garage S3 connection
└── README.md                       # This file
```

## 🧪 Testing

### Test Garage S3 Connection

```bash
python test_garage_connection.py
```

### Test API Endpoints

```bash
# Login
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "javiddelossantos", "password": "Password"}'

# Upload image (replace TOKEN with actual token)
curl -X POST http://localhost:8000/upload/image \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@test-image.jpg"

# List images
curl -X GET http://localhost:8000/images \
  -H "Authorization: Bearer TOKEN"
```

## 🔄 Deployment Process

The `deploy_to_server.sh` script automates:

1. **Server Setup**: Install Python, pip, venv, nginx
2. **Code Deployment**: Copy project files to server
3. **Dependencies**: Install Python packages
4. **Nginx Configuration**: Set up reverse proxy
5. **Service Setup**: Create systemd service for FastAPI
6. **Service Start**: Enable and start the service

## 🛠️ Troubleshooting

### Common Issues

1. **Garage Connection Failed**

   - Check if Garage is running on http://10.1.2.165:3900
   - Verify bucket 'nextcloud-bucket' exists
   - Confirm credentials are correct

2. **FastAPI Service Not Starting**

   ```bash
   sudo journalctl -u fastapi-image-upload -f
   ```

3. **Nginx Configuration Issues**

   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

4. **Permission Issues**
   ```bash
   sudo chown -R javiddelossantos:javiddelossantos /home/javiddelossantos/fast-api-test
   ```

### Service Management

```bash
# Check service status
sudo systemctl status fastapi-image-upload

# Restart service
sudo systemctl restart fastapi-image-upload

# View logs
sudo journalctl -u fastapi-image-upload -f

# Stop service
sudo systemctl stop fastapi-image-upload
```

## 📊 Usage Examples

### Upload Image via API

```python
import requests

# Login
response = requests.post("http://10.1.2.165/api/login",
                        json={"username": "javiddelossantos", "password": "Password"})
token = response.json()["access_token"]

# Upload image
with open("image.jpg", "rb") as f:
    files = {"file": f}
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post("http://10.1.2.165/upload/image",
                           files=files, headers=headers)
    print(response.json())
```

### List Images via API

```python
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://10.1.2.165/images", headers=headers)
images = response.json()["images"]
for image in images:
    print(f"Image: {image['filename']} - URL: {image['url']}")
```

## 🎯 Next Steps

1. **Deploy to Server**: Run `./deploy_to_server.sh`
2. **Test Upload**: Access http://10.1.2.165/ and upload images
3. **Monitor Logs**: Check service logs for any issues
4. **Scale Up**: Add more features like image resizing, thumbnails, etc.

## 🔒 Security Notes

- Change default passwords in production
- Use HTTPS in production
- Implement rate limiting
- Add image virus scanning
- Use environment variables for sensitive data
- Regular security updates

---

**🎉 Your image upload system is ready to use!**

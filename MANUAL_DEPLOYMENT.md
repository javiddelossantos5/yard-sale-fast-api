# 🚀 **Manual Production Deployment Guide**

## **Step 1: Copy Files to Server**

```bash
# Copy all files to your server
scp -r /Users/javiddelossantos/Documents/Github/Strata/fast-api-test/* javiddelossantos@10.1.2.165:/home/javiddelossantos/fast-api-test/
```

## **Step 2: SSH to Server and Setup**

```bash
ssh javiddelossantos@10.1.2.165
cd /home/javiddelossantos/fast-api-test

# Install Python dependencies
sudo apt update
sudo apt install python3-venv python3-pip -y

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install fastapi uvicorn sqlalchemy mysql-connector-python python-jose passlib bcrypt python-multipart boto3 pytz

# Create static directory and copy frontend
mkdir -p static
cp image_upload_frontend.html static/index.html
```

## **Step 3: Create Systemd Service**

```bash
sudo tee /etc/systemd/system/fastapi-image-upload.service > /dev/null << 'EOF'
[Unit]
Description=FastAPI Image Upload Service
After=network.target

[Service]
Type=simple
User=javiddelossantos
WorkingDirectory=/home/javiddelossantos/fast-api-test
Environment=PATH=/home/javiddelossantos/fast-api-test/venv/bin
ExecStart=/home/javiddelossantos/fast-api-test/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable fastapi-image-upload
sudo systemctl start fastapi-image-upload
```

## **Step 4: Check Service Status**

```bash
sudo systemctl status fastapi-image-upload
```

## **Step 5: Test Backend**

```bash
# Test if backend is running
curl http://localhost:8000/

# Test API docs
curl http://localhost:8000/docs
```

## **Step 6: Configure Nginx Proxy Manager**

### **Proxy Host Settings:**

- **Domain Names**: `garage.javidscript.com`
- **Scheme**: `http`
- **Forward Hostname/IP**: `10.1.2.165`
- **Forward Port**: `8000`
- **Cache Assets**: ✅ Enabled
- **Block Common Exploits**: ✅ Enabled
- **Websockets Support**: ✅ Enabled

### **SSL Settings:**

- **SSL Certificate**: Let's Encrypt
- **Force SSL**: ✅ Enabled

## **Step 7: Test Production**

### **Test Frontend:**

```bash
curl -I https://garage.javidscript.com/
# Should return: HTTP/1.1 200 OK
```

### **Test API:**

```bash
curl -I https://garage.javidscript.com/docs
# Should return: HTTP/1.1 200 OK
```

### **Test Login:**

```bash
curl -X POST "https://garage.javidscript.com/api/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "javiddelossantos", "password": "Password"}'
```

## **Troubleshooting**

### **If Backend Not Running:**

```bash
sudo systemctl restart fastapi-image-upload
sudo journalctl -u fastapi-image-upload -f
```

### **If Nginx Proxy Issues:**

- Check Proxy Manager logs
- Verify domain DNS points to your server
- Ensure SSL certificate is valid

### **If Database Issues:**

```bash
# Check database connection
python3 -c "
from database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Database connection OK')
"
```

## **Success Indicators**

✅ **Frontend loads**: `https://garage.javidscript.com/` shows upload interface  
✅ **API docs work**: `https://garage.javidscript.com/docs` shows Swagger UI  
✅ **Login works**: Can authenticate and get JWT token  
✅ **Upload works**: Can upload images successfully  
✅ **Images display**: Can view uploaded images in gallery  
✅ **SSL works**: Green lock icon in browser

## **Quick Commands**

```bash
# Restart service
sudo systemctl restart fastapi-image-upload

# Check logs
sudo journalctl -u fastapi-image-upload -f

# Check status
sudo systemctl status fastapi-image-upload

# Test locally on server
curl http://localhost:8000/
```

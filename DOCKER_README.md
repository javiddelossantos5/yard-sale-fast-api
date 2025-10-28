# 🐳 Docker Compose Setup for Image Upload System

## 📋 **What's Included:**

- **FastAPI Backend**: Handles API, authentication, and image proxying
- **Nginx Frontend**: Serves static files and handles SSL
- **MySQL Database**: Stores user data and application state
- **Garage S3**: External S3-compatible storage (your existing setup)

## 🚀 **Quick Start:**

### **1. Copy Files to Server:**

```bash
scp -r /Users/javiddelossantos/Documents/Github/Strata/fast-api-test/* javiddelossantos@10.1.2.165:/home/javiddelossantos/fast-api-test/
```

### **2. SSH to Server and Deploy:**

```bash
ssh javiddelossantos@10.1.2.165
cd /home/javiddelossantos/fast-api-test
chmod +x deploy_docker.sh
./deploy_docker.sh
```

## 📁 **File Structure:**

```
fast-api-test/
├── docker-compose.simple.yml    # Main compose file
├── Dockerfile.backend           # FastAPI backend
├── Dockerfile.frontend         # Nginx frontend
├── nginx.conf                  # Nginx configuration
├── requirements.txt            # Python dependencies
├── deploy_docker.sh            # Deployment script
├── main.py                     # FastAPI application
├── database.py                 # Database models
└── static/
    └── index.html              # Frontend
```

## 🔧 **Configuration:**

### **Environment Variables:**

- `DATABASE_URL`: MySQL connection string
- `GARAGE_ENDPOINT_URL`: Your Garage S3 endpoint
- `GARAGE_ACCESS_KEY_ID`: Your Garage access key
- `GARAGE_SECRET_ACCESS_KEY`: Your Garage secret key
- `GARAGE_BUCKET_NAME`: Your Garage bucket name
- `DOMAIN_NAME`: Your domain (https://garage.javidscript.com)

### **Ports:**

- `80`: Nginx frontend (HTTP)
- `443`: Nginx frontend (HTTPS)
- `8000`: FastAPI backend
- `3306`: MySQL database

## 🌐 **Nginx Proxy Manager Setup:**

Configure your Nginx Proxy Manager with:

- **Domain**: `garage.javidscript.com`
- **Scheme**: `http`
- **Forward to**: `10.1.2.165:80` (or `10.1.2.165:8000` for direct backend)
- **SSL**: Enable Let's Encrypt

## 📊 **Management Commands:**

### **Check Status:**

```bash
docker-compose -f docker-compose.simple.yml ps
```

### **View Logs:**

```bash
# All services
docker-compose -f docker-compose.simple.yml logs -f

# Specific service
docker-compose -f docker-compose.simple.yml logs -f backend
```

### **Restart Services:**

```bash
# All services
docker-compose -f docker-compose.simple.yml restart

# Specific service
docker-compose -f docker-compose.simple.yml restart backend
```

### **Stop Services:**

```bash
docker-compose -f docker-compose.simple.yml down
```

### **Clean Up (Remove Volumes):**

```bash
docker-compose -f docker-compose.simple.yml down -v
```

## 🔍 **Troubleshooting:**

### **Backend Not Starting:**

```bash
docker-compose -f docker-compose.simple.yml logs backend
```

### **Database Connection Issues:**

```bash
docker-compose -f docker-compose.simple.yml logs db
```

### **Nginx Issues:**

```bash
docker-compose -f docker-compose.simple.yml logs frontend
```

### **Check Service Health:**

```bash
# Test backend
curl http://localhost:8000/

# Test frontend
curl http://localhost/

# Test API docs
curl http://localhost:8000/docs
```

## 🎯 **Expected Results:**

Once deployed, you should have:

- ✅ `https://garage.javidscript.com/` → Frontend loads
- ✅ `https://garage.javidscript.com/docs` → API documentation
- ✅ `https://garage.javidscript.com/api/login` → Authentication
- ✅ `https://garage.javidscript.com/upload/image` → Image upload
- ✅ `https://garage.javidscript.com/image-proxy/...` → Image viewing

## 🔄 **Updates:**

To update your application:

1. Copy new files to server
2. Rebuild containers: `docker-compose -f docker-compose.simple.yml build`
3. Restart services: `docker-compose -f docker-compose.simple.yml restart`

## 💾 **Data Persistence:**

- **MySQL Data**: Stored in Docker volume `mysql_data`
- **Uploaded Images**: Stored in your Garage S3 bucket
- **Application Code**: Mounted from host filesystem

## 🛡️ **Security Notes:**

- Database credentials are in environment variables
- Garage S3 credentials are in environment variables
- Nginx includes security headers
- Rate limiting is configured for API endpoints
- SSL termination handled by Nginx Proxy Manager

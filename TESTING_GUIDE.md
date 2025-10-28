# 🧪 **Testing Your Image Upload System**

## **Quick Manual Tests**

### **1. Test Frontend Access**

```bash
# Open in browser or test with curl
curl -I https://garage.javidscript.com/
# Should return: HTTP/1.1 200 OK
```

### **2. Test API Documentation**

```bash
# Open in browser or test with curl
curl -I https://garage.javidscript.com/docs
# Should return: HTTP/1.1 200 OK
```

### **3. Test Login**

```bash
curl -X POST "https://garage.javidscript.com/api/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "javiddelossantos", "password": "Password"}'

# Should return:
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "token_type": "bearer",
#   "expires_in": 10800
# }
```

### **4. Test Authenticated Endpoints**

```bash
# Get your token from step 3, then:
TOKEN="your_token_here"

# Test user profile
curl -H "Authorization: Bearer $TOKEN" \
  https://garage.javidscript.com/api/me

# Test image list
curl -H "Authorization: Bearer $TOKEN" \
  https://garage.javidscript.com/images

# Test yard sales
curl -H "Authorization: Bearer $TOKEN" \
  https://garage.javidscript.com/yard-sales
```

### **5. Test Image Upload**

```bash
# Create a test image
echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==" | base64 -d > test.png

# Upload it
curl -X POST "https://garage.javidscript.com/upload/image" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.png"

# Should return:
# {
#   "success": true,
#   "message": "Image uploaded successfully",
#   "image_url": "/image-proxy/images/...",
#   "file_name": "...",
#   "file_size": ...
# }
```

### **6. Test Image Viewing**

```bash
# Get the image_url from step 5, then:
curl -H "Authorization: Bearer $TOKEN" \
  "https://garage.javidscript.com/image-proxy/images/your_image_path"

# Should return the image data
```

## **Browser Tests**

### **Frontend Test**

1. Open `https://garage.javidscript.com/`
2. Should see the image upload interface
3. Try logging in with your credentials
4. Try uploading an image
5. Check if images appear in the gallery

### **API Documentation Test**

1. Open `https://garage.javidscript.com/docs`
2. Should see Swagger UI
3. Try the login endpoint
4. Try other endpoints with authentication

## **Common Issues & Solutions**

### **❌ 502 Bad Gateway**

- **Cause**: FastAPI service not running
- **Solution**:
  ```bash
  ssh javiddelossantos@10.1.2.165
  sudo systemctl status fastapi-image-upload
  sudo systemctl restart fastapi-image-upload
  ```

### **❌ 404 Not Found**

- **Cause**: Nginx Proxy Manager not configured correctly
- **Solution**: Check Proxy Manager settings:
  - Domain: `garage.javidscript.com`
  - Forward to: `10.1.2.165:8000`

### **❌ SSL Certificate Error**

- **Cause**: Let's Encrypt certificate not issued
- **Solution**: Check Proxy Manager SSL settings

### **❌ Login Fails**

- **Cause**: Database connection issue
- **Solution**: Check database connection and user exists

### **❌ Image Upload Fails**

- **Cause**: Garage S3 connection issue
- **Solution**: Check Garage service and credentials

## **Automated Test Script**

Run the comprehensive test script:

```bash
./test_deployment.sh
```

This will test both local and remote deployment automatically.

## **Success Indicators**

✅ **Frontend loads**: `https://garage.javidscript.com/` shows upload interface  
✅ **API docs work**: `https://garage.javidscript.com/docs` shows Swagger UI  
✅ **Login works**: Can authenticate and get JWT token  
✅ **Upload works**: Can upload images successfully  
✅ **Images display**: Can view uploaded images in gallery  
✅ **SSL works**: Green lock icon in browser

If all these work, your deployment is successful! 🎉

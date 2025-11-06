# HTTPS Setup Guide for Backend API

## Problem

Your frontend at `https://yardsalefinders.com` (HTTPS) cannot access your backend at `http://10.1.2.165:8000` (HTTP) due to:

1. **Mixed Content Policy**: Browsers block HTTPS pages from loading HTTP resources
2. **Private IP Access**: Browsers block requests to private IPs (10.x.x.x) from public HTTPS sites

## Solution: Use HTTPS for Backend

You need to expose your backend over HTTPS. Here are two options:

---

## Option 1: Subdomain with SSL (Recommended)

Use a subdomain like `api.yardsalefinders.com` with SSL certificate.

### Steps:

1. **Set up DNS**:
   - Add A record: `api.yardsalefinders.com` → `10.1.2.165` (or your public IP)

2. **Set up SSL Certificate** (using Let's Encrypt/Certbot):
   ```bash
   # Install certbot
   sudo apt-get update
   sudo apt-get install certbot

   # Get certificate for api subdomain
   sudo certbot certonly --standalone -d api.yardsalefinders.com
   ```

3. **Set up Nginx Reverse Proxy**:
   Create `/etc/nginx/sites-available/api.yardsalefinders.com`:
   ```nginx
   server {
       listen 443 ssl http2;
       server_name api.yardsalefinders.com;

       ssl_certificate /etc/letsencrypt/live/api.yardsalefinders.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/api.yardsalefinders.com/privkey.pem;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }

   server {
       listen 80;
       server_name api.yardsalefinders.com;
       return 301 https://$server_name$request_uri;
   }
   ```

4. **Enable and restart Nginx**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/api.yardsalefinders.com /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

5. **Update Frontend**:
   Change API base URL to: `https://api.yardsalefinders.com`

---

## Option 2: Nginx Reverse Proxy on Same Domain

If you want to use `/api` path on the same domain.

### Steps:

1. **Update your main Nginx config** (`/etc/nginx/sites-available/yardsalefinders.com`):
   ```nginx
   server {
       listen 443 ssl http2;
       server_name yardsalefinders.com;

       # Your existing SSL config...

       # Frontend
       location / {
           # Your existing frontend config
           root /var/www/yardsalefinders;
           try_files $uri $uri/ /index.html;
       }

       # Backend API
       location /api {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           
           # CORS headers (if needed)
           add_header Access-Control-Allow-Origin https://yardsalefinders.com always;
           add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
           add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
           add_header Access-Control-Allow-Credentials true always;
           
           if ($request_method = OPTIONS) {
               return 204;
           }
       }
   }
   ```

2. **Update Frontend**:
   Use relative URLs: `/api/...` instead of `http://10.1.2.165:8000/...`

---

## Option 3: Quick Fix - Use Frontend Proxy (Development Only)

If you're using Vite for your Svelte frontend, you can proxy API requests:

### Vite Config (`vite.config.js`):

```javascript
import { defineConfig } from 'vite';
import { sveltekit } from '@sveltejs/kit/vite';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    proxy: {
      '/api': {
        target: 'http://10.1.2.165:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
```

Then use `/api/...` in your frontend code.

**Note**: This only works in development. For production, you need Option 1 or 2.

---

## Frontend Changes Required

### Update API Base URL

In your frontend code, change from:
```javascript
const API_BASE = 'http://10.1.2.165:8000'; // ❌ Won't work in production
```

To:
```javascript
// Option 1: Subdomain
const API_BASE = 'https://api.yardsalefinders.com';

// Option 2: Same domain
const API_BASE = ''; // Use relative URLs: /api/...

// Option 3: Environment variable
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'https://api.yardsalefinders.com';
```

### Environment Variables

Create `.env.production`:
```env
VITE_API_BASE_URL=https://api.yardsalefinders.com
```

Or for same-domain:
```env
VITE_API_BASE_URL=
```

---

## Testing

After setup, test:

```bash
# Test HTTPS endpoint
curl https://api.yardsalefinders.com/health

# Or if using same domain
curl https://yardsalefinders.com/api/health
```

---

## Recommended Solution

**For Production**: Use **Option 1** (subdomain with SSL)
- Clean separation
- Easy to manage
- Standard practice
- Works with CORS

**Quick Setup Script**:

```bash
#!/bin/bash
# setup-api-ssl.sh

DOMAIN="api.yardsalefinders.com"
BACKEND_PORT=8000

# Install certbot if not installed
sudo apt-get update
sudo apt-get install -y certbot nginx

# Get SSL certificate
sudo certbot certonly --standalone -d $DOMAIN --non-interactive --agree-tos --email your-email@example.com

# Create Nginx config
sudo tee /etc/nginx/sites-available/$DOMAIN > /dev/null <<EOF
server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$server_name\$request_uri;
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

echo "✅ SSL setup complete!"
echo "Backend now available at: https://$DOMAIN"
```

---

## Summary

**Root Cause**: HTTPS frontend cannot call HTTP backend (browser security)

**Solution**: Expose backend over HTTPS using:
1. Subdomain with SSL (best)
2. Nginx reverse proxy on same domain
3. Frontend proxy (dev only)

**Frontend Change**: Update API base URL to HTTPS endpoint


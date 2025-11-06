# Frontend API Configuration Fix

## The Problem

Your frontend at `https://yardsalefinders.com` is trying to call `http://10.1.2.165:8000`, which browsers block because:

1. **Mixed Content**: HTTPS pages cannot load HTTP resources
2. **Private IP**: Browsers block private IPs from public HTTPS sites

## Quick Diagnosis

**This is a BACKEND configuration issue**, but requires FRONTEND changes too.

---

## Immediate Frontend Fix

### Step 1: Update API Base URL

Find where your frontend sets the API base URL and change it.

**Current (Wrong):**

```javascript
const API_BASE = 'http://10.1.2.165:8000';
```

**Change to one of these:**

#### Option A: Use HTTPS Subdomain (Recommended)

```javascript
// If you set up api.yardsalefinders.com with SSL
const API_BASE = 'https://api.yardsalefinders.com';
```

#### Option B: Use Relative URLs (If using Nginx proxy)

```javascript
// If Nginx proxies /api to backend
const API_BASE = ''; // Empty = same domain
// Then use: /api/endpoint instead of http://10.1.2.165:8000/endpoint
```

#### Option C: Environment Variable

```javascript
// In your API config file
const API_BASE =
  import.meta.env.VITE_API_BASE_URL || 'https://api.yardsalefinders.com';
```

### Step 2: Update All API Calls

Make sure all API calls use the new base URL:

```javascript
// ✅ CORRECT
fetch(`${API_BASE}/admin/users`, {
  headers: { Authorization: `Bearer ${token}` },
});

// ❌ WRONG - Hardcoded HTTP IP
fetch('http://10.1.2.165:8000/admin/users', {
  headers: { Authorization: `Bearer ${token}` },
});
```

---

## Where to Make Changes

### If using SvelteKit:

1. **Create/Update `src/lib/api.ts` or `src/lib/api.js`:**

```typescript
// api.ts
const API_BASE =
  import.meta.env.VITE_API_BASE_URL || 'https://api.yardsalefinders.com';

export async function apiCall(endpoint: string, options: RequestInit = {}) {
  const token = localStorage.getItem('token');

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = endpoint.startsWith('http')
    ? endpoint
    : `${API_BASE}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}
```

2. **Create `.env.production`:**

```env
VITE_API_BASE_URL=https://api.yardsalefinders.com
```

3. **Update all API calls to use `apiCall()`:**

```javascript
// Before
const response = await fetch('http://10.1.2.165:8000/admin/users', {
  headers: { Authorization: `Bearer ${token}` },
});

// After
import { apiCall } from '$lib/api';
const data = await apiCall('/admin/users');
```

---

## Backend Setup Required

You MUST set up HTTPS for your backend. See `HTTPS_SETUP.md` for details.

**Quick option**: Set up `api.yardsalefinders.com` subdomain with SSL certificate.

---

## Testing

After making changes:

1. **Check browser console** - Should see requests to HTTPS URL
2. **Check Network tab** - Verify requests go to `https://api.yardsalefinders.com`
3. **Test upload** - Image upload should work without mixed content errors

---

## Common Issues

### Still seeing HTTP requests?

- Check all API calls use the new base URL
- Search codebase for `10.1.2.165:8000` and replace
- Clear browser cache

### CORS errors?

- Backend CORS already includes `https://yardsalefinders.com`
- Verify backend is accessible at HTTPS URL
- Check backend logs for CORS errors

### SSL certificate errors?

- Make sure SSL certificate is valid
- Check certificate expiration
- Verify DNS points to correct IP

---

## Summary

**Frontend Changes:**

1. Update API base URL to HTTPS
2. Use environment variables for different environments
3. Replace all hardcoded HTTP URLs

**Backend Changes:**

1. Set up HTTPS (subdomain or proxy)
2. SSL certificate required
3. Nginx reverse proxy recommended

**Result:** Frontend can call backend over HTTPS ✅

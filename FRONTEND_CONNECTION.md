# Frontend Connection Guide

## Backend API Configuration

Your FastAPI backend is running at:

- **URL**: `http://10.1.2.165:8000`
- **API Base**: `http://10.1.2.165:8000/api`
- **Docs**: `http://10.1.2.165:8000/docs`

## Svelte Frontend Configuration

### 1. Create API Configuration File

Create a file in your Svelte project: `/opt/stacks/svelte-yardsale/frontend/src/lib/api.js` (or similar)

```javascript
// API Configuration
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://10.1.2.165:8000';
export const API_URL = `${API_BASE_URL}/api`;

// Helper function to make API calls
export async function apiCall(endpoint, options = {}) {
  const token = localStorage.getItem('authToken');

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
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

// Auth functions
export async function login(username, password) {
  const response = await fetch(`${API_URL}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Login failed');
  }

  const data = await response.json();
  localStorage.setItem('authToken', data.access_token);
  return data;
}

export function logout() {
  localStorage.removeItem('authToken');
}

export function getAuthToken() {
  return localStorage.getItem('authToken');
}
```

### 2. Create Environment Variable File

Create `/opt/stacks/svelte-yardsale/frontend/.env`:

```env
VITE_API_BASE_URL=http://10.1.2.165:8000
```

Or for production:

```env
VITE_API_BASE_URL=http://10.1.2.165:8000
```

### 3. Update package.json (if needed)

Make sure your Svelte project has Vite configured properly. The dev server should run with:

```json
{
  "scripts": {
    "dev": "vite --host --port 5173"
  }
}
```

### 4. Example Usage in Svelte Component

```svelte
<script>
  import { login, apiCall, logout } from '$lib/api';
  import { onMount } from 'svelte';

  let user = null;
  let yardSales = [];

  async function handleLogin(username, password) {
    try {
      await login(username, password);
      await loadUserData();
    } catch (error) {
      console.error('Login failed:', error);
    }
  }

  async function loadUserData() {
    try {
      user = await apiCall('/me');
      yardSales = await apiCall('/yard-sales');
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  }

  onMount(() => {
    if (getAuthToken()) {
      loadUserData();
    }
  });
</script>
```

## Docker Compose for Svelte Dev

Your current docker-compose.yml looks good. Make sure it's configured like this:

```yaml
services:
  svelte-dev:
    image: node:20-alpine
    container_name: svelte-dev
    working_dir: /app
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - 5173:5173
    command: sh -c "npm install && npm run dev -- --host"
    environment:
      - VITE_API_BASE_URL=http://10.1.2.165:8000
```

## Testing the Connection

1. **Start your backend** (already running):

   ```bash
   # Backend should be running at http://10.1.2.165:8000
   ```

2. **Start your Svelte frontend**:

   ```bash
   cd /opt/stacks/svelte-yardsale
   docker-compose up -d
   ```

3. **Test the connection**:
   - Open browser: `http://10.1.2.165:5173`
   - Check browser console for CORS errors
   - Try to login/register from the frontend

## Common Issues

### CORS Errors

If you see CORS errors, make sure:

- Backend CORS includes your frontend URL
- Frontend is making requests to the correct backend URL
- Both services are running

### Connection Refused

- Check that backend is running: `curl http://10.1.2.165:8000/health`
- Check that frontend can reach the backend IP
- Verify firewall settings

### Authentication Issues

- Make sure tokens are stored in localStorage
- Check that Authorization header is being sent
- Verify token format: `Bearer <token>`

## API Endpoints Reference

- `POST /api/register` - Register new user
- `POST /api/login` - Login user
- `GET /api/me` - Get current user (requires auth)
- `GET /api/yard-sales` - Get yard sales list
- `POST /api/yard-sales` - Create yard sale (requires auth)
- `GET /api/market-items` - Get market items
- `POST /api/market-items` - Create market item (requires auth)

See full API docs at: `http://10.1.2.165:8000/docs`

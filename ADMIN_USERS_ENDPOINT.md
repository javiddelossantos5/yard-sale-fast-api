# Admin Users Endpoint - Troubleshooting Guide

## Endpoint Information

**URL:** `GET /admin/users`  
**Note:** The endpoint is `/admin/users` NOT `/api/admin/users`

**Base URL:** `http://10.1.2.165:8000` (or your server IP)

**Full URL:** `http://10.1.2.165:8000/admin/users`

---

## Authentication

**Required Header:**

```
Authorization: Bearer <your_admin_token>
```

**Required Permission:** User must have `permissions: "admin"`

---

## Response Format

The endpoint returns a paginated response:

```json
{
  "users": [
    {
      "id": "uuid-string",
      "username": "username",
      "email": "user@example.com",
      "full_name": "Full Name",
      "phone_number": "123-456-7890",
      "city": "Vernal",
      "state": "UT",
      "zip_code": "84078",
      "bio": "User bio text",
      "is_active": true,
      "permissions": "admin",
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ],
  "total": 150,
  "limit": 100,
  "offset": 0,
  "has_more": true
}
```

---

## Query Parameters

- `skip` (int, default: 0) - Number of users to skip (pagination)
- `limit` (int, default: 100) - Number of users per page
- `search` (string, optional) - Search by username, email, or full name

---

## Frontend Implementation

### Basic Usage

```javascript
async function getAdminUsers(token, skip = 0, limit = 100) {
  const response = await fetch(
    `http://10.1.2.165:8000/admin/users?skip=${skip}&limit=${limit}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch users');
  }

  const data = await response.json();
  return data; // { users: [...], total: 150, limit: 100, offset: 0, has_more: true }
}

// Usage
try {
  const data = await getAdminUsers(adminToken);
  console.log('Users:', data.users);
  console.log('Total:', data.total);
} catch (error) {
  console.error('Error:', error.message);
}
```

### With Search

```javascript
async function searchUsers(token, searchTerm) {
  const response = await fetch(
    `http://10.1.2.165:8000/admin/users?search=${encodeURIComponent(
      searchTerm
    )}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );
  return await response.json();
}
```

### Svelte Example

```javascript
// AdminUsers.svelte
<script>
  import { onMount } from 'svelte';

  let users = [];
  let loading = true;
  let error = null;
  let total = 0;
  let hasMore = false;

  const API_BASE = 'http://10.1.2.165:8000';
  const token = localStorage.getItem('token'); // or your token storage

  async function loadUsers(skip = 0, limit = 50) {
    try {
      loading = true;
      error = null;

      const response = await fetch(
        `${API_BASE}/admin/users?skip=${skip}&limit=${limit}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to load users');
      }

      const data = await response.json();
      users = data.users;
      total = data.total;
      hasMore = data.has_more;
    } catch (err) {
      error = err.message;
      console.error('Error loading users:', err);
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    loadUsers();
  });
</script>

{#if loading}
  <p>Loading users...</p>
{:else if error}
  <p class="error">Error: {error}</p>
{:else}
  <div>
    <p>Total users: {total}</p>
    <ul>
      {#each users as user}
        <li>
          <strong>{user.username}</strong> ({user.email})
          - {user.permissions}
          {#if !user.is_active}
            <span class="inactive">(Inactive)</span>
          {/if}
        </li>
      {/each}
    </ul>
  </div>
{/if}
```

---

## Common Errors and Solutions

### 1. "Access denied" or 403 Forbidden

**Cause:** User doesn't have admin permissions

**Solution:**

- Check user permissions: `user.permissions === "admin"`
- Verify token is for an admin user
- Check token hasn't expired

**Check user permissions:**

```javascript
// After login, check permissions
const user = await getCurrentUser();
if (user.permissions !== 'admin') {
  console.error('User is not an admin');
}
```

### 2. 401 Unauthorized

**Cause:** Invalid or missing token

**Solution:**

- Verify token is included in Authorization header
- Check token format: `Bearer <token>` (with space)
- Verify token hasn't expired
- Re-login to get a new token

**Debug:**

```javascript
console.log('Token:', token);
console.log('Header:', `Bearer ${token}`);
```

### 3. 404 Not Found

**Cause:** Wrong endpoint URL

**Solution:**

- Use `/admin/users` NOT `/api/admin/users`
- Check base URL is correct: `http://10.1.2.165:8000`
- Verify backend is running

**Test endpoint:**

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://10.1.2.165:8000/admin/users
```

### 4. CORS Error

**Cause:** Frontend origin not allowed in backend CORS

**Solution:**

- Check backend CORS configuration includes your frontend URL
- Verify `allow_credentials: true` is set
- Check browser console for CORS error details

### 5. Response Format Mismatch

**Cause:** Expecting array but getting object with `users` property

**Solution:**

- Access `data.users` not `data` directly
- Response format: `{ users: [...], total: 150, ... }`

**Correct usage:**

```javascript
const data = await response.json();
const users = data.users; // ✅ Correct
// const users = data; // ❌ Wrong - data is an object, not array
```

### 6. Network Error / Failed to Fetch

**Cause:** Backend not running or wrong URL

**Solution:**

- Verify backend is running: `docker ps | grep yard-sale-backend`
- Check backend logs: `docker logs yard-sale-backend`
- Test with curl to verify endpoint works
- Check network connectivity

---

## Testing the Endpoint

### Using curl

```bash
# Get all users
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://10.1.2.165:8000/admin/users

# With pagination
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://10.1.2.165:8000/admin/users?skip=0&limit=10"

# With search
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://10.1.2.165:8000/admin/users?search=john"
```

### Using Browser Console

```javascript
// In browser console (on your frontend domain)
const token = localStorage.getItem('token'); // or however you store it

fetch('http://10.1.2.165:8000/admin/users', {
  headers: {
    Authorization: `Bearer ${token}`,
  },
})
  .then((res) => res.json())
  .then((data) => {
    console.log('Response:', data);
    console.log('Users:', data.users);
    console.log('Total:', data.total);
  })
  .catch((err) => console.error('Error:', err));
```

### Using Postman

1. **Method:** GET
2. **URL:** `http://10.1.2.165:8000/admin/users`
3. **Headers:**
   - Key: `Authorization`
   - Value: `Bearer YOUR_TOKEN`
4. **Query Params (optional):**
   - `skip`: 0
   - `limit`: 100
   - `search`: (optional)

---

## Debugging Checklist

- [ ] Is the backend running? (`docker ps`)
- [ ] Is the endpoint URL correct? (`/admin/users` not `/api/admin/users`)
- [ ] Is the token valid and not expired?
- [ ] Does the user have admin permissions? (`permissions === "admin"`)
- [ ] Is the Authorization header formatted correctly? (`Bearer <token>`)
- [ ] Are you accessing `data.users` not `data` directly?
- [ ] Check browser console for CORS errors
- [ ] Check network tab for actual request/response
- [ ] Verify backend logs for errors

---

## Quick Test Script

```javascript
// test-admin-users.js
async function testAdminUsers() {
  const token = 'YOUR_ADMIN_TOKEN';
  const baseUrl = 'http://10.1.2.165:8000';

  try {
    console.log('Testing /admin/users endpoint...');

    const response = await fetch(`${baseUrl}/admin/users?limit=5`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    console.log('Status:', response.status);
    console.log('Status Text:', response.statusText);

    if (!response.ok) {
      const error = await response.json();
      console.error('Error Response:', error);
      return;
    }

    const data = await response.json();
    console.log('✅ Success!');
    console.log('Response Structure:', Object.keys(data));
    console.log('Users Count:', data.users?.length || 0);
    console.log('Total:', data.total);
    console.log('First User:', data.users?.[0]);
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

testAdminUsers();
```

Run in Node.js or browser console to test the endpoint.

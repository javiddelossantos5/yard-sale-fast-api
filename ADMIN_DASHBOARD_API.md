# Admin Dashboard API Documentation

This document describes all the admin endpoints available for managing the platform.

## Authentication

All admin endpoints require:
- **Authorization Header**: `Bearer <token>`
- **User Permissions**: User must have `permissions: "admin"`

## Admin Capabilities

### 1. Edit Any Item or Yard Sale
Admins can now edit and delete ANY marketplace item or yard sale, not just their own.

### 2. View Dashboard Statistics
Get overview statistics for the platform.

### 3. View All Items and Yard Sales
View all items and yard sales including hidden/inactive ones.

---

## Endpoints

### 1. Dashboard Statistics

**GET** `/admin/dashboard/stats`

Get platform-wide statistics.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "total_users": 150,
  "total_items": 500,
  "total_yard_sales": 200,
  "active_items": 450,
  "active_yard_sales": 180,
  "free_items": 50,
  "admin_users": 3,
  "recent_activity": {
    "items_last_7_days": 25,
    "yard_sales_last_7_days": 15,
    "users_last_7_days": 10
  }
}
```

**Frontend Example:**
```javascript
const response = await fetch('http://10.1.2.165:8000/admin/dashboard/stats', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
const stats = await response.json();
```

---

### 2. Get All Items (Admin View)

**GET** `/admin/items`

Get all marketplace items including hidden ones.

**Query Parameters:**
- `skip` (int, default: 0) - Pagination offset
- `limit` (int, default: 100) - Items per page
- `status` (string, optional) - Filter by status: "active", "sold", "hidden"

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Item Name",
      "description": "Item description",
      "price": 50.00,
      "is_free": false,
      "status": "active",
      "is_public": true,
      "category": "Electronics",
      "owner_id": "user-uuid",
      "owner_username": "username",
      "owner_is_admin": false,
      "comment_count": 5,
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "total": 500,
  "limit": 100,
  "offset": 0,
  "has_more": true
}
```

**Frontend Example:**
```javascript
// Get all items
const response = await fetch('http://10.1.2.165:8000/admin/items?limit=50&skip=0', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
const data = await response.json();

// Get only hidden items
const hiddenResponse = await fetch('http://10.1.2.165:8000/admin/items?status=hidden', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

---

### 3. Get All Yard Sales (Admin View)

**GET** `/admin/yard-sales`

Get all yard sales including inactive ones.

**Query Parameters:**
- `skip` (int, default: 0) - Pagination offset
- `limit` (int, default: 100) - Yard sales per page
- `status` (string, optional) - Filter by status: "active", "closed", "on_break"

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "yard_sales": [
    {
      "id": "uuid",
      "title": "Yard Sale Title",
      "description": "Description",
      "city": "Vernal",
      "state": "UT",
      "status": "active",
      "is_active": true,
      "owner_id": "user-uuid",
      "owner_username": "username",
      "owner_is_admin": false,
      "comment_count": 10,
      "created_at": "2024-01-01T00:00:00",
      "start_date": "2024-01-15"
    }
  ],
  "total": 200,
  "limit": 100,
  "offset": 0,
  "has_more": true
}
```

**Frontend Example:**
```javascript
const response = await fetch('http://10.1.2.165:8000/admin/yard-sales?limit=50', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
const data = await response.json();
```

---

### 4. Edit Any Marketplace Item

**PUT** `/market-items/{item_id}`

Admins can now edit ANY item, not just their own.

**Headers:**
```
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "price": 75.00,
  "status": "active",
  "is_free": false,
  "category": "Electronics"
}
```

**Response:** Returns updated `MarketItemResponse`

**Frontend Example:**
```javascript
const response = await fetch(`http://10.1.2.165:8000/market-items/${itemId}`, {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: "Updated Name",
    price: 75.00,
    status: "active"
  })
});
const updatedItem = await response.json();
```

---

### 5. Edit Any Yard Sale

**PUT** `/yard-sales/{yard_sale_id}`

Admins can now edit ANY yard sale, not just their own.

**Headers:**
```
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "Updated Title",
  "description": "Updated description",
  "status": "active",
  "is_active": true
}
```

**Response:** Returns updated `YardSaleResponse`

**Frontend Example:**
```javascript
const response = await fetch(`http://10.1.2.165:8000/yard-sales/${yardSaleId}`, {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: "Updated Title",
    status: "active"
  })
});
const updatedYardSale = await response.json();
```

---

### 6. Delete Any Marketplace Item

**DELETE** `/market-items/{item_id}`

Admins can now delete ANY item, not just their own.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Response:** `204 No Content`

**Frontend Example:**
```javascript
const response = await fetch(`http://10.1.2.165:8000/market-items/${itemId}`, {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
if (response.ok) {
  console.log('Item deleted successfully');
}
```

---

### 7. Delete Any Yard Sale

**DELETE** `/yard-sales/{yard_sale_id}`

Admins can now delete ANY yard sale, not just their own.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Response:** `204 No Content`

**Frontend Example:**
```javascript
const response = await fetch(`http://10.1.2.165:8000/yard-sales/${yardSaleId}`, {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
if (response.ok) {
  console.log('Yard sale deleted successfully');
}
```

---

### 8. Get All Users (Existing)

**GET** `/admin/users`

Get all users with pagination.

**Query Parameters:**
- `skip` (int, default: 0)
- `limit` (int, default: 100)

**Frontend Example:**
```javascript
const response = await fetch('http://10.1.2.165:8000/admin/users?limit=50', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
const users = await response.json();
```

---

## Frontend Implementation Guide

### 1. Check if User is Admin

```javascript
// After login, check user permissions
const user = await getCurrentUser(); // Your existing function
const isAdmin = user.permissions === 'admin';

if (isAdmin) {
  // Show admin dashboard link/button
}
```

### 2. Admin Dashboard Component

```javascript
// AdminDashboard.svelte (or React/Vue equivalent)
async function loadDashboardStats() {
  const response = await fetch('http://10.1.2.165:8000/admin/dashboard/stats', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  const stats = await response.json();
  
  // Display stats
  console.log('Total Users:', stats.total_users);
  console.log('Total Items:', stats.total_items);
  console.log('Recent Activity:', stats.recent_activity);
}

async function loadAllItems(status = null) {
  let url = 'http://10.1.2.165:8000/admin/items?limit=50';
  if (status) {
    url += `&status=${status}`;
  }
  
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  const data = await response.json();
  return data.items;
}

async function editItem(itemId, updates) {
  const response = await fetch(`http://10.1.2.165:8000/market-items/${itemId}`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(updates)
  });
  return await response.json();
}

async function deleteItem(itemId) {
  const response = await fetch(`http://10.1.2.165:8000/market-items/${itemId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.ok;
}
```

### 3. Admin Item List Component

```javascript
// AdminItemList.svelte
let items = [];
let loading = true;

onMount(async () => {
  const response = await fetch('http://10.1.2.165:8000/admin/items?limit=100', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  const data = await response.json();
  items = data.items;
  loading = false;
});

async function handleEdit(itemId) {
  // Open edit modal/form
  // Call editItem(itemId, updates)
}

async function handleDelete(itemId) {
  if (confirm('Are you sure you want to delete this item?')) {
    await deleteItem(itemId);
    // Refresh list
    items = items.filter(item => item.id !== itemId);
  }
}
```

---

## Summary of Changes

### Backend Changes Made:

1. **Modified Update Endpoints:**
   - `PUT /market-items/{item_id}` - Now allows admins to edit any item
   - `PUT /yard-sales/{yard_sale_id}` - Now allows admins to edit any yard sale

2. **Modified Delete Endpoints:**
   - `DELETE /market-items/{item_id}` - Now allows admins to delete any item
   - `DELETE /yard-sales/{yard_sale_id}` - Now allows admins to delete any yard sale

3. **New Admin Dashboard Endpoints:**
   - `GET /admin/dashboard/stats` - Platform statistics
   - `GET /admin/items` - All items (including hidden)
   - `GET /admin/yard-sales` - All yard sales (including inactive)

### How It Works:

- Regular users: Can only edit/delete their own items and yard sales
- Admin users: Can edit/delete ANY item or yard sale
- Permission check: `if current_user.permissions == "admin"` allows access to any item/sale

---

## Testing

Test the endpoints using curl or Postman:

```bash
# Get dashboard stats
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://10.1.2.165:8000/admin/dashboard/stats

# Get all items
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://10.1.2.165:8000/admin/items?limit=10

# Edit any item (as admin)
curl -X PUT \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Name","price":100}' \
  http://10.1.2.165:8000/market-items/ITEM_ID
```

---

## Error Handling

All endpoints return standard HTTP status codes:
- `200 OK` - Success
- `401 Unauthorized` - Invalid or missing token
- `403 Forbidden` - User is not an admin
- `404 Not Found` - Item/sale/user not found
- `500 Internal Server Error` - Server error

Check the response status and handle errors appropriately in your frontend.


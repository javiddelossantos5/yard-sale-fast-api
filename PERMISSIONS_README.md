# User Permissions System

This document explains the user permissions system implemented in the FastAPI application.

## Overview

The application now supports three levels of user permissions:

- **user**: Regular users with basic access
- **moderator**: Users with moderation capabilities
- **admin**: Full administrative access

## Permission Levels

### User (Default)

- Can create and manage their own yard sales
- Can comment on yard sales
- Can send messages to other users
- Can rate other users
- Can report inappropriate content
- Can manage their own profile

### Moderator

- All user permissions
- Can view all reports
- Can moderate content
- Can access moderation tools

### Admin

- All moderator permissions
- Can view all users
- Can create, update, and delete any user
- Can change user permissions
- Can access all administrative functions

## Database Changes

### New Column

A new `permissions` column has been added to the `users` table:

```sql
permissions VARCHAR(20) NOT NULL DEFAULT 'user'
```

### Migration

Run the migration script to add the permissions column to existing databases:

```bash
python add_permissions_column.py
```

## API Changes

### User Registration

The registration endpoint now accepts a `permissions` field:

```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "password123",
  "full_name": "New User",
  "permissions": "user"
}
```

### User Response

All user responses now include the permissions field:

```json
{
  "id": 1,
  "username": "newuser",
  "email": "user@example.com",
  "full_name": "New User",
  "permissions": "user",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

## New Admin Endpoints

### Get All Users (Admin Only)

```
GET /admin/users
```

Returns a list of all users with pagination support.

### Get User by ID (Admin Only)

```
GET /admin/users/{user_id}
```

Returns detailed information about a specific user.

### Update User (Admin Only)

```
PUT /admin/users/{user_id}
```

Allows admins to update any user's information including permissions.

### Delete User (Admin Only)

```
DELETE /admin/users/{user_id}
```

Allows admins to delete any user (except themselves).

### Get All Reports (Moderator/Admin Only)

```
GET /admin/reports
```

Returns all reports for moderation purposes.

## Authentication Dependencies

### New Dependency Functions

- `get_current_admin_user`: Ensures user has admin permissions
- `get_current_moderator_or_admin_user`: Ensures user has moderator or admin permissions

### Usage Example

```python
@app.get("/admin/users")
async def get_all_users(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    # Only admins can access this endpoint
    pass
```

## Testing

### Test Script

Run the test script to verify the permissions system:

```bash
python test_permissions.py
```

### Manual Testing

1. Start the server: `python main.py`
2. Run the migration: `python add_permissions_column.py`
3. Create users with different permission levels
4. Test admin endpoints with different user types

## Security Considerations

1. **Default Permissions**: New users are created with "user" permissions by default
2. **Permission Validation**: All admin endpoints validate user permissions
3. **Self-Protection**: Admins cannot delete their own accounts
4. **Token-Based**: Permissions are checked on every request using JWT tokens

## Creating Admin Users

### Method 1: Migration Script

The migration script can create an admin user:

```bash
python add_permissions_column.py
# Choose 'y' when prompted to create admin user
```

### Method 2: Direct Registration

Register a user with admin permissions:

```json
POST /register
{
  "username": "admin",
  "email": "admin@example.com",
  "password": "securepassword",
  "permissions": "admin"
}
```

### Method 3: Update Existing User

Use the admin endpoint to promote an existing user:

```json
PUT /admin/users/{user_id}
{
  "permissions": "admin"
}
```

## Error Handling

### Permission Denied (403)

When a user tries to access an endpoint they don't have permission for:

```json
{
  "detail": "Admin access required"
}
```

### User Not Found (404)

When trying to access a non-existent user:

```json
{
  "detail": "User not found"
}
```

## Future Enhancements

Potential improvements to the permissions system:

1. Role-based permissions with granular controls
2. Permission inheritance
3. Temporary permission grants
4. Audit logging for permission changes
5. Permission groups for easier management

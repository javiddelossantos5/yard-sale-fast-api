# Yard Sale Finder API

A comprehensive yard sale platform where users can post yard sales and discover nearby sales in their community.

## Features

- **🔐 Authentication**: JWT-based login/logout with password hashing
- **👤 User Management**: User registration and profile management
- **🏠 Yard Sale Management**: Create, read, update, delete yard sales
- **📍 Location-Based Search**: Find yard sales by city, state, ZIP code
- **🏷️ Advanced Filtering**: Filter by categories, price range, payment methods
- **💬 Community Comments**: Comment system for yard sale discussions
- **📧 Personal Messaging**: Private messaging between yard sale owners and customers
- **🔒 Protected Routes**: All yard sale operations require authentication
- **✅ Data Validation**: Using Pydantic models for request/response validation
- **⚠️ Error Handling**: Proper HTTP status codes and error messages
- **📚 API Documentation**: Automatic Swagger UI and ReDoc documentation
- **🎯 Type Hints**: Full type safety with Python type hints

## Available Routes

### Core Endpoints

- `GET /` - Welcome message and API information
- `GET /health` - Health check endpoint

### Authentication Endpoints

- `POST /register` - Register a new user
- `POST /login` - Login and get access token
- `POST /logout` - Logout (revoke token)
- `GET /me` - Get current user information

### Yard Sale Management (🔒 Protected Routes)

- `POST /yard-sales` - Create a new yard sale
- `PUT /yard-sales/{yard_sale_id}` - Update yard sale (owner only)
- `DELETE /yard-sales/{yard_sale_id}` - Delete yard sale (owner only)

### Yard Sale Discovery (🌍 Public Routes)

- `GET /yard-sales` - Get all active yard sales with filtering (including status filter)
- `GET /yard-sales/{yard_sale_id}` - Get specific yard sale details
- `GET /yard-sales/search/nearby` - Search yard sales by ZIP code

### Comment System (🔒 Protected Routes)

- `POST /yard-sales/{yard_sale_id}/comments` - Add comment to yard sale
- `GET /yard-sales/{yard_sale_id}/comments` - Get all comments for yard sale
- `DELETE /comments/{comment_id}` - Delete comment (owner only)

### Personal Messaging System (🔒 Protected Routes)

- `POST /yard-sales/{yard_sale_id}/messages` - Send private message to yard sale owner
- `GET /yard-sales/{yard_sale_id}/messages` - Get conversation for specific yard sale
- `GET /messages` - Get all messages for current user (inbox)
- `GET /messages/unread-count` - Get count of unread messages
- `PUT /messages/{message_id}/read` - Mark message as read
- `DELETE /messages/{message_id}` - Delete message (sender or recipient)

### Item Management (🔒 Protected Routes)

- `GET /items` - Get all items for current user
- `GET /items/{item_id}` - Get specific item by ID (user's items only)
- `POST /items` - Create new item
- `PUT /items/{item_id}` - Update existing item (user's items only)
- `DELETE /items/{item_id}` - Delete item (user's items only)
- `GET /items/search/` - Search items with query parameters (user's items only)

## Getting Started

### 1. Activate Virtual Environment

```bash
source venv/bin/activate
```

### 2. Run the Application

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Access the API

- **API Base URL**: http://localhost:8000
- **Interactive API Docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative API Docs (ReDoc)**: http://localhost:8000/redoc

## Example Usage

### 1. Register a New User

```bash
curl -X POST "http://localhost:8000/register" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "testuser",
       "email": "test@example.com",
       "password": "password123"
     }'
```

### 2. Login and Get Access Token

```bash
curl -X POST "http://localhost:8000/login" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "testuser",
       "password": "password123"
     }'
```

**Response:**

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 3. Create an Item (Protected Route)

```bash
curl -X POST "http://localhost:8000/items" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -d '{
       "name": "Sample Item",
       "description": "A sample item for testing",
       "price": 29.99,
       "is_available": true
     }'
```

### 4. Get All Items (Protected Route)

```bash
curl -X GET "http://localhost:8000/items" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 5. Get Current User Info

```bash
curl -X GET "http://localhost:8000/me" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 6. Search Items (Protected Route)

```bash
curl -X GET "http://localhost:8000/items/search/?min_price=10&max_price=50&is_available=true" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 7. Logout

```bash
curl -X POST "http://localhost:8000/logout" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Yard Sale Examples

### 8. Create a Yard Sale

```bash
curl -X POST "http://localhost:8000/yard-sales" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -d '{
       "title": "Multi-Family Yard Sale",
       "description": "Furniture, kids clothes, electronics, toys, and household items. Everything must go!",
       "start_date": "2025-10-25",
       "end_date": "2025-10-26",
       "start_time": "08:00:00",
       "end_time": "16:00:00",
       "address": "123 Main Street",
       "city": "San Francisco",
       "state": "CA",
       "zip_code": "94102",
       "contact_name": "John Smith",
       "contact_phone": "(555) 123-4567",
       "contact_email": "john@example.com",
       "allow_messages": true,
       "categories": ["Furniture", "Clothing", "Electronics", "Toys"],
       "price_range": "Under $50",
       "payment_methods": ["Cash", "Venmo", "Zelle"],
       "status": "active"
     }'
```

### 8a. Create Yard Sale with Different Status

```bash
# Create a yard sale that's on break
curl -X POST "http://localhost:8000/yard-sales" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -d '{
       "title": "Weekend Sale - On Break",
       "description": "Taking a lunch break, will be back soon!",
       "start_date": "2025-10-25",
       "start_time": "09:00:00",
       "end_time": "17:00:00",
       "address": "456 Oak Street",
       "city": "Vernal",
       "state": "UT",
       "zip_code": "84078",
       "contact_name": "Jane Doe",
       "contact_phone": "(435) 555-1234",
       "allow_messages": true,
       "categories": ["Furniture", "Clothing"],
       "price_range": "Under $25",
       "payment_methods": ["Cash"],
       "status": "on_break"
     }'
```

### 9. Get All Yard Sales

```bash
curl -X GET "http://localhost:8000/yard-sales"
```

### 10. Search Yard Sales by City

```bash
curl -X GET "http://localhost:8000/yard-sales?city=San%20Francisco"
```

### 11. Search Yard Sales by Category

```bash
curl -X GET "http://localhost:8000/yard-sales?category=Furniture"
```

### 12. Find Nearby Yard Sales

```bash
curl -X GET "http://localhost:8000/yard-sales/search/nearby?zip_code=94102"
```

### 12a. Filter Yard Sales by Status

```bash
# Get only active yard sales
curl -X GET "http://localhost:8000/yard-sales?status=active"

# Get yard sales that are on break
curl -X GET "http://localhost:8000/yard-sales?status=on_break"

# Get closed yard sales
curl -X GET "http://localhost:8000/yard-sales?status=closed"
```

### 13. Add a Comment to Yard Sale

```bash
curl -X POST "http://localhost:8000/yard-sales/1/comments" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -d '{
       "content": "Great! I will definitely stop by on Saturday morning. Do you have any vintage furniture?"
     }'
```

### 14. Get Comments for Yard Sale

```bash
curl -X GET "http://localhost:8000/yard-sales/1/comments"
```

## Personal Messaging Examples

### 15. Send a Private Message

```bash
curl -X POST "http://localhost:8000/yard-sales/1/messages" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -d '{
       "content": "Hi! I am interested in the furniture you have for sale. Do you have any dining room tables available?",
       "recipient_id": 2
     }'
```

### 16. Get Conversation for Yard Sale

```bash
curl -X GET "http://localhost:8000/yard-sales/1/messages" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 17. Get All Messages (Inbox)

```bash
curl -X GET "http://localhost:8000/messages" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 18. Get Unread Messages Count

```bash
curl -X GET "http://localhost:8000/messages/unread-count" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 19. Mark Message as Read

```bash
curl -X PUT "http://localhost:8000/messages/1/read" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 20. Delete a Message

```bash
curl -X DELETE "http://localhost:8000/messages/1" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Yard Sale Status Management

### 21. Update Yard Sale Status

```bash
# Set yard sale to "on_break" (taking a break)
curl -X PUT "http://localhost:8000/yard-sales/1" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -d '{
       "status": "on_break"
     }'

# Set yard sale to "closed" (sale ended)
curl -X PUT "http://localhost:8000/yard-sales/1" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -d '{
       "status": "closed"
     }'

# Set yard sale back to "active"
curl -X PUT "http://localhost:8000/yard-sales/1" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -d '{
       "status": "active"
     }'
```

## Data Models

### User

- `id`: Unique identifier (auto-generated)
- `username`: Username (required, 3-50 characters)
- `email`: Email address (required, must be valid email)
- `password`: Password (required, 6-72 characters, bcrypt limitation)
- `is_active`: Account status (default: true)
- `created_at`: Creation timestamp (auto-generated)

### Item

- `id`: Unique identifier (auto-generated)
- `name`: Item name (required, 1-100 characters)
- `description`: Item description (optional, max 500 characters)
- `price`: Item price (required, must be positive)
- `is_available`: Availability status (default: true)
- `created_at`: Creation timestamp (auto-generated)
- `owner_id`: ID of the user who owns this item

### Token

- `access_token`: JWT access token
- `token_type`: Token type (always "bearer")
- `expires_in`: Token expiration time in seconds

### Yard Sale

- `id`: Unique identifier (auto-generated)
- `title`: Yard sale title (required, 1-200 characters)
- `description`: Detailed description of items for sale (optional)
- `start_date`: Start date of the yard sale (required)
- `end_date`: End date (optional for multi-day sales)
- `start_time`: Start time each day (required)
- `end_time`: End time each day (required)
- `address`: Full street address (required, 1-300 characters)
- `city`: City name (required, 1-100 characters)
- `state`: State abbreviation (required, 2 characters)
- `zip_code`: ZIP code (required, 5-10 characters)
- `latitude`: Latitude for map integration (optional)
- `longitude`: Longitude for map integration (optional)
- `contact_name`: Contact person name (required, 1-100 characters)
- `contact_phone`: Contact phone number (optional, max 20 characters)
- `contact_email`: Contact email (optional, max 100 characters)
- `allow_messages`: Allow messages through app (default: true)
- `categories`: List of item categories (optional)
- `price_range`: Price range (optional, max 50 characters)
- `payment_methods`: Accepted payment methods (optional)
- `photos`: List of photo URLs/paths (optional)
- `featured_image`: Featured image URL/path (optional, max 500 characters)
- `is_active`: Whether the yard sale is active (default: true)
- `status`: Yard sale status - "active", "closed", or "on_break" (default: "active")
- `created_at`: Creation timestamp (auto-generated)
- `updated_at`: Last update timestamp (auto-generated)
- `owner_id`: ID of the user who created this yard sale
- `owner_username`: Username of the yard sale owner
- `comment_count`: Number of comments on this yard sale

### Comment

- `id`: Unique identifier (auto-generated)
- `content`: Comment content (required, 1-1000 characters)
- `created_at`: Creation timestamp (auto-generated)
- `updated_at`: Last update timestamp (auto-generated)
- `user_id`: ID of the user who wrote the comment
- `username`: Username of the comment author
- `yard_sale_id`: ID of the yard sale this comment belongs to

### Message

- `id`: Unique identifier (auto-generated)
- `content`: Message content (required, 1-1000 characters)
- `is_read`: Whether the message has been read (default: false)
- `created_at`: Creation timestamp (auto-generated)
- `yard_sale_id`: ID of the yard sale this message is about
- `sender_id`: ID of the user who sent the message
- `sender_username`: Username of the message sender
- `recipient_id`: ID of the user who received the message
- `recipient_username`: Username of the message recipient

## Error Handling

The API returns appropriate HTTP status codes:

- `200 OK` - Successful GET/PUT requests
- `201 Created` - Successful POST requests (registration, login, item creation)
- `204 No Content` - Successful DELETE requests
- `400 Bad Request` - Invalid request data, duplicate username/email
- `401 Unauthorized` - Invalid credentials, missing/invalid token
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation errors

## Development

The application includes:

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: Bcrypt password hashing for security
- **Auto-reload**: Code changes trigger automatic reload (`--reload` flag)
- **Comprehensive Error Handling**: Proper HTTP status codes and error messages
- **Input Validation**: Pydantic models with field validation
- **Type Hints**: Full type safety with Python type hints
- **User Isolation**: Each user can only access their own items
- **Token Management**: JWT tokens with expiration and blacklisting
- **In-memory Storage**: Replace with database for production use

## Security Features

- **Password Hashing**: Passwords are hashed using bcrypt
- **JWT Tokens**: Secure token-based authentication
- **Token Expiration**: Tokens expire after 30 minutes
- **User Isolation**: Users can only access their own data
- **Input Validation**: All inputs are validated and sanitized
- **Error Handling**: Secure error messages without sensitive information

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

### Community & Trust System (🔒 Protected Routes)

#### User Ratings & Reviews

- `POST /users/{user_id}/ratings` - Rate and review a user (1-5 stars)
- `GET /users/{user_id}/ratings` - Get all ratings for a user
- `GET /users/{user_id}/profile` - Get user profile with trust metrics

#### Reporting System

- `POST /reports` - Report inappropriate content, scams, or users
- `GET /reports` - Get user's own reports

#### Verification System

- `POST /verifications` - Request verification (email, phone, identity, address)
- `GET /verifications` - Get user's verification status

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

## Community & Trust System Examples

### 22. Rate and Review a User

```bash
# Rate a user after a successful yard sale interaction
curl -X POST "http://localhost:8000/users/15/ratings" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -d '{
       "rating": 5,
       "review_text": "Great seller! Very friendly and had exactly what I was looking for. Highly recommend!",
       "yard_sale_id": 23
     }'
```

### 23. Get User Ratings

```bash
# Get all ratings for a specific user
curl -X GET "http://localhost:8000/users/15/ratings"
```

### 24. Get User Profile with Trust Metrics

```bash
# Get user profile including average rating, total ratings, and verification badges
curl -X GET "http://localhost:8000/users/15/profile"
```

### 25. Report Inappropriate Content

```bash
# Report a yard sale for inappropriate content
curl -X POST "http://localhost:8000/reports" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -d '{
       "report_type": "inappropriate",
       "description": "This yard sale listing contains inappropriate content and misleading information.",
       "reported_yard_sale_id": 1
     }'

# Report a user for suspicious behavior
curl -X POST "http://localhost:8000/reports" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -d '{
       "report_type": "scam",
       "description": "This user is asking for payment upfront without showing items. Very suspicious behavior.",
       "reported_user_id": 15
     }'
```

### 26. Request Verification

```bash
# Request email verification
curl -X POST "http://localhost:8000/verifications" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -d '{
       "verification_type": "email"
     }'

# Request phone verification
curl -X POST "http://localhost:8000/verifications" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -d '{
       "verification_type": "phone"
     }'
```

### 27. Get Verification Status

```bash
# Get all verification requests for current user
curl -X GET "http://localhost:8000/verifications" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
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
- `conversation_id`: ID of the conversation this message belongs to
- `sender_id`: ID of the user who sent the message
- `sender_username`: Username of the message sender
- `recipient_id`: ID of the user who received the message
- `recipient_username`: Username of the message recipient

### User Rating

- `id`: Unique identifier (auto-generated)
- `rating`: Star rating from 1-5 (required)
- `review_text`: Optional review text (up to 1000 characters)
- `created_at`: Creation timestamp (auto-generated)
- `reviewer_id`: ID of the user giving the rating
- `reviewer_username`: Username of the reviewer
- `rated_user_id`: ID of the user being rated
- `rated_user_username`: Username of the rated user
- `yard_sale_id`: Optional ID of related yard sale
- `yard_sale_title`: Title of related yard sale (if applicable)

### User Profile (with Trust Metrics)

- `id`: Unique identifier (auto-generated)
- `username`: Username (required, 3-50 characters)
- `email`: Email address (required, valid email format)
- `full_name`: Full name (optional, up to 100 characters)
- `phone_number`: Phone number (optional, up to 20 characters)
- `city`: City (optional, up to 100 characters)
- `state`: State abbreviation (optional, 2 characters)
- `zip_code`: ZIP code (optional, up to 10 characters)
- `bio`: User bio (optional, up to 1000 characters)
- `is_active`: Account status (default: true)
- `created_at`: Account creation timestamp (auto-generated)
- `updated_at`: Last update timestamp (auto-generated)
- `average_rating`: Average rating from all reviews (calculated)
- `total_ratings`: Total number of ratings received
- `verification_badges`: List of verified verification types
- `is_verified`: Whether user has any verified badges

### Report

- `id`: Unique identifier (auto-generated)
- `report_type`: Type of report ("scam", "inappropriate", "spam", "other")
- `description`: Detailed description of the issue (required, 10-1000 characters)
- `status`: Report status ("pending", "reviewed", "resolved", "dismissed")
- `created_at`: Creation timestamp (auto-generated)
- `reporter_id`: ID of the user making the report
- `reporter_username`: Username of the reporter
- `reported_user_id`: Optional ID of reported user
- `reported_user_username`: Username of reported user (if applicable)
- `reported_yard_sale_id`: Optional ID of reported yard sale
- `reported_yard_sale_title`: Title of reported yard sale (if applicable)

### Verification

- `id`: Unique identifier (auto-generated)
- `verification_type`: Type of verification ("email", "phone", "identity", "address")
- `status`: Verification status ("pending", "verified", "rejected")
- `verified_at`: Timestamp when verification was completed (if verified)
- `created_at`: Request creation timestamp (auto-generated)
- `user_id`: ID of the user requesting verification
- `user_username`: Username of the user requesting verification

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

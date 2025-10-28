from fastapi import FastAPI, HTTPException, status, Depends, Form, WebSocket, WebSocketDisconnect, UploadFile, File, Header, Cookie, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
import uvicorn
from datetime import datetime, timedelta
import pytz
import json
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
from sqlalchemy.orm import Session
import uuid
import boto3
from botocore.exceptions import ClientError
import os
from pathlib import Path
from database import get_db, create_tables, User, Item, YardSale, Comment, Message, Conversation, UserRating, Report, Verification, VisitedYardSale, Notification
from contextlib import asynccontextmanager
from datetime import date, time
from typing import List, Optional
from enum import Enum

# User Permission Levels
class UserPermission(str, Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"

# Authentication configuration
SECRET_KEY = secrets.token_urlsafe(32)  # Generate a random secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 180  # 3 hours

# MinIO S3 Configuration
MINIO_ENDPOINT_URL = "http://10.1.2.165:9000"
MINIO_ACCESS_KEY_ID = "minioadmin"
MINIO_SECRET_ACCESS_KEY = "minioadmin"
MINIO_BUCKET_NAME = "yardsale"
MINIO_REGION = "us-east-1"  # MinIO ignores this, but boto3 requires it

# Domain configuration for image URLs
DOMAIN_NAME = "http://localhost:8000"  # For local development

# Initialize S3 client for MinIO
s3_client = boto3.client(
    's3',
    endpoint_url=MINIO_ENDPOINT_URL,
    aws_access_key_id=MINIO_ACCESS_KEY_ID,
    aws_secret_access_key=MINIO_SECRET_ACCESS_KEY,
    region_name=MINIO_REGION
)

# Helper functions
def get_mountain_time() -> datetime:
    """Get current time in Mountain Time Zone (Vernal, Utah)"""
    mountain_tz = pytz.timezone('America/Denver')  # Mountain Time Zone
    return datetime.now(mountain_tz)

def get_standard_payment_methods() -> List[str]:
    """Get list of standard payment methods available"""
    return [
        "Cash",
        "Credit Card",
        "Debit Card",
        "Venmo",
        "PayPal",
        "Zelle",
        "Apple Pay",
        "Google Pay",
        "Samsung Pay",
        "Cash App",
        "Check"
    ]

# Yard Sale Status Enum
class YardSaleStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    ON_BREAK = "on_break"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__default_rounds=12)

# Security scheme
security = HTTPBearer()

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        create_tables()
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
    yield
    # Shutdown (if needed)

# Create FastAPI instance
app = FastAPI(
    title="Yard Sale Finder API",
    description="A comprehensive yard sale platform where users can post yard sales and discover nearby sales in their community",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
    lifespan=lifespan
)

# Mount static files for frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve frontend at root
@app.get("/")
async def serve_frontend():
    """Serve the image upload frontend"""
    from fastapi.responses import FileResponse
    return FileResponse("static/index.html")


# Pydantic models for request/response validation
class Location(BaseModel):
    city: Optional[str] = Field(None, max_length=100, description="City name")
    state: Optional[str] = Field(None, max_length=2, description="State abbreviation")
    zip: Optional[str] = Field(None, max_length=10, description="ZIP code")

class PaymentMethod(BaseModel):
    username: Optional[str] = Field(None, max_length=100, description="Username for the payment method")
    email: Optional[str] = Field(None, max_length=100, description="Email for the payment method")
    phone: Optional[str] = Field(None, max_length=20, description="Phone for the payment method")
    link: Optional[str] = Field(None, max_length=500, description="Link for the payment method")

class PaymentMethods(BaseModel):
    venmo: Optional[PaymentMethod] = None
    paypal: Optional[PaymentMethod] = None
    zelle: Optional[PaymentMethod] = None
    google_pay: Optional[PaymentMethod] = None
    apple_pay: Optional[PaymentMethod] = None

class UserPreferences(BaseModel):
    notifications: bool = Field(True, description="Enable notifications")
    radius_preference: int = Field(10, ge=1, le=100, description="Search radius in miles")
    theme: str = Field("light", description="UI theme preference")

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: str = Field(..., description="Email address")

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=72, description="Password (6-72 characters)")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")
    location: Optional[Location] = None
    bio: Optional[str] = Field(None, max_length=1000, description="User bio")
    permissions: UserPermission = Field(UserPermission.USER, description="User permission level")

class UserResponse(UserBase):
    id: str
    full_name: Optional[str]
    phone_number: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    bio: Optional[str]
    is_active: bool
    permissions: UserPermission
    created_at: datetime
    updated_at: datetime

class UserLogin(BaseModel):
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")

class PasswordUpdate(BaseModel):
    email: str = Field(..., description="Email address of the account")
    current_password: str = Field(..., min_length=6, max_length=72, description="Current password")
    new_password: str = Field(..., min_length=6, max_length=72, description="New password (6-72 characters)")

class PasswordReset(BaseModel):
    email: str = Field(..., description="Email address of the account")
    new_password: str = Field(..., min_length=6, max_length=72, description="New password (6-72 characters)")
    confirm_password: str = Field(..., min_length=6, max_length=72, description="Confirm new password")

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    username: Optional[str] = None

class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Item name")
    description: Optional[str] = Field(None, max_length=500, description="Item description")
    price: float = Field(..., gt=0, description="Item price (must be positive)")
    is_available: bool = True

class ItemResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    price: float
    is_available: bool
    created_at: datetime
    owner_id: str

class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, gt=0)
    is_available: Optional[bool] = None

# Yard Sale Models
class YardSaleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Yard sale title")
    description: Optional[str] = Field(None, description="Detailed description of items for sale")
    
    # Date and Time
    start_date: date = Field(..., description="Start date of the yard sale")
    end_date: Optional[date] = Field(None, description="End date (optional for multi-day sales)")
    start_time: time = Field(..., description="Start time each day")
    end_time: time = Field(..., description="End time each day")
    
    # Location
    address: str = Field(..., min_length=1, max_length=300, description="Full street address")
    city: str = Field(..., min_length=1, max_length=100, description="City name")
    state: str = Field(..., min_length=2, max_length=2, description="State abbreviation (e.g., CA, NY)")
    zip_code: str = Field(..., min_length=5, max_length=10, description="ZIP code")
    latitude: Optional[float] = Field(None, description="Latitude for map integration")
    longitude: Optional[float] = Field(None, description="Longitude for map integration")
    
    # Contact Information
    contact_name: str = Field(..., min_length=1, max_length=100, description="Contact person name")
    contact_phone: Optional[str] = Field(None, max_length=20, description="Contact phone number")
    contact_email: Optional[str] = Field(None, max_length=100, description="Contact email")
    venmo_url: Optional[str] = Field(None, max_length=500, description="Venmo profile URL")
    allow_messages: bool = Field(True, description="Allow messages through app")
    
    # Sale Details
    categories: Optional[List[str]] = Field(None, description="List of item categories")
    price_range: Optional[str] = Field(None, max_length=50, description="Price range (e.g., 'Under $20', '$20-$100')")
    payment_methods: Optional[List[str]] = Field(None, description="Accepted payment methods")
    
    # Media
    photos: Optional[List[str]] = Field(None, description="List of photo URLs/paths")
    featured_image: Optional[str] = Field(None, max_length=500, description="Featured image URL/path")
    
    # Status
    status: Optional[YardSaleStatus] = Field(YardSaleStatus.ACTIVE, description="Yard sale status: active, closed, on_break")

class YardSaleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    address: Optional[str] = Field(None, min_length=1, max_length=300)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    zip_code: Optional[str] = Field(None, min_length=5, max_length=10)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_name: Optional[str] = Field(None, min_length=1, max_length=100)
    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_email: Optional[str] = Field(None, max_length=100)
    venmo_url: Optional[str] = Field(None, max_length=500)
    allow_messages: Optional[bool] = None
    categories: Optional[List[str]] = None
    price_range: Optional[str] = Field(None, max_length=50)
    payment_methods: Optional[List[str]] = None
    photos: Optional[List[str]] = None
    featured_image: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    status: Optional[YardSaleStatus] = Field(None, description="Yard sale status: active, closed, on_break")

class YardSaleResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    start_date: date
    end_date: Optional[date]
    start_time: time
    end_time: time
    address: str
    city: str
    state: str
    zip_code: str
    latitude: Optional[float]
    longitude: Optional[float]
    contact_name: str
    contact_phone: Optional[str]
    contact_email: Optional[str]
    venmo_url: Optional[str]
    allow_messages: bool
    categories: Optional[List[str]]
    price_range: Optional[str]
    payment_methods: Optional[List[str]]
    photos: Optional[List[str]]
    featured_image: Optional[str]
    is_active: bool
    status: YardSaleStatus
    created_at: datetime
    updated_at: datetime
    owner_id: str
    owner_username: str
    comment_count: int = 0
    is_visited: Optional[bool] = None
    visit_count: Optional[int] = None
    last_visited: Optional[datetime] = None

# Comment Models
class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000, description="Comment content")

class CommentResponse(BaseModel):
    id: str
    content: str
    created_at: datetime
    updated_at: datetime
    user_id: str
    username: str
    yard_sale_id: str

# Message Models
class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000, description="Message content")
    recipient_id: Optional[str] = Field(None, description="ID of the user receiving the message (for yard sale messages)")
    yard_sale_id: Optional[str] = Field(None, description="ID of the yard sale (for starting new conversations)")
    conversation_id: Optional[str] = Field(None, description="ID of the conversation (for replying in existing conversations)")

class ConversationResponse(BaseModel):
    id: str
    yard_sale_id: str
    yard_sale_title: str
    participant1_id: str
    participant1_username: str
    participant2_id: str
    participant2_username: str
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    unread_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    id: str
    content: str
    is_read: bool
    created_at: datetime
    conversation_id: str
    sender_id: str
    sender_username: str
    recipient_id: str
    recipient_username: str
    notification_id: Optional[str] = None  # NEW: Link to notification
    has_unread_notification: bool = False  # NEW: Quick check

# Trust System Models
class UserRatingCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    review_text: Optional[str] = Field(None, max_length=1000, description="Optional review text")
    yard_sale_id: Optional[str] = Field(None, description="Optional yard sale ID if rating is related to a specific sale")
    rated_user_id: Optional[str] = Field(None, description="ID of the user being rated (required for /ratings endpoint)")

class UserRatingResponse(BaseModel):
    id: str
    rating: int
    review_text: Optional[str]
    created_at: datetime
    reviewer_id: str
    reviewer_username: str
    rated_user_id: str
    rated_user_username: str
    yard_sale_id: Optional[str]
    yard_sale_title: Optional[str]

class UserProfileResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str]
    phone_number: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    bio: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    # Trust metrics
    average_rating: Optional[float] = None
    total_ratings: int = 0
    verification_badges: List[str] = []
    is_verified: bool = False

class ReportCreate(BaseModel):
    report_type: str = Field(..., description="Type of report: scam, inappropriate, spam, other")
    description: str = Field(..., min_length=10, max_length=1000, description="Detailed description of the issue")
    reported_user_id: Optional[str] = Field(None, description="ID of user being reported")
    reported_yard_sale_id: Optional[str] = Field(None, description="ID of yard sale being reported")

class ReportResponse(BaseModel):
    id: str
    report_type: str
    description: str
    status: str
    created_at: datetime
    reporter_id: str
    reporter_username: str
    reported_user_id: Optional[str]
    reported_user_username: Optional[str]
    reported_yard_sale_id: Optional[str]
    reported_yard_sale_title: Optional[str]

class VerificationCreate(BaseModel):
    verification_type: str = Field(..., description="Type of verification: email, phone, identity, address")

class VerificationResponse(BaseModel):
    id: str
    verification_type: str
    status: str
    verified_at: Optional[datetime]
    created_at: datetime
    user_id: str
    user_username: str

# Image Upload Models
class ImageUploadResponse(BaseModel):
    success: bool
    message: str
    image_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None

class ImageListResponse(BaseModel):
    images: List[dict]
    total: int

# Visit Tracking Models
class VisitedYardSaleResponse(BaseModel):
    id: str
    yard_sale_id: str
    yard_sale_title: str
    visited_at: datetime
    visit_count: int
    last_visited: datetime
    created_at: datetime

class VisitStatsResponse(BaseModel):
    yard_sale_id: str
    yard_sale_title: str
    total_visits: int
    unique_visitors: int
    most_recent_visit: Optional[datetime]
    average_visits_per_user: float

# Notification Models
class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime]
    user_id: str
    related_user_id: Optional[str]
    related_user_username: Optional[str]
    related_yard_sale_id: Optional[str]
    related_yard_sale_title: Optional[str]
    related_message_id: Optional[str]

class NotificationCountResponse(BaseModel):
    total_notifications: int
    unread_notifications: int

# Enhanced Messaging Models
class MessagesWithNotificationStatus(BaseModel):
    messages: List[MessageResponse]
    unread_message_count: int
    total_messages: int

class BulkMarkReadRequest(BaseModel):
    message_ids: List[int]
    conversation_id: Optional[int] = None

class BulkMarkReadResponse(BaseModel):
    marked_count: int
    updated_notifications: List[int]

class MessageNotificationCounts(BaseModel):
    unread_message_notifications: int
    total_message_notifications: int
    last_updated: datetime

class ConversationSummary(BaseModel):
    conversation_id: str
    other_user_id: str
    other_username: str
    last_message: Optional[str]
    last_message_time: Optional[datetime]
    unread_count: int
    total_messages: int

class ConversationSummariesResponse(BaseModel):
    conversations: List[ConversationSummary]
    total_unread: int

# Token blacklist for logout functionality
token_blacklist = set()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_text(json.dumps(message))
            except:
                # Connection closed, remove it
                self.disconnect(user_id)

    async def broadcast(self, message: dict):
        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except:
                # Connection closed, remove it
                self.disconnect(user_id)

manager = ConnectionManager()

# WebSocket event models
class WebSocketEvent(BaseModel):
    type: str
    data: dict

# Conversation helper functions
def get_or_create_conversation(db: Session, yard_sale_id: str, user1_id: str, user2_id: str) -> Conversation:
    """Get existing conversation or create a new one between two users for a yard sale"""
    # Ensure consistent ordering (smaller ID first)
    participant1_id = min(user1_id, user2_id)
    participant2_id = max(user1_id, user2_id)
    
    # Look for existing conversation
    conversation = db.query(Conversation).filter(
        Conversation.yard_sale_id == yard_sale_id,
        Conversation.participant1_id == participant1_id,
        Conversation.participant2_id == participant2_id
    ).first()
    
    if not conversation:
        # Create new conversation
        conversation = Conversation(
            yard_sale_id=yard_sale_id,
            participant1_id=participant1_id,
            participant2_id=participant2_id,
            created_at=get_mountain_time(),
            updated_at=get_mountain_time()
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    else:
        # Update the conversation's updated_at timestamp
        conversation.updated_at = get_mountain_time()
        db.commit()
    
    return conversation

# Notification helper functions
def create_notification(
    db: Session,
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    related_user_id: Optional[str] = None,
    related_yard_sale_id: Optional[str] = None,
    related_message_id: Optional[str] = None
):
    """Create a notification for a user"""
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        related_user_id=related_user_id,
        related_yard_sale_id=related_yard_sale_id,
        related_message_id=related_message_id
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    # Send real-time WebSocket notification
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, schedule the coroutine
            asyncio.create_task(send_websocket_notification(user_id, notification))
        else:
            # If we're not in an async context, run it
            loop.run_until_complete(send_websocket_notification(user_id, notification))
    except:
        # If WebSocket fails, continue without error
        pass
    
    return notification

async def send_websocket_notification(user_id: str, notification: Notification):
    """Send real-time notification via WebSocket"""
    websocket_message = {
        "type": "new_notification",
        "data": {
            "notification": {
                "id": notification.id,
                "type": notification.type,
                "title": notification.title,
                "message": notification.message,
                "created_at": notification.created_at.isoformat(),
                "is_read": notification.is_read
            }
        }
    }
    
    await manager.send_personal_message(websocket_message, user_id)

# Authentication utility functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    # Ensure password is not longer than 72 bytes (bcrypt limitation)
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        plain_password = password_bytes[:72].decode('utf-8', errors='ignore')
    
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        # Fallback: truncate to 72 characters (not bytes) if still failing
        if len(plain_password) > 72:
            plain_password = plain_password[:72]
        return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    # Ensure password is not longer than 72 bytes (bcrypt limitation)
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode('utf-8', errors='ignore')
    
    try:
        return pwd_context.hash(password)
    except Exception as e:
        # Fallback: truncate to 72 characters (not bytes) if still failing
        if len(password) > 72:
            password = password[:72]
        return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_username(db: Session, username: str):
    """Get user by username or email"""
    return db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()

def get_user_by_id(db: Session, user_id: str):
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()

def authenticate_user(db: Session, username: str, password: str):
    """Authenticate a user"""
    user = get_user_by_username(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        # Check if token is blacklisted (logged out)
        if token in token_blacklist:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)):
    """Get current user and verify they have admin permissions"""
    if current_user.permissions != UserPermission.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def get_current_moderator_or_admin_user(current_user: User = Depends(get_current_active_user)):
    """Get current user and verify they have moderator or admin permissions"""
    if current_user.permissions not in [UserPermission.MODERATOR.value, UserPermission.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator or admin access required"
        )
    return current_user

# Root endpoint
@app.get("/", response_model=dict)
async def root():
    """Welcome endpoint with API information"""
    return {
        "message": "Welcome to FastAPI Test Application",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

# Health check endpoint
@app.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

# Authentication endpoints
@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    
    # Check if username already exists
    if get_user_by_username(db, user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    if get_user_by_username(db, user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    
    # Extract location data
    city = user.location.city if user.location else None
    state = user.location.state if user.location else None
    zip_code = user.location.zip if user.location else None
    
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        city=city,
        state=state,
        zip_code=zip_code,
        bio=user.bio,
        is_active=True,
        permissions=user.permissions.value
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Return user without password
    return UserResponse(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        full_name=db_user.full_name,
        phone_number=db_user.phone_number,
        city=db_user.city,
        state=db_user.state,
        zip_code=db_user.zip_code,
        bio=db_user.bio,
        is_active=db_user.is_active,
        permissions=UserPermission(db_user.permissions),
        created_at=db_user.created_at,
        updated_at=db_user.updated_at
    )

@app.post("/api/login", response_model=Token)
async def login_user(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user and return access token"""
    user = authenticate_user(db, user_credentials.username, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
    }

@app.post("/logout", status_code=status.HTTP_200_OK)
async def logout_user(current_user: User = Depends(get_current_active_user)):
    """Logout user by blacklisting their token"""
    # Note: In a real application, you'd need to store the token to blacklist it
    # For this example, we'll return a success message
    return {"message": "Successfully logged out"}

@app.get("/api/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        phone_number=current_user.phone_number,
        city=current_user.city,
        state=current_user.state,
        zip_code=current_user.zip_code,
        bio=current_user.bio,
        is_active=current_user.is_active,
        permissions=UserPermission(current_user.permissions),
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )

@app.put("/me/password")
async def update_password(
    password_data: PasswordUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user password"""
    # Verify email matches the authenticated user
    if password_data.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email does not match the authenticated user's email"
        )
    
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Hash new password
    new_hashed_password = get_password_hash(password_data.new_password)
    
    # Update password in database
    current_user.hashed_password = new_hashed_password
    current_user.updated_at = get_mountain_time()
    db.commit()
    
    return {"message": "Password updated successfully"}

@app.put("/reset-password")
async def reset_password(
    password_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """Reset password using email address (for forgot password scenario)"""
    # Validate that new password and confirm password match
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirm password do not match"
        )
    
    # Find user by email
    user = db.query(User).filter(User.email == password_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email address"
        )
    
    # Hash new password
    new_hashed_password = get_password_hash(password_data.new_password)
    
    # Update password in database
    user.hashed_password = new_hashed_password
    user.updated_at = get_mountain_time()
    db.commit()
    
    return {"message": "Password reset successfully"}

# GET all items (protected route)
@app.get("/items", response_model=List[ItemResponse])
async def get_items(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get all items for the current user"""
    user_items = db.query(Item).filter(Item.owner_id == current_user.id).all()
    return user_items

# GET item by ID (protected route)
@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get a specific item by ID (only if owned by current user)"""
    item = db.query(Item).filter(
        Item.id == item_id, 
        Item.owner_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found"
        )
    
    return item

# POST create new item (protected route)
@app.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Create a new item"""
    db_item = Item(
        name=item.name,
        description=item.description,
        price=item.price,
        is_available=item.is_available,
        owner_id=current_user.id
    )
    
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    return db_item

# PUT update item (protected route)
@app.put("/items/{item_id}", response_model=ItemResponse)
async def update_item(item_id: str, item_update: ItemUpdate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Update an existing item (only if owned by current user)"""
    item = db.query(Item).filter(
        Item.id == item_id, 
        Item.owner_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found"
        )
    
    # Update only provided fields
    update_data = item_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    db.commit()
    db.refresh(item)
    
    return item

# DELETE item (protected route)
@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Delete an item (only if owned by current user)"""
    item = db.query(Item).filter(
        Item.id == item_id, 
        Item.owner_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found"
        )
    
    db.delete(item)
    db.commit()
    
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

# GET items with query parameters (protected route)
@app.get("/items/search/", response_model=List[ItemResponse])
async def search_items(
    name: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    is_available: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Search items with query parameters (only user's items)"""
    # Start with user's items only
    query = db.query(Item).filter(Item.owner_id == current_user.id)
    
    if name:
        query = query.filter(Item.name.ilike(f"%{name}%"))
    
    if min_price is not None:
        query = query.filter(Item.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Item.price <= max_price)
    
    if is_available is not None:
        query = query.filter(Item.is_available == is_available)
    
    return query.all()

# Utility Endpoints
@app.get("/payment-methods", response_model=List[str])
async def get_payment_methods():
    """Get list of available payment methods"""
    return get_standard_payment_methods()

# Yard Sale Endpoints
@app.post("/yard-sales", response_model=YardSaleResponse, status_code=status.HTTP_201_CREATED)
async def create_yard_sale(yard_sale: YardSaleCreate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Create a new yard sale"""
    db_yard_sale = YardSale(
        title=yard_sale.title,
        description=yard_sale.description,
        start_date=yard_sale.start_date,
        end_date=yard_sale.end_date,
        start_time=yard_sale.start_time,
        end_time=yard_sale.end_time,
        address=yard_sale.address,
        city=yard_sale.city,
        state=yard_sale.state.upper(),  # Store as uppercase
        zip_code=yard_sale.zip_code,
        latitude=yard_sale.latitude,
        longitude=yard_sale.longitude,
        contact_name=yard_sale.contact_name,
        contact_phone=yard_sale.contact_phone,
        contact_email=yard_sale.contact_email,
        venmo_url=yard_sale.venmo_url,
        allow_messages=yard_sale.allow_messages,
        categories=yard_sale.categories,
        price_range=yard_sale.price_range,
        payment_methods=yard_sale.payment_methods,
        photos=yard_sale.photos,
        featured_image=yard_sale.featured_image,
        status=yard_sale.status.value if yard_sale.status else "active",
        owner_id=current_user.id
    )
    
    db.add(db_yard_sale)
    db.commit()
    db.refresh(db_yard_sale)
    
    # Get comment count
    comment_count = db.query(Comment).filter(Comment.yard_sale_id == db_yard_sale.id).count()
    
    return YardSaleResponse(
        **db_yard_sale.__dict__,
        owner_username=current_user.username,
        comment_count=comment_count
    )

@app.get("/yard-sales", response_model=List[YardSaleResponse])
async def get_yard_sales(
    skip: int = 0,
    limit: int = 100,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
    category: Optional[str] = None,
    price_range: Optional[str] = None,
    status: Optional[YardSaleStatus] = None,
    include_visited_status: bool = False,
    current_user: Optional[User] = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all active yard sales with optional filtering"""
    query = db.query(YardSale).filter(YardSale.is_active == True)
    
    # Apply filters
    if city:
        query = query.filter(YardSale.city.ilike(f"%{city}%"))
    if state:
        query = query.filter(YardSale.state == state.upper())
    if zip_code:
        query = query.filter(YardSale.zip_code == zip_code)
    if category:
        query = query.filter(YardSale.categories.contains([category]))
    if price_range:
        query = query.filter(YardSale.price_range == price_range)
    if status:
        query = query.filter(YardSale.status == status.value)
    
    # Order by start date (upcoming sales first)
    query = query.order_by(YardSale.start_date.asc())
    
    yard_sales = query.offset(skip).limit(limit).all()
    
    # Build response with comment counts and visited status
    result = []
    for yard_sale in yard_sales:
        comment_count = db.query(Comment).filter(Comment.yard_sale_id == yard_sale.id).count()
        
        # Get visited status if requested and user is authenticated
        is_visited = None
        visit_count = None
        last_visited = None
        
        if include_visited_status and current_user:
            visit = db.query(VisitedYardSale).filter(
                VisitedYardSale.user_id == current_user.id,
                VisitedYardSale.yard_sale_id == yard_sale.id
            ).first()
            
            if visit:
                is_visited = True
                visit_count = visit.visit_count
                last_visited = visit.last_visited
            else:
                is_visited = False
        
        result.append(YardSaleResponse(
            **yard_sale.__dict__,
            owner_username=yard_sale.owner.username,
            comment_count=comment_count,
            is_visited=is_visited,
            visit_count=visit_count,
            last_visited=last_visited
        ))
    
    return result

@app.get("/yard-sales/{yard_sale_id}", response_model=YardSaleResponse)
async def get_yard_sale(yard_sale_id: str, db: Session = Depends(get_db)):
    """Get a specific yard sale by ID"""
    yard_sale = db.query(YardSale).filter(YardSale.id == yard_sale_id).first()
    
    if not yard_sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Yard sale with id {yard_sale_id} not found"
        )
    
    # Get comment count
    comment_count = db.query(Comment).filter(Comment.yard_sale_id == yard_sale.id).count()
    
    return YardSaleResponse(
        **yard_sale.__dict__,
        owner_username=yard_sale.owner.username,
        comment_count=comment_count
    )

@app.put("/yard-sales/{yard_sale_id}", response_model=YardSaleResponse)
async def update_yard_sale(
    yard_sale_id: str, 
    yard_sale_update: YardSaleUpdate, 
    current_user: User = Depends(get_current_active_user), 
    db: Session = Depends(get_db)
):
    """Update a yard sale (only if owned by current user)"""
    yard_sale = db.query(YardSale).filter(
        YardSale.id == yard_sale_id, 
        YardSale.owner_id == current_user.id
    ).first()
    
    if not yard_sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Yard sale with id {yard_sale_id} not found"
        )
    
    # Update only provided fields
    update_data = yard_sale_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "state" and value:
            value = value.upper()  # Store state as uppercase
        elif field == "status" and value:
            value = value.value if hasattr(value, 'value') else value  # Handle enum
        setattr(yard_sale, field, value)
    
    db.commit()
    db.refresh(yard_sale)
    
    # Get comment count
    comment_count = db.query(Comment).filter(Comment.yard_sale_id == yard_sale.id).count()
    
    return YardSaleResponse(
        **yard_sale.__dict__,
        owner_username=yard_sale.owner.username,
        comment_count=comment_count
    )

@app.delete("/yard-sales/{yard_sale_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_yard_sale(
    yard_sale_id: str, 
    current_user: User = Depends(get_current_active_user), 
    db: Session = Depends(get_db)
):
    """Delete a yard sale (only if owned by current user)"""
    yard_sale = db.query(YardSale).filter(
        YardSale.id == yard_sale_id, 
        YardSale.owner_id == current_user.id
    ).first()
    
    if not yard_sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Yard sale with id {yard_sale_id} not found"
        )
    
    db.delete(yard_sale)
    db.commit()
    
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

@app.get("/yard-sales/search/nearby", response_model=List[YardSaleResponse])
async def search_nearby_yard_sales(
    zip_code: str,
    radius_miles: int = 10,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Search for yard sales near a ZIP code"""
    # For now, we'll do a simple ZIP code match
    # In a real application, you'd use geocoding and distance calculations
    query = db.query(YardSale).filter(
        YardSale.is_active == True,
        YardSale.zip_code == zip_code
    ).order_by(YardSale.start_date.asc())
    
    yard_sales = query.offset(skip).limit(limit).all()
    
    # Build response with comment counts
    result = []
    for yard_sale in yard_sales:
        comment_count = db.query(Comment).filter(Comment.yard_sale_id == yard_sale.id).count()
        result.append(YardSaleResponse(
            **yard_sale.__dict__,
            owner_username=yard_sale.owner.username,
            comment_count=comment_count
        ))
    
    return result

# Comment Endpoints
@app.post("/yard-sales/{yard_sale_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    yard_sale_id: str,
    comment: CommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a comment to a yard sale"""
    # Check if yard sale exists
    yard_sale = db.query(YardSale).filter(YardSale.id == yard_sale_id).first()
    if not yard_sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Yard sale with id {yard_sale_id} not found"
        )
    
    db_comment = Comment(
        content=comment.content,
        yard_sale_id=yard_sale_id,
        user_id=current_user.id
    )
    
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    
    return CommentResponse(
        **db_comment.__dict__,
        username=current_user.username
    )

@app.get("/yard-sales/{yard_sale_id}/comments", response_model=List[CommentResponse])
async def get_comments(yard_sale_id: str, db: Session = Depends(get_db)):
    """Get all comments for a yard sale"""
    # Check if yard sale exists
    yard_sale = db.query(YardSale).filter(YardSale.id == yard_sale_id).first()
    if not yard_sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Yard sale with id {yard_sale_id} not found"
        )
    
    comments = db.query(Comment).filter(
        Comment.yard_sale_id == yard_sale_id
    ).order_by(Comment.created_at.asc()).all()
    
    return [CommentResponse(**comment.__dict__, username=comment.user.username) for comment in comments]

@app.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a comment (only if owned by current user)"""
    comment = db.query(Comment).filter(
        Comment.id == comment_id,
        Comment.user_id == current_user.id
    ).first()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment with id {comment_id} not found"
        )
    
    db.delete(comment)
    db.commit()
    
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

# ============================================================================
# MESSAGE ENDPOINTS
# ============================================================================

# Send a message to yard sale owner
@app.post("/yard-sales/{yard_sale_id}/messages", response_model=MessageResponse)
async def send_message(
    yard_sale_id: str,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send a private message to the yard sale owner"""
    # Check if yard sale exists
    yard_sale = db.query(YardSale).filter(YardSale.id == yard_sale_id).first()
    if not yard_sale:
        raise HTTPException(status_code=404, detail="Yard sale not found")
    
    # Determine recipient - use provided recipient_id or default to yard sale owner
    recipient_id = message_data.recipient_id if message_data.recipient_id else yard_sale.owner_id
    recipient = db.query(User).filter(User.id == recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    # Check if yard sale allows messages
    if not yard_sale.allow_messages:
        raise HTTPException(status_code=400, detail="This yard sale does not allow messages")
    
    # Get or create conversation between the two users
    conversation = get_or_create_conversation(db, yard_sale_id, current_user.id, recipient_id)
    
    # Create the message
    message = Message(
        content=message_data.content,
        conversation_id=conversation.id,
        sender_id=current_user.id,
        recipient_id=recipient_id
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # Create notification for the recipient (only if not sending to self)
    if recipient_id != current_user.id:
        create_notification(
            db=db,
            user_id=recipient_id,
            notification_type="message",
            title=f"New message from {current_user.username}",
            message=f"You received a message: \"{message_data.content[:100]}{'...' if len(message_data.content) > 100 else ''}\"",
            related_user_id=current_user.id,
            related_yard_sale_id=yard_sale_id,
            related_message_id=message.id
        )
    
    return MessageResponse(
        id=message.id,
        content=message.content,
        is_read=message.is_read,
        created_at=message.created_at,
        conversation_id=message.conversation_id,
        sender_id=message.sender_id,
        sender_username=current_user.username,
        recipient_id=message.recipient_id,
        recipient_username=recipient.username
    )

# Get messages for a specific yard sale (conversation)
@app.get("/yard-sales/{yard_sale_id}/messages", response_model=List[MessageResponse])
async def get_yard_sale_messages(
    yard_sale_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all messages for a specific yard sale (only participants can see)"""
    # Check if yard sale exists
    yard_sale = db.query(YardSale).filter(YardSale.id == yard_sale_id).first()
    if not yard_sale:
        raise HTTPException(status_code=404, detail="Yard sale not found")
    
    # Get conversations for this yard sale where current user is a participant
    conversations = db.query(Conversation).filter(
        Conversation.yard_sale_id == yard_sale_id,
        (Conversation.participant1_id == current_user.id) | (Conversation.participant2_id == current_user.id)
    ).all()
    
    if not conversations:
        return []
    
    # Get all messages from these conversations
    conversation_ids = [conv.id for conv in conversations]
    messages = db.query(Message).filter(
        Message.conversation_id.in_(conversation_ids)
    ).order_by(Message.created_at.asc()).all()
    
    # Get sender and recipient usernames
    result = []
    for message in messages:
        sender = db.query(User).filter(User.id == message.sender_id).first()
        recipient = db.query(User).filter(User.id == message.recipient_id).first()
        
        result.append(MessageResponse(
            id=message.id,
            content=message.content,
            is_read=message.is_read,
            created_at=message.created_at,
            conversation_id=message.conversation_id,
            sender_id=message.sender_id,
            sender_username=sender.username,
            recipient_id=message.recipient_id,
            recipient_username=recipient.username
        ))
    
    return result

# Get all conversations for current user
@app.get("/conversations", response_model=List[ConversationResponse])
async def get_user_conversations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all conversations for the current user"""
    # Get conversations where user is either participant1 or participant2
    conversations = db.query(Conversation).filter(
        (Conversation.participant1_id == current_user.id) | 
        (Conversation.participant2_id == current_user.id)
    ).order_by(Conversation.updated_at.desc()).all()
    
    result = []
    for conv in conversations:
        # Get yard sale info
        yard_sale = db.query(YardSale).filter(YardSale.id == conv.yard_sale_id).first()
        
        # Get participant info
        participant1 = db.query(User).filter(User.id == conv.participant1_id).first()
        participant2 = db.query(User).filter(User.id == conv.participant2_id).first()
        
        # Get last message
        last_message = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).order_by(Message.created_at.desc()).first()
        
        # Count unread messages for current user
        unread_count = db.query(Message).filter(
            Message.conversation_id == conv.id,
            Message.recipient_id == current_user.id,
            Message.is_read == False
        ).count()
        
        result.append(ConversationResponse(
            id=conv.id,
            yard_sale_id=conv.yard_sale_id,
            yard_sale_title=yard_sale.title if yard_sale else "Unknown",
            participant1_id=conv.participant1_id,
            participant1_username=participant1.username,
            participant2_id=conv.participant2_id,
            participant2_username=participant2.username,
            last_message=last_message.content if last_message else None,
            last_message_time=last_message.created_at if last_message else None,
            unread_count=unread_count,
            created_at=conv.created_at,
            updated_at=conv.updated_at
        ))
    
    return result

# Get conversation summaries with unread counts
@app.get("/conversations/summaries", response_model=ConversationSummariesResponse)
async def get_conversation_summaries(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get conversation summaries with unread counts and last message info"""
    # Get conversations where user is either participant1 or participant2
    conversations = db.query(Conversation).filter(
        (Conversation.participant1_id == current_user.id) | 
        (Conversation.participant2_id == current_user.id)
    ).order_by(Conversation.updated_at.desc()).all()
    
    result = []
    total_unread = 0
    
    for conv in conversations:
        # Determine the other user
        if conv.participant1_id == current_user.id:
            other_user_id = conv.participant2_id
        else:
            other_user_id = conv.participant1_id
        
        # Get other user info
        other_user = db.query(User).filter(User.id == other_user_id).first()
        
        # Get last message
        last_message = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).order_by(Message.created_at.desc()).first()
        
        # Count unread messages for current user
        unread_count = db.query(Message).filter(
            Message.conversation_id == conv.id,
            Message.recipient_id == current_user.id,
            Message.is_read == False
        ).count()
        
        # Count total messages in conversation
        total_messages = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).count()
        
        total_unread += unread_count
        
        result.append(ConversationSummary(
            conversation_id=conv.id,
            other_user_id=other_user_id,
            other_username=other_user.username if other_user else "Unknown",
            last_message=last_message.content if last_message else None,
            last_message_time=last_message.created_at if last_message else None,
            unread_count=unread_count,
            total_messages=total_messages
        ))
    
    return ConversationSummariesResponse(
        conversations=result,
        total_unread=total_unread
    )

# WebSocket endpoint for real-time message updates
@app.websocket("/ws/messages/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time message notifications"""
    # Verify user exists
    db = next(get_db())
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        await websocket.close(code=4004, reason="User not found")
        return
    
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            # For now, just echo back (can be extended for other real-time features)
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(user_id)

# Get messages for a specific conversation
@app.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all messages for a specific conversation"""
    # Check if user is participant in this conversation
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        (Conversation.participant1_id == current_user.id) | 
        (Conversation.participant2_id == current_user.id)
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")
    
    # Get messages for this conversation
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()
    
    result = []
    for message in messages:
        sender = db.query(User).filter(User.id == message.sender_id).first()
        recipient = db.query(User).filter(User.id == message.recipient_id).first()
        
        result.append(MessageResponse(
            id=message.id,
            content=message.content,
            is_read=message.is_read,
            created_at=message.created_at,
            conversation_id=message.conversation_id,
            sender_id=message.sender_id,
            sender_username=sender.username,
            recipient_id=message.recipient_id,
            recipient_username=recipient.username
        ))
    
    return result

# Send a message in a conversation
@app.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_conversation_message(
    conversation_id: str,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send a message in an existing conversation"""
    # Check if conversation exists and user is a participant
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Check if current user is a participant in this conversation
    if current_user.id not in [conversation.participant1_id, conversation.participant2_id]:
        raise HTTPException(status_code=403, detail="You are not a participant in this conversation")
    
    # Determine the recipient (the other participant)
    recipient_id = conversation.participant2_id if current_user.id == conversation.participant1_id else conversation.participant1_id
    
    # Create the message
    message = Message(
        content=message_data.content,
        sender_id=current_user.id,
        recipient_id=recipient_id,
        conversation_id=conversation_id,
        is_read=False
    )
    
    db.add(message)
    
    # Update conversation's updated_at timestamp
    conversation.updated_at = get_mountain_time()
    
    db.commit()
    db.refresh(message)
    
    # Get recipient info for response
    recipient = db.query(User).filter(User.id == recipient_id).first()
    
    # Create notification for the recipient (only if not sending to self)
    if recipient_id != current_user.id:
        create_notification(
            db=db,
            user_id=recipient_id,
            notification_type="message",
            title=f"New message from {current_user.username}",
            message=f"You received a message: \"{message_data.content[:100]}{'...' if len(message_data.content) > 100 else ''}\"",
            related_user_id=current_user.id,
            related_yard_sale_id=conversation.yard_sale_id,
            related_message_id=message.id
        )
    
    return MessageResponse(
        id=message.id,
        content=message.content,
        is_read=message.is_read,
        created_at=message.created_at,
        conversation_id=message.conversation_id,
        sender_id=message.sender_id,
        sender_username=current_user.username,
        recipient_id=message.recipient_id,
        recipient_username=recipient.username
    )

# Get all messages for current user (inbox)
@app.get("/messages", response_model=MessagesWithNotificationStatus)
async def get_user_messages(
    include_notification_status: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all messages for the current user with optional notification status"""
    messages = db.query(Message).filter(
        (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id)
    ).order_by(Message.created_at.desc()).all()
    
    result = []
    unread_count = 0
    
    for message in messages:
        sender = db.query(User).filter(User.id == message.sender_id).first()
        recipient = db.query(User).filter(User.id == message.recipient_id).first()
        
        # Get notification info if requested
        notification_id = None
        has_unread_notification = False
        
        if include_notification_status:
            notification = db.query(Notification).filter(
                Notification.related_message_id == message.id,
                Notification.user_id == current_user.id
            ).first()
            
            if notification:
                notification_id = notification.id
                has_unread_notification = not notification.is_read
        
        # Count unread messages (received but not read)
        if message.recipient_id == current_user.id and not message.is_read:
            unread_count += 1
        
        result.append(MessageResponse(
            id=message.id,
            content=message.content,
            is_read=message.is_read,
            created_at=message.created_at,
            conversation_id=message.conversation_id,
            sender_id=message.sender_id,
            sender_username=sender.username,
            recipient_id=message.recipient_id,
            recipient_username=recipient.username,
            notification_id=notification_id,
            has_unread_notification=has_unread_notification
        ))
    
    return MessagesWithNotificationStatus(
        messages=result,
        unread_message_count=unread_count,
        total_messages=len(result)
    )

# Bulk mark messages as read
@app.post("/messages/mark-read", response_model=BulkMarkReadResponse)
async def bulk_mark_messages_read(
    request: BulkMarkReadRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark multiple messages as read in one call"""
    marked_count = 0
    updated_notifications = []
    
    if request.conversation_id:
        # Mark all messages in conversation as read
        messages = db.query(Message).filter(
            Message.conversation_id == request.conversation_id,
            Message.recipient_id == current_user.id,
            Message.is_read == False
        ).all()
        
        for message in messages:
            message.is_read = True
            marked_count += 1
            
            # Mark related notification as read
            notification = db.query(Notification).filter(
                Notification.related_message_id == message.id,
                Notification.user_id == current_user.id,
                Notification.is_read == False
            ).first()
            
            if notification:
                notification.is_read = True
                notification.read_at = get_mountain_time()
                updated_notifications.append(notification.id)
    
    else:
        # Mark specific messages as read
        for message_id in request.message_ids:
            message = db.query(Message).filter(
                Message.id == message_id,
                Message.recipient_id == current_user.id,
                Message.is_read == False
            ).first()
            
            if message:
                message.is_read = True
                marked_count += 1
                
                # Mark related notification as read
                notification = db.query(Notification).filter(
                    Notification.related_message_id == message.id,
                    Notification.user_id == current_user.id,
                    Notification.is_read == False
                ).first()
                
                if notification:
                    notification.is_read = True
                    notification.read_at = get_mountain_time()
                    updated_notifications.append(notification.id)
    
    db.commit()
    
    return BulkMarkReadResponse(
        marked_count=marked_count,
        updated_notifications=updated_notifications
    )

# Get unread messages count
@app.get("/messages/unread-count")
async def get_unread_messages_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get count of unread messages for current user"""
    unread_count = db.query(Message).filter(
        Message.recipient_id == current_user.id,
        Message.is_read == False
    ).count()
    
    return {"unread_count": unread_count}

# Mark message as read
@app.put("/messages/{message_id}/read")
async def mark_message_as_read(
    message_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark a message as read (only recipient can mark as read)"""
    message = db.query(Message).filter(Message.id == message_id).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if message.recipient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to mark this message as read")
    
    message.is_read = True
    db.commit()
    
    return {"message": "Message marked as read"}

# Delete message (sender or recipient can delete)
@app.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a message (sender or recipient can delete)"""
    message = db.query(Message).filter(Message.id == message_id).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if message.sender_id != current_user.id and message.recipient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this message")
    
    db.delete(message)
    db.commit()
    
    return {"message": "Message deleted successfully"}

# General message sending endpoint (alternative to yard-sale specific)
@app.post("/messages", response_model=MessageResponse)
async def send_message_general(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send a message - requires either yard_sale_id or conversation_id in the request body"""
    if not message_data.yard_sale_id and not message_data.conversation_id:
        raise HTTPException(
            status_code=400, 
            detail="Either yard_sale_id or conversation_id must be provided"
        )
    
    if message_data.yard_sale_id and message_data.conversation_id:
        raise HTTPException(
            status_code=400, 
            detail="Provide either yard_sale_id or conversation_id, not both"
        )
    
    if message_data.yard_sale_id:
        # Use the existing yard sale messaging logic
        yard_sale = db.query(YardSale).filter(YardSale.id == message_data.yard_sale_id).first()
        if not yard_sale:
            raise HTTPException(status_code=404, detail="Yard sale not found")
        
        # Get or create conversation
        conversation = get_or_create_conversation(db, message_data.yard_sale_id, current_user.id, yard_sale.owner_id)
        
        # Determine recipient
        recipient_id = yard_sale.owner_id if current_user.id != yard_sale.owner_id else current_user.id
        
        # Create message
        message = Message(
            content=message_data.content,
            sender_id=current_user.id,
            recipient_id=recipient_id,
            conversation_id=conversation.id,
            is_read=False
        )
        
        db.add(message)
        conversation.updated_at = get_mountain_time()
        db.commit()
        db.refresh(message)
        
        # Get recipient info
        recipient = db.query(User).filter(User.id == recipient_id).first()
        
        # Create notification for the recipient (only if not sending to self)
        if recipient_id != current_user.id:
            create_notification(
                db=db,
                user_id=recipient_id,
                notification_type="message",
                title=f"New message from {current_user.username}",
                message=f"You received a message: \"{message_data.content[:100]}{'...' if len(message_data.content) > 100 else ''}\"",
                related_user_id=current_user.id,
                related_yard_sale_id=message_data.yard_sale_id,
                related_message_id=message.id
            )
        
        return MessageResponse(
            id=message.id,
            content=message.content,
            is_read=message.is_read,
            created_at=message.created_at,
            conversation_id=message.conversation_id,
            sender_id=message.sender_id,
            sender_username=current_user.username,
            recipient_id=message.recipient_id,
            recipient_username=recipient.username
        )
    
    else:  # conversation_id provided
        # Use the conversation messaging logic
        conversation = db.query(Conversation).filter(Conversation.id == message_data.conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Check if current user is a participant
        if current_user.id not in [conversation.participant1_id, conversation.participant2_id]:
            raise HTTPException(status_code=403, detail="You are not a participant in this conversation")
        
        # Determine recipient
        recipient_id = conversation.participant2_id if current_user.id == conversation.participant1_id else conversation.participant1_id
        
        # Create message
        message = Message(
            content=message_data.content,
            sender_id=current_user.id,
            recipient_id=recipient_id,
            conversation_id=conversation.id,
            is_read=False
        )
        
        db.add(message)
        conversation.updated_at = get_mountain_time()
        db.commit()
        db.refresh(message)
        
        # Get recipient info
        recipient = db.query(User).filter(User.id == recipient_id).first()
        
        # Create notification for the recipient (only if not sending to self)
        if recipient_id != current_user.id:
            create_notification(
                db=db,
                user_id=recipient_id,
                notification_type="message",
                title=f"New message from {current_user.username}",
                message=f"You received a message: \"{message_data.content[:100]}{'...' if len(message_data.content) > 100 else ''}\"",
                related_user_id=current_user.id,
                related_yard_sale_id=conversation.yard_sale_id,
                related_message_id=message.id
            )
        
        return MessageResponse(
            id=message.id,
            content=message.content,
            is_read=message.is_read,
            created_at=message.created_at,
            conversation_id=message.conversation_id,
            sender_id=message.sender_id,
            sender_username=current_user.username,
            recipient_id=message.recipient_id,
            recipient_username=recipient.username
        )

# ============================================================================
# TRUST SYSTEM ENDPOINTS
# ============================================================================

# User Rating and Review Endpoints
@app.post("/users/{user_id}/ratings", response_model=UserRatingResponse)
async def create_user_rating(
    user_id: str,
    rating_data: UserRatingCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Rate and review a user"""
    # Check if user exists
    rated_user = db.query(User).filter(User.id == user_id).first()
    if not rated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-rating
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot rate yourself")
    
    # Check if user already rated this person
    existing_rating = db.query(UserRating).filter(
        UserRating.reviewer_id == current_user.id,
        UserRating.rated_user_id == user_id
    ).first()
    
    if existing_rating:
        raise HTTPException(status_code=400, detail="You have already rated this user")
    
    # Validate yard sale if provided
    yard_sale = None
    if rating_data.yard_sale_id:
        yard_sale = db.query(YardSale).filter(YardSale.id == rating_data.yard_sale_id).first()
        if not yard_sale:
            raise HTTPException(status_code=404, detail="Yard sale not found")
    
    # Create rating
    rating = UserRating(
        rating=rating_data.rating,
        review_text=rating_data.review_text,
        reviewer_id=current_user.id,
        rated_user_id=user_id,
        yard_sale_id=rating_data.yard_sale_id
    )
    
    db.add(rating)
    db.commit()
    db.refresh(rating)
    
    # Create notification for the rated user
    create_notification(
        db=db,
        user_id=user_id,
        notification_type="rating",
        title=f"New rating from {current_user.username}",
        message=f"You received a {rating.rating}-star rating: \"{rating.review_text[:100] if rating.review_text else 'No review text'}{'...' if rating.review_text and len(rating.review_text) > 100 else ''}\"",
        related_user_id=current_user.id,
        related_yard_sale_id=rating.yard_sale_id
    )
    
    return UserRatingResponse(
        id=rating.id,
        rating=rating.rating,
        review_text=rating.review_text,
        created_at=rating.created_at,
        reviewer_id=rating.reviewer_id,
        reviewer_username=current_user.username,
        rated_user_id=rating.rated_user_id,
        rated_user_username=rated_user.username,
        yard_sale_id=rating.yard_sale_id,
        yard_sale_title=yard_sale.title if yard_sale else None
    )

@app.get("/api/users/{user_id}/ratings", response_model=List[UserRatingResponse])
async def get_user_ratings(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get all ratings for a user"""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    ratings = db.query(UserRating).filter(UserRating.rated_user_id == user_id).all()
    
    result = []
    for rating in ratings:
        yard_sale = None
        if rating.yard_sale_id:
            yard_sale = db.query(YardSale).filter(YardSale.id == rating.yard_sale_id).first()
        
        result.append(UserRatingResponse(
            id=rating.id,
            rating=rating.rating,
            review_text=rating.review_text,
            created_at=rating.created_at,
            reviewer_id=rating.reviewer_id,
            reviewer_username=rating.reviewer.username,
            rated_user_id=rating.rated_user_id,
            rated_user_username=rating.rated_user.username,
            yard_sale_id=rating.yard_sale_id,
            yard_sale_title=yard_sale.title if yard_sale else None
        ))
    
    return result

@app.get("/users/{user_id}/ratings", response_model=List[UserRatingResponse])
async def get_user_ratings_by_id(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all ratings for a user by ID (authenticated endpoint)"""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    ratings = db.query(UserRating).filter(UserRating.rated_user_id == user_id).all()
    
    result = []
    for rating in ratings:
        yard_sale = None
        if rating.yard_sale_id:
            yard_sale = db.query(YardSale).filter(YardSale.id == rating.yard_sale_id).first()
        
        result.append(UserRatingResponse(
            id=rating.id,
            rating=rating.rating,
            review_text=rating.review_text,
            created_at=rating.created_at,
            reviewer_id=rating.reviewer_id,
            reviewer_username=rating.reviewer.username,
            rated_user_id=rating.rated_user_id,
            rated_user_username=rating.rated_user.username,
            yard_sale_id=rating.yard_sale_id,
            yard_sale_title=yard_sale.title if yard_sale else None
        ))
    
    return result

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user by ID (basic user information)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        city=user.city,
        state=user.state,
        zip_code=user.zip_code,
        bio=user.bio,
        is_active=user.is_active,
        permissions=UserPermission(user.permissions),
        created_at=user.created_at,
        updated_at=user.updated_at
    )

@app.get("/users/{user_id}/profile", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get user profile with trust metrics"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate average rating
    ratings = db.query(UserRating).filter(UserRating.rated_user_id == user_id).all()
    average_rating = None
    if ratings:
        average_rating = sum(r.rating for r in ratings) / len(ratings)
    
    # Get verification badges
    verifications = db.query(Verification).filter(
        Verification.user_id == user_id,
        Verification.status == "verified"
    ).all()
    verification_badges = [v.verification_type for v in verifications]
    
    return UserProfileResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        city=user.city,
        state=user.state,
        zip_code=user.zip_code,
        bio=user.bio,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        average_rating=average_rating,
        total_ratings=len(ratings),
        verification_badges=verification_badges,
        is_verified=len(verification_badges) > 0
    )

# Report Endpoints
@app.post("/reports", response_model=ReportResponse)
async def create_report(
    report_data: ReportCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a report for a user or yard sale"""
    # Validate reported user if provided
    reported_user = None
    if report_data.reported_user_id:
        reported_user = db.query(User).filter(User.id == report_data.reported_user_id).first()
        if not reported_user:
            raise HTTPException(status_code=404, detail="Reported user not found")
    
    # Validate reported yard sale if provided
    reported_yard_sale = None
    if report_data.reported_yard_sale_id:
        reported_yard_sale = db.query(YardSale).filter(YardSale.id == report_data.reported_yard_sale_id).first()
        if not reported_yard_sale:
            raise HTTPException(status_code=404, detail="Reported yard sale not found")
    
    # Create report
    report = Report(
        report_type=report_data.report_type,
        description=report_data.description,
        reporter_id=current_user.id,
        reported_user_id=report_data.reported_user_id,
        reported_yard_sale_id=report_data.reported_yard_sale_id
    )
    
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return ReportResponse(
        id=report.id,
        report_type=report.report_type,
        description=report.description,
        status=report.status,
        created_at=report.created_at,
        reporter_id=report.reporter_id,
        reporter_username=current_user.username,
        reported_user_id=report.reported_user_id,
        reported_user_username=reported_user.username if reported_user else None,
        reported_yard_sale_id=report.reported_yard_sale_id,
        reported_yard_sale_title=reported_yard_sale.title if reported_yard_sale else None
    )

@app.get("/reports", response_model=List[ReportResponse])
async def get_reports(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all reports (admin only - for now, returns user's own reports)"""
    reports = db.query(Report).filter(Report.reporter_id == current_user.id).all()
    
    result = []
    for report in reports:
        reported_user = None
        if report.reported_user_id:
            reported_user = db.query(User).filter(User.id == report.reported_user_id).first()
        
        reported_yard_sale = None
        if report.reported_yard_sale_id:
            reported_yard_sale = db.query(YardSale).filter(YardSale.id == report.reported_yard_sale_id).first()
        
        result.append(ReportResponse(
            id=report.id,
            report_type=report.report_type,
            description=report.description,
            status=report.status,
            created_at=report.created_at,
            reporter_id=report.reporter_id,
            reporter_username=report.reporter.username,
            reported_user_id=report.reported_user_id,
            reported_user_username=reported_user.username if reported_user else None,
            reported_yard_sale_id=report.reported_yard_sale_id,
            reported_yard_sale_title=reported_yard_sale.title if reported_yard_sale else None
        ))
    
    return result

# Verification Endpoints
@app.post("/verifications", response_model=VerificationResponse)
async def create_verification(
    verification_data: VerificationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Request verification for a user"""
    # Check if verification already exists
    existing_verification = db.query(Verification).filter(
        Verification.user_id == current_user.id,
        Verification.verification_type == verification_data.verification_type
    ).first()
    
    if existing_verification:
        raise HTTPException(status_code=400, detail="Verification request already exists for this type")
    
    # Create verification request
    verification = Verification(
        verification_type=verification_data.verification_type,
        user_id=current_user.id
    )
    
    db.add(verification)
    db.commit()
    db.refresh(verification)
    
    return VerificationResponse(
        id=verification.id,
        verification_type=verification.verification_type,
        status=verification.status,
        verified_at=verification.verified_at,
        created_at=verification.created_at,
        user_id=verification.user_id,
        user_username=current_user.username
    )

@app.get("/verifications", response_model=List[VerificationResponse])
async def get_user_verifications(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all verifications for current user"""
    verifications = db.query(Verification).filter(Verification.user_id == current_user.id).all()
    
    result = []
    for verification in verifications:
        result.append(VerificationResponse(
            id=verification.id,
            verification_type=verification.verification_type,
            status=verification.status,
            verified_at=verification.verified_at,
            created_at=verification.created_at,
            user_id=verification.user_id,
            user_username=current_user.username
        ))
    
    return result

# Additional User Profile Endpoints
@app.get("/api/users/{user_id}", response_model=UserProfileResponse)
async def get_user_by_id(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed user profile by ID with trust metrics"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate average rating
    ratings = db.query(UserRating).filter(UserRating.rated_user_id == user_id).all()
    average_rating = None
    if ratings:
        average_rating = sum(r.rating for r in ratings) / len(ratings)
    
    # Get verification badges
    verifications = db.query(Verification).filter(
        Verification.user_id == user_id,
        Verification.status == "verified"
    ).all()
    verification_badges = [v.verification_type for v in verifications]
    
    return UserProfileResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        city=user.city,
        state=user.state,
        zip_code=user.zip_code,
        bio=user.bio,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        average_rating=average_rating,
        total_ratings=len(ratings),
        verification_badges=verification_badges,
        is_verified=len(verification_badges) > 0
    )

@app.get("/users/{user_id}/verifications", response_model=List[VerificationResponse])
async def get_user_verifications_by_id(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get all verifications for a specific user"""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    verifications = db.query(Verification).filter(Verification.user_id == user_id).all()
    
    result = []
    for verification in verifications:
        result.append(VerificationResponse(
            id=verification.id,
            verification_type=verification.verification_type,
            status=verification.status,
            verified_at=verification.verified_at,
            created_at=verification.created_at,
            user_id=verification.user_id,
            user_username=user.username
        ))
    
    return result

# Alternative Ratings Endpoint (as requested)
@app.post("/ratings", response_model=UserRatingResponse)
async def create_rating(
    rating_data: UserRatingCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new rating/review for a user (alternative endpoint)"""
    # This endpoint requires rated_user_id to be provided in the request body
    # instead of as a path parameter
    
    # Check if rated_user_id is provided
    if not hasattr(rating_data, 'rated_user_id') or not rating_data.rated_user_id:
        raise HTTPException(status_code=400, detail="rated_user_id is required")
    
    rated_user_id = rating_data.rated_user_id
    
    # Check if user exists
    rated_user = db.query(User).filter(User.id == rated_user_id).first()
    if not rated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-rating
    if rated_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot rate yourself")
    
    # Check if user already rated this person
    existing_rating = db.query(UserRating).filter(
        UserRating.reviewer_id == current_user.id,
        UserRating.rated_user_id == rated_user_id
    ).first()
    
    if existing_rating:
        raise HTTPException(status_code=400, detail="You have already rated this user")
    
    # Validate yard sale if provided
    yard_sale = None
    if rating_data.yard_sale_id:
        yard_sale = db.query(YardSale).filter(YardSale.id == rating_data.yard_sale_id).first()
        if not yard_sale:
            raise HTTPException(status_code=404, detail="Yard sale not found")
        
        # Verify yard sale is associated with the rated user
        if yard_sale.owner_id != rated_user_id:
            raise HTTPException(status_code=400, detail="Yard sale is not associated with the rated user")
    
    # Create rating
    rating = UserRating(
        rating=rating_data.rating,
        review_text=rating_data.review_text,
        reviewer_id=current_user.id,
        rated_user_id=rated_user_id,
        yard_sale_id=rating_data.yard_sale_id
    )
    
    db.add(rating)
    db.commit()
    db.refresh(rating)
    
    return UserRatingResponse(
        id=rating.id,
        rating=rating.rating,
        review_text=rating.review_text,
        created_at=rating.created_at,
        reviewer_id=rating.reviewer_id,
        reviewer_username=current_user.username,
        rated_user_id=rating.rated_user_id,
        rated_user_username=rated_user.username,
        yard_sale_id=rating.yard_sale_id,
        yard_sale_title=yard_sale.title if yard_sale else None
    )

# Visit Tracking Endpoints
@app.post("/yard-sales/{yard_sale_id}/visit", response_model=VisitedYardSaleResponse)
async def mark_yard_sale_visited(
    yard_sale_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark a yard sale as visited by the current user"""
    # Check if yard sale exists
    yard_sale = db.query(YardSale).filter(YardSale.id == yard_sale_id).first()
    if not yard_sale:
        raise HTTPException(status_code=404, detail="Yard sale not found")
    
    # Check if user has already visited this yard sale
    existing_visit = db.query(VisitedYardSale).filter(
        VisitedYardSale.user_id == current_user.id,
        VisitedYardSale.yard_sale_id == yard_sale_id
    ).first()
    
    if existing_visit:
        # Update existing visit - increment count and update last_visited
        existing_visit.visit_count += 1
        existing_visit.last_visited = get_mountain_time()
        existing_visit.updated_at = get_mountain_time()
        db.commit()
        db.refresh(existing_visit)
        
        return VisitedYardSaleResponse(
            id=existing_visit.id,
            yard_sale_id=existing_visit.yard_sale_id,
            yard_sale_title=yard_sale.title,
            visited_at=existing_visit.visited_at,
            visit_count=existing_visit.visit_count,
            last_visited=existing_visit.last_visited,
            created_at=existing_visit.created_at
        )
    else:
        # Create new visit record
        visit = VisitedYardSale(
            user_id=current_user.id,
            yard_sale_id=yard_sale_id,
            visited_at=get_mountain_time(),
            visit_count=1,
            last_visited=get_mountain_time()
        )
        
        db.add(visit)
        db.commit()
        db.refresh(visit)
        
        # Create notification for the yard sale owner (only for first visit, not repeat visits)
        if yard_sale.owner_id != current_user.id:
            try:
                create_notification(
                    db=db,
                    user_id=yard_sale.owner_id,
                    notification_type="visit",
                    title=f"Someone visited your yard sale!",
                    message=f"{current_user.username} visited your yard sale \"{yard_sale.title}\"",
                    related_user_id=current_user.id,
                    related_yard_sale_id=yard_sale_id
                )
            except Exception as e:
                # If notification creation fails, continue without error
                print(f"Notification creation failed: {e}")
                pass
        
        return VisitedYardSaleResponse(
            id=visit.id,
            yard_sale_id=visit.yard_sale_id,
            yard_sale_title=yard_sale.title,
            visited_at=visit.visited_at,
            visit_count=visit.visit_count,
            last_visited=visit.last_visited,
            created_at=visit.created_at
        )

@app.delete("/yard-sales/{yard_sale_id}/visit")
async def mark_yard_sale_not_visited(
    yard_sale_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark a yard sale as not visited by the current user (remove visit record)"""
    # Check if yard sale exists
    yard_sale = db.query(YardSale).filter(YardSale.id == yard_sale_id).first()
    if not yard_sale:
        raise HTTPException(status_code=404, detail="Yard sale not found")
    
    # Find and delete the visit record
    visit = db.query(VisitedYardSale).filter(
        VisitedYardSale.user_id == current_user.id,
        VisitedYardSale.yard_sale_id == yard_sale_id
    ).first()
    
    if not visit:
        raise HTTPException(status_code=404, detail="Visit record not found")
    
    db.delete(visit)
    db.commit()
    
    return {"message": "Yard sale marked as not visited"}

@app.get("/user/visited-yard-sales", response_model=List[VisitedYardSaleResponse])
async def get_user_visited_yard_sales(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all yard sales visited by the current user"""
    visits = db.query(VisitedYardSale).filter(
        VisitedYardSale.user_id == current_user.id
    ).order_by(VisitedYardSale.last_visited.desc()).all()
    
    result = []
    for visit in visits:
        yard_sale = db.query(YardSale).filter(YardSale.id == visit.yard_sale_id).first()
        if yard_sale:  # Only include visits for yard sales that still exist
            result.append(VisitedYardSaleResponse(
                id=visit.id,
                yard_sale_id=visit.yard_sale_id,
                yard_sale_title=yard_sale.title,
                visited_at=visit.visited_at,
                visit_count=visit.visit_count,
                last_visited=visit.last_visited,
                created_at=visit.created_at
            ))
    
    return result

@app.get("/yard-sales/{yard_sale_id}/visit-stats", response_model=VisitStatsResponse)
async def get_yard_sale_visit_stats(
    yard_sale_id: str,
    db: Session = Depends(get_db)
):
    """Get visit statistics for a specific yard sale"""
    # Check if yard sale exists
    yard_sale = db.query(YardSale).filter(YardSale.id == yard_sale_id).first()
    if not yard_sale:
        raise HTTPException(status_code=404, detail="Yard sale not found")
    
    # Get all visits for this yard sale
    visits = db.query(VisitedYardSale).filter(
        VisitedYardSale.yard_sale_id == yard_sale_id
    ).all()
    
    if not visits:
        return VisitStatsResponse(
            yard_sale_id=yard_sale_id,
            yard_sale_title=yard_sale.title,
            total_visits=0,
            unique_visitors=0,
            most_recent_visit=None,
            average_visits_per_user=0.0
        )
    
    total_visits = sum(visit.visit_count for visit in visits)
    unique_visitors = len(visits)
    most_recent_visit = max(visit.last_visited for visit in visits)
    average_visits_per_user = total_visits / unique_visitors if unique_visitors > 0 else 0.0
    
    return VisitStatsResponse(
        yard_sale_id=yard_sale_id,
        yard_sale_title=yard_sale.title,
        total_visits=total_visits,
        unique_visitors=unique_visitors,
        most_recent_visit=most_recent_visit,
        average_visits_per_user=average_visits_per_user
    )

# Notification Endpoints
@app.get("/notifications", response_model=List[NotificationResponse])
async def get_user_notifications(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get notifications for the current user"""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    notifications = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for notification in notifications:
        # Get related user info
        related_user_username = None
        if notification.related_user_id:
            related_user = db.query(User).filter(User.id == notification.related_user_id).first()
            if related_user:
                related_user_username = related_user.username
        
        # Get related yard sale info
        related_yard_sale_title = None
        if notification.related_yard_sale_id:
            related_yard_sale = db.query(YardSale).filter(YardSale.id == notification.related_yard_sale_id).first()
            if related_yard_sale:
                related_yard_sale_title = related_yard_sale.title
        
        result.append(NotificationResponse(
            id=notification.id,
            type=notification.type,
            title=notification.title,
            message=notification.message,
            is_read=notification.is_read,
            created_at=notification.created_at,
            read_at=notification.read_at,
            user_id=notification.user_id,
            related_user_id=notification.related_user_id,
            related_user_username=related_user_username,
            related_yard_sale_id=notification.related_yard_sale_id,
            related_yard_sale_title=related_yard_sale_title,
            related_message_id=notification.related_message_id
        ))
    
    return result

@app.get("/notifications/count", response_model=NotificationCountResponse)
async def get_notification_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get notification count for the current user"""
    total_notifications = db.query(Notification).filter(Notification.user_id == current_user.id).count()
    unread_notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    return NotificationCountResponse(
        total_notifications=total_notifications,
        unread_notifications=unread_notifications
    )

# Get message-specific notification counts
@app.get("/notifications/counts", response_model=MessageNotificationCounts)
async def get_message_notification_counts(
    type: str = "message",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get notification counts for specific types (e.g., message notifications)"""
    if type != "message":
        raise HTTPException(status_code=400, detail="Only 'message' type is currently supported")
    
    # Get message notification counts
    total_message_notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.type == "message"
    ).count()
    
    unread_message_notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.type == "message",
        Notification.is_read == False
    ).count()
    
    # Get last updated time
    last_notification = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.type == "message"
    ).order_by(Notification.created_at.desc()).first()
    
    last_updated = last_notification.created_at if last_notification else get_mountain_time()
    
    return MessageNotificationCounts(
        unread_message_notifications=unread_message_notifications,
        total_message_notifications=total_message_notifications,
        last_updated=last_updated
    )

@app.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    notification.read_at = get_mountain_time()
    db.commit()
    
    return {"message": "Notification marked as read"}

@app.put("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read for the current user"""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({
        "is_read": True,
        "read_at": get_mountain_time()
    })
    db.commit()
    
    return {"message": "All notifications marked as read"}

@app.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a notification"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.delete(notification)
    db.commit()
    
    return {"message": "Notification deleted"}

# Admin-only endpoints
@app.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            phone_number=user.phone_number,
            city=user.city,
            state=user.state,
            zip_code=user.zip_code,
            bio=user.bio,
            is_active=user.is_active,
            permissions=UserPermission(user.permissions),
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        for user in users
    ]

@app.get("/admin/users/{user_id}", response_model=UserResponse)
async def get_user_by_id_admin(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get user by ID (admin only)"""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        city=user.city,
        state=user.state,
        zip_code=user.zip_code,
        bio=user.bio,
        is_active=user.is_active,
        permissions=UserPermission(user.permissions),
        created_at=user.created_at,
        updated_at=user.updated_at
    )

class UserUpdateAdmin(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None)
    phone_number: Optional[str] = Field(None, max_length=20)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=2)
    zip_code: Optional[str] = Field(None, max_length=10)
    bio: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None
    permissions: Optional[UserPermission] = None

@app.put("/admin/users/{user_id}", response_model=UserResponse)
async def update_user_admin(
    user_id: str,
    user_update: UserUpdateAdmin,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update user (admin only)"""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields if provided
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    if user_update.email is not None:
        user.email = user_update.email
    if user_update.phone_number is not None:
        user.phone_number = user_update.phone_number
    if user_update.city is not None:
        user.city = user_update.city
    if user_update.state is not None:
        user.state = user_update.state
    if user_update.zip_code is not None:
        user.zip_code = user_update.zip_code
    if user_update.bio is not None:
        user.bio = user_update.bio
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    if user_update.permissions is not None:
        user.permissions = user_update.permissions.value
    
    user.updated_at = get_mountain_time()
    
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        city=user.city,
        state=user.state,
        zip_code=user.zip_code,
        bio=user.bio,
        is_active=user.is_active,
        permissions=UserPermission(user.permissions),
        created_at=user.created_at,
        updated_at=user.updated_at
    )

@app.delete("/admin/users/{user_id}")
async def delete_user_admin(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete user (admin only)"""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}

@app.get("/admin/reports", response_model=List[dict])
async def get_all_reports(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_moderator_or_admin_user),
    db: Session = Depends(get_db)
):
    """Get all reports (moderator/admin only)"""
    reports = db.query(Report).offset(skip).limit(limit).all()
    return [
        {
            "id": report.id,
            "report_type": report.report_type,
            "description": report.description,
            "status": report.status,
            "created_at": report.created_at,
            "updated_at": report.updated_at,
            "reporter_id": report.reporter_id,
            "reported_user_id": report.reported_user_id,
            "reported_yard_sale_id": report.reported_yard_sale_id
        }
        for report in reports
    ]

# Custom exception handler
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )

# Image Upload Endpoints
@app.post("/upload/image", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload an image to Garage S3 storage"""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )
        
        # Validate file size (max 10MB)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size must be less than 10MB"
            )
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix if file.filename else '.jpg'
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        s3_key = f"images/{current_user.id}/{unique_filename}"
        
        # Upload to Garage S3
        s3_client.put_object(
            Bucket=MINIO_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType=file.content_type,
            Metadata={
                'uploaded_by': current_user.username,
                'uploaded_at': datetime.now().isoformat(),
                'original_filename': file.filename or 'unknown'
            }
        )
        
        # Generate proxy URL (served through FastAPI backend)
        image_url = f"{DOMAIN_NAME}/image-proxy/{s3_key}"
        
        return ImageUploadResponse(
            success=True,
            message="Image uploaded successfully",
            image_url=image_url,
            file_name=unique_filename,
            file_size=len(file_content)
        )
        
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )

@app.get("/images", response_model=ImageListResponse)
async def list_user_images(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all images uploaded by the current user"""
    try:
        # List objects in user's folder
        prefix = f"images/{current_user.id}/"
        response = s3_client.list_objects_v2(
            Bucket=MINIO_BUCKET_NAME,
            Prefix=prefix
        )
        
        images = []
        if 'Contents' in response:
            for obj in response['Contents']:
                image_url = f"{DOMAIN_NAME}/image-proxy/{obj['Key']}"
                images.append({
                    'key': obj['Key'],
                    'url': image_url,
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'filename': obj['Key'].split('/')[-1]
                })
        
        return ImageListResponse(
            images=images,
            total=len(images)
        )
        
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list images: {str(e)}"
        )

@app.delete("/images/{image_key:path}")
async def delete_image(
    image_key: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an image uploaded by the current user"""
    try:
        # Verify the image belongs to the current user
        if not image_key.startswith(f"images/{current_user.id}/"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own images"
            )
        
        # Check if object exists
        try:
            s3_client.head_object(Bucket=MINIO_BUCKET_NAME, Key=image_key)
        except ClientError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found"
            )
        
        # Delete the object
        s3_client.delete_object(Bucket=MINIO_BUCKET_NAME, Key=image_key)
        
        return {"message": "Image deleted successfully"}
        
    except HTTPException:
        raise
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete image: {str(e)}"
        )

@app.get("/image-proxy/{image_key:path}")
async def proxy_image(
    image_key: str,
    authorization: str | None = Header(default=None, alias="Authorization"),
    token_query: str | None = Query(default=None, alias="token"),
    access_token_cookie: str | None = Cookie(default=None, alias="access_token"),
    db: Session = Depends(get_db)
):
    """Proxy images from Garage S3 with authentication.
    Accepts JWT via Authorization header, `access_token` cookie, or `token` query param.
    """
    try:
        # Resolve token from header, cookie, or query param
        resolved_token = None
        if authorization and authorization.lower().startswith("bearer "):
            resolved_token = authorization.split(" ", 1)[1].strip()
        elif access_token_cookie:
            resolved_token = access_token_cookie.strip()
        elif token_query:
            resolved_token = token_query.strip()

        if not resolved_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        # Validate token and load user
        try:
            if resolved_token in token_blacklist:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
            payload = jwt.decode(resolved_token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str | None = payload.get("sub")
            if not username:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

        user = get_user_by_username(db, username)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

        # For yard sale app, allow users to view any image (not just their own)
        # Remove the ownership check to allow public viewing of images
        # if not image_key.startswith(f"images/{user.id}/"):
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="You can only access your own images"
        #     )

        # Fetch from Garage S3
        response = s3_client.get_object(Bucket=MINIO_BUCKET_NAME, Key=image_key)
        content_type = response.get('ContentType', 'image/jpeg')

        def generate():
            for chunk in response['Body'].iter_chunks(chunk_size=8192):
                yield chunk

        return StreamingResponse(
            generate(),
            media_type=content_type,
            headers={
                'Cache-Control': 'public, max-age=3600',
                'Content-Disposition': f'inline; filename="{image_key.split("/")[-1]}"'
            }
        )

    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve image: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )

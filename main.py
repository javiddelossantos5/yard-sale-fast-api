from fastapi import FastAPI, HTTPException, status, Depends, Form
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uvicorn
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
from sqlalchemy.orm import Session
from database import get_db, create_tables, User, Item, YardSale, Comment, Message
from contextlib import asynccontextmanager
from datetime import date, time
from typing import List, Optional
from enum import Enum

# Authentication configuration
SECRET_KEY = secrets.token_urlsafe(32)  # Generate a random secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")
    location: Optional[Location] = None
    bio: Optional[str] = Field(None, max_length=1000, description="User bio")

class UserResponse(UserBase):
    id: int
    full_name: Optional[str]
    phone_number: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    bio: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

class UserLogin(BaseModel):
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")

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
    id: int
    name: str
    description: Optional[str]
    price: float
    is_available: bool
    created_at: datetime
    owner_id: int

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
    allow_messages: Optional[bool] = None
    categories: Optional[List[str]] = None
    price_range: Optional[str] = Field(None, max_length=50)
    payment_methods: Optional[List[str]] = None
    photos: Optional[List[str]] = None
    featured_image: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    status: Optional[YardSaleStatus] = Field(None, description="Yard sale status: active, closed, on_break")

class YardSaleResponse(BaseModel):
    id: int
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
    owner_id: int
    owner_username: str
    comment_count: int = 0

# Comment Models
class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000, description="Comment content")

class CommentResponse(BaseModel):
    id: int
    content: str
    created_at: datetime
    updated_at: datetime
    user_id: int
    username: str
    yard_sale_id: int

# Message Models
class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000, description="Message content")
    recipient_id: int = Field(..., description="ID of the user receiving the message")

class MessageResponse(BaseModel):
    id: int
    content: str
    is_read: bool
    created_at: datetime
    yard_sale_id: int
    sender_id: int
    sender_username: str
    recipient_id: int
    recipient_username: str

# Token blacklist for logout functionality
token_blacklist = set()

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

def get_user_by_id(db: Session, user_id: int):
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
        phone_number=user.phone_number,
        city=city,
        state=state,
        zip_code=zip_code,
        bio=user.bio,
        is_active=True
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
        created_at=db_user.created_at,
        updated_at=db_user.updated_at
    )

@app.post("/login", response_model=Token)
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

@app.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at
    }

# GET all items (protected route)
@app.get("/items", response_model=List[ItemResponse])
async def get_items(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get all items for the current user"""
    user_items = db.query(Item).filter(Item.owner_id == current_user.id).all()
    return user_items

# GET item by ID (protected route)
@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
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
async def update_item(item_id: int, item_update: ItemUpdate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
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
async def delete_item(item_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
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

@app.get("/yard-sales/{yard_sale_id}", response_model=YardSaleResponse)
async def get_yard_sale(yard_sale_id: int, db: Session = Depends(get_db)):
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
    yard_sale_id: int, 
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
    yard_sale_id: int, 
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
    yard_sale_id: int,
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
async def get_comments(yard_sale_id: int, db: Session = Depends(get_db)):
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
    comment_id: int,
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
    yard_sale_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send a private message to the yard sale owner"""
    # Check if yard sale exists
    yard_sale = db.query(YardSale).filter(YardSale.id == yard_sale_id).first()
    if not yard_sale:
        raise HTTPException(status_code=404, detail="Yard sale not found")
    
    # Check if recipient exists
    recipient = db.query(User).filter(User.id == message_data.recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    # Check if yard sale allows messages
    if not yard_sale.allow_messages:
        raise HTTPException(status_code=400, detail="This yard sale does not allow messages")
    
    # Don't allow sending messages to yourself
    if current_user.id == message_data.recipient_id:
        raise HTTPException(status_code=400, detail="Cannot send message to yourself")
    
    # Create the message
    message = Message(
        content=message_data.content,
        yard_sale_id=yard_sale_id,
        sender_id=current_user.id,
        recipient_id=message_data.recipient_id
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    return MessageResponse(
        id=message.id,
        content=message.content,
        is_read=message.is_read,
        created_at=message.created_at,
        yard_sale_id=message.yard_sale_id,
        sender_id=message.sender_id,
        sender_username=current_user.username,
        recipient_id=message.recipient_id,
        recipient_username=recipient.username
    )

# Get messages for a specific yard sale (conversation)
@app.get("/yard-sales/{yard_sale_id}/messages", response_model=List[MessageResponse])
async def get_yard_sale_messages(
    yard_sale_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all messages for a specific yard sale (only participants can see)"""
    # Check if yard sale exists
    yard_sale = db.query(YardSale).filter(YardSale.id == yard_sale_id).first()
    if not yard_sale:
        raise HTTPException(status_code=404, detail="Yard sale not found")
    
    # Get messages where current user is either sender or recipient
    messages = db.query(Message).filter(
        Message.yard_sale_id == yard_sale_id,
        (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id)
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
            yard_sale_id=message.yard_sale_id,
            sender_id=message.sender_id,
            sender_username=sender.username,
            recipient_id=message.recipient_id,
            recipient_username=recipient.username
        ))
    
    return result

# Get all messages for current user (inbox)
@app.get("/messages", response_model=List[MessageResponse])
async def get_user_messages(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all messages for the current user (both sent and received)"""
    messages = db.query(Message).filter(
        (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id)
    ).order_by(Message.created_at.desc()).all()
    
    result = []
    for message in messages:
        sender = db.query(User).filter(User.id == message.sender_id).first()
        recipient = db.query(User).filter(User.id == message.recipient_id).first()
        
        result.append(MessageResponse(
            id=message.id,
            content=message.content,
            is_read=message.is_read,
            created_at=message.created_at,
            yard_sale_id=message.yard_sale_id,
            sender_id=message.sender_id,
            sender_username=sender.username,
            recipient_id=message.recipient_id,
            recipient_username=recipient.username
        ))
    
    return result

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
    message_id: int,
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
    message_id: int,
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

# Custom exception handler
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )

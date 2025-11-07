from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Date, Time, JSON, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.mysql import CHAR
import os
from datetime import datetime
import pytz
import uuid
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
load_dotenv()

def get_mountain_time():
    """Get current time in Mountain Time Zone (Vernal, Utah)"""
    mountain_tz = pytz.timezone('America/Denver')  # Mountain Time Zone
    return datetime.now(mountain_tz)

# Database configuration
# MySQL database running in Docker container
# DATABASE_URL = "mysql+mysqlconnector://root:@127.0.0.1:3306/fastapi_db"
# DATABASE_URL = "mysql+mysqlconnector://root:supersecretpassword@127.0.0.1:3306/yardsale"
# Use environment variable if set, otherwise default to local connection
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "mysql+mysqlconnector://yardsaleuser:yardpass@127.0.0.1:3306/yardsale"
)

# Create engine with connection pooling and retry logic
engine = create_engine(
    DATABASE_URL, 
    echo=True,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,   # Recycle connections after 1 hour
    connect_args={
        "connect_timeout": 10,  # 10 second connection timeout
    }
)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Location fields
    city = Column(String(100), nullable=True)
    state = Column(String(2), nullable=True)
    zip_code = Column(String(10), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True)
    permissions = Column(String(20), default="user", nullable=False)  # "user", "admin", "moderator"
    created_at = Column(DateTime, default=get_mountain_time)
    updated_at = Column(DateTime, default=get_mountain_time, onupdate=get_mountain_time)
    
    # Relationships
    items = relationship("Item", back_populates="owner")
    yard_sales = relationship("YardSale", back_populates="owner")
    comments = relationship("Comment", back_populates="user")
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="Message.recipient_id", back_populates="recipient")
    conversations_as_participant1 = relationship("Conversation", foreign_keys="Conversation.participant1_id", back_populates="participant1")
    conversations_as_participant2 = relationship("Conversation", foreign_keys="Conversation.participant2_id", back_populates="participant2")
    
    # Trust system relationships
    ratings_given = relationship("UserRating", foreign_keys="UserRating.reviewer_id", back_populates="reviewer")
    ratings_received = relationship("UserRating", foreign_keys="UserRating.rated_user_id", back_populates="rated_user")
    reports_made = relationship("Report", foreign_keys="Report.reporter_id", back_populates="reporter")
    reports_received = relationship("Report", foreign_keys="Report.reported_user_id", back_populates="reported_user")
    verifications = relationship("Verification", back_populates="user")
    
    # Visit tracking relationships
    visited_yard_sales = relationship("VisitedYardSale", back_populates="user")
    
    # Notification relationships
    notifications = relationship("Notification", foreign_keys="Notification.user_id", back_populates="user")

class Item(Base):
    __tablename__ = "items"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    price = Column(Float, nullable=False)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_mountain_time)
    owner_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    
    # Marketplace fields
    is_public = Column(Boolean, default=True, nullable=False)
    status = Column(String(20), default="active", nullable=False)  # active, pending, sold, hidden
    category = Column(String(100), nullable=True)
    photos = Column(JSON, nullable=True)
    featured_image = Column(String(500), nullable=True)
    price_range = Column(String(50), nullable=True)
    accepts_best_offer = Column(Boolean, default=False, nullable=False)  # Whether seller accepts best offers
    payment_methods = Column(JSON, nullable=True)
    venmo_url = Column(String(500), nullable=True)
    facebook_url = Column(String(500), nullable=True)
    
    # Contact information for customer communication
    contact_phone = Column(String(20), nullable=True)  # Seller's phone number for this item
    contact_email = Column(String(100), nullable=True)  # Seller's email for this item
    
    # Price tracking for reductions
    original_price = Column(Float, nullable=True)  # Original price when item was created
    last_price_change_date = Column(DateTime, nullable=True)  # When price was last changed
    
    # Item details
    condition = Column(String(50), nullable=True)  # e.g., "new", "like new", "good", "fair", "poor"
    quantity = Column(Integer, nullable=True)  # Number of items available (None means not specified/unlimited)
    is_free = Column(Boolean, default=False, nullable=False)  # Whether the item is free (price == 0)
    miles = Column(Integer, nullable=True)  # Mileage for automotive items (optional)
    
    # Relationship with user
    owner = relationship("User", back_populates="items")

class YardSale(Base):
    __tablename__ = "yard_sales"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    
    # Basic Information
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Date and Time
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # Optional for multi-day sales
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    
    # Location
    address = Column(String(300), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)  # State abbreviation
    zip_code = Column(String(10), nullable=False)
    latitude = Column(Float, nullable=True)  # For map integration
    longitude = Column(Float, nullable=True)  # For map integration
    
    # Contact Information
    contact_name = Column(String(100), nullable=False)
    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(100), nullable=True)
    venmo_url = Column(String(500), nullable=True)  # Venmo profile URL
    facebook_url = Column(String(500), nullable=True)  # Facebook listing/profile URL
    allow_messages = Column(Boolean, default=True)
    
    # Sale Details
    categories = Column(JSON, nullable=True)  # List of categories
    price_range = Column(String(50), nullable=True)  # e.g., "Under $20", "$20-$100"
    payment_methods = Column(JSON, nullable=True)  # List of accepted payment methods
    
    # Media
    photos = Column(JSON, nullable=True)  # List of photo URLs/paths
    featured_image = Column(String(500), nullable=True)  # Featured image URL/path
    
    # Metadata
    is_active = Column(Boolean, default=True)
    status = Column(String(20), default="active", nullable=False)  # active, closed, on_break
    created_at = Column(DateTime, default=get_mountain_time)
    updated_at = Column(DateTime, default=get_mountain_time, onupdate=get_mountain_time)
    owner_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="yard_sales")
    comments = relationship("Comment", back_populates="yard_sale", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="yard_sale", cascade="all, delete-orphan")
    ratings = relationship("UserRating", back_populates="yard_sale")
    reports = relationship("Report", back_populates="reported_yard_sale")
    visits = relationship("VisitedYardSale", back_populates="yard_sale")

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=get_mountain_time)
    updated_at = Column(DateTime, default=get_mountain_time, onupdate=get_mountain_time)
    
    # Foreign Keys
    yard_sale_id = Column(CHAR(36), ForeignKey("yard_sales.id"), nullable=False)
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    yard_sale = relationship("YardSale", back_populates="comments")
    user = relationship("User", back_populates="comments")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    yard_sale_id = Column(CHAR(36), ForeignKey("yard_sales.id"), nullable=False)
    participant1_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    participant2_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=get_mountain_time)
    updated_at = Column(DateTime, default=get_mountain_time, onupdate=get_mountain_time)
    
    # Relationships
    yard_sale = relationship("YardSale", back_populates="conversations")
    participant1 = relationship("User", foreign_keys=[participant1_id], back_populates="conversations_as_participant1")
    participant2 = relationship("User", foreign_keys=[participant2_id], back_populates="conversations_as_participant2")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=get_mountain_time)
    
    # Foreign Keys
    conversation_id = Column(CHAR(36), ForeignKey("conversations.id"), nullable=False)
    sender_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    recipient_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_messages")

class MarketItemComment(Base):
    __tablename__ = "market_item_comments"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=get_mountain_time)
    updated_at = Column(DateTime, default=get_mountain_time, onupdate=get_mountain_time)
    
    # Foreign Keys
    item_id = Column(CHAR(36), ForeignKey("items.id"), nullable=False)
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    item = relationship("Item")
    user = relationship("User")

class WatchedItem(Base):
    __tablename__ = "watched_items"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    created_at = Column(DateTime, default=get_mountain_time)
    
    # Foreign Keys
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    item_id = Column(CHAR(36), ForeignKey("items.id"), nullable=False)
    
    # Relationships
    user = relationship("User")
    item = relationship("Item")
    
    # Ensure one watch per user per item
    __table_args__ = (
        UniqueConstraint('user_id', 'item_id', name='unique_user_item_watch'),
    )

class MarketItemConversation(Base):
    __tablename__ = "market_item_conversations"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    item_id = Column(CHAR(36), ForeignKey("items.id"), nullable=False)
    participant1_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)  # Buyer/Inquirer
    participant2_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)  # Seller (item owner)
    created_at = Column(DateTime, default=get_mountain_time)
    updated_at = Column(DateTime, default=get_mountain_time, onupdate=get_mountain_time)
    
    # Relationships
    item = relationship("Item")
    participant1 = relationship("User", foreign_keys=[participant1_id])
    participant2 = relationship("User", foreign_keys=[participant2_id])
    messages = relationship("MarketItemMessage", back_populates="conversation", cascade="all, delete-orphan")

class MarketItemMessage(Base):
    __tablename__ = "market_item_messages"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=get_mountain_time)
    
    # Foreign Keys
    conversation_id = Column(CHAR(36), ForeignKey("market_item_conversations.id"), nullable=False)
    sender_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    recipient_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    conversation = relationship("MarketItemConversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])
    recipient = relationship("User", foreign_keys=[recipient_id])

class UserRating(Base):
    __tablename__ = "user_ratings"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    review_text = Column(Text, nullable=True)  # Optional review text
    created_at = Column(DateTime, default=get_mountain_time)
    updated_at = Column(DateTime, default=get_mountain_time, onupdate=get_mountain_time)
    
    # Foreign Keys
    reviewer_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)  # User giving the rating
    rated_user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)  # User being rated
    yard_sale_id = Column(CHAR(36), ForeignKey("yard_sales.id"), nullable=True)  # Optional: related yard sale
    
    # Relationships
    reviewer = relationship("User", foreign_keys=[reviewer_id], back_populates="ratings_given")
    rated_user = relationship("User", foreign_keys=[rated_user_id], back_populates="ratings_received")
    yard_sale = relationship("YardSale", back_populates="ratings")

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    report_type = Column(String(50), nullable=False)  # "scam", "inappropriate", "spam", "other"
    description = Column(Text, nullable=False)
    status = Column(String(20), default="pending")  # "pending", "reviewed", "resolved", "dismissed"
    created_at = Column(DateTime, default=get_mountain_time)
    updated_at = Column(DateTime, default=get_mountain_time, onupdate=get_mountain_time)
    
    # Foreign Keys
    reporter_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)  # User making the report
    reported_user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=True)  # User being reported
    reported_yard_sale_id = Column(CHAR(36), ForeignKey("yard_sales.id"), nullable=True)  # Yard sale being reported
    
    # Relationships
    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="reports_made")
    reported_user = relationship("User", foreign_keys=[reported_user_id], back_populates="reports_received")
    reported_yard_sale = relationship("YardSale", back_populates="reports")

class Verification(Base):
    __tablename__ = "verifications"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    verification_type = Column(String(50), nullable=False)  # "email", "phone", "identity", "address"
    status = Column(String(20), default="pending")  # "pending", "verified", "rejected"
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_mountain_time)
    updated_at = Column(DateTime, default=get_mountain_time, onupdate=get_mountain_time)
    
    # Foreign Keys
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="verifications")

class VisitedYardSale(Base):
    __tablename__ = "visited_yard_sales"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    visited_at = Column(DateTime, default=get_mountain_time)
    visit_count = Column(Integer, default=1)
    last_visited = Column(DateTime, default=get_mountain_time, onupdate=get_mountain_time)
    created_at = Column(DateTime, default=get_mountain_time)
    updated_at = Column(DateTime, default=get_mountain_time, onupdate=get_mountain_time)
    
    # Foreign Keys
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    yard_sale_id = Column(CHAR(36), ForeignKey("yard_sales.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="visited_yard_sales")
    yard_sale = relationship("YardSale", back_populates="visits")
    
    # Unique constraint to prevent duplicate visits
    __table_args__ = (
        UniqueConstraint('user_id', 'yard_sale_id', name='unique_user_yard_sale_visit'),
    )

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    type = Column(String(50), nullable=False)  # "message", "rating", "comment", "visit", etc.
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=get_mountain_time)
    read_at = Column(DateTime, nullable=True)
    
    # Foreign Keys
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)  # User receiving the notification
    related_user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=True)  # User who triggered the notification
    related_yard_sale_id = Column(CHAR(36), ForeignKey("yard_sales.id"), nullable=True)  # Related yard sale
    related_message_id = Column(CHAR(36), ForeignKey("messages.id"), nullable=True)  # Related message
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="notifications")
    related_user = relationship("User", foreign_keys=[related_user_id])
    related_yard_sale = relationship("YardSale", foreign_keys=[related_yard_sale_id])
    related_message = relationship("Message", foreign_keys=[related_message_id])

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create all tables
def create_tables():
    Base.metadata.create_all(bind=engine)

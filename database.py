from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Date, Time, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, date, time

# Database configuration
# MySQL root user has empty password
DATABASE_URL = "mysql+mysqlconnector://root:@127.0.0.1:3306/fastapi_db"

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    items = relationship("Item", back_populates="owner")
    yard_sales = relationship("YardSale", back_populates="owner")
    comments = relationship("Comment", back_populates="user")
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="Message.recipient_id", back_populates="recipient")

class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    price = Column(Float, nullable=False)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationship with user
    owner = relationship("User", back_populates="items")

class YardSale(Base):
    __tablename__ = "yard_sales"
    
    id = Column(Integer, primary_key=True, index=True)
    
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="yard_sales")
    comments = relationship("Comment", back_populates="yard_sale", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="yard_sale", cascade="all, delete-orphan")

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    yard_sale_id = Column(Integer, ForeignKey("yard_sales.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    yard_sale = relationship("YardSale", back_populates="comments")
    user = relationship("User", back_populates="comments")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    yard_sale_id = Column(Integer, ForeignKey("yard_sales.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    yard_sale = relationship("YardSale", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_messages")

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

from fastapi import FastAPI, HTTPException, status, Depends, Form, WebSocket, WebSocketDisconnect, UploadFile, File, Header, Cookie, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response
from pydantic import BaseModel, Field, EmailStr, model_validator
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
from botocore.config import Config
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
# This must be called before any os.getenv() calls
load_dotenv()
from database import get_db, create_tables, User, Item, YardSale, Comment, Message, Conversation, UserRating, Report, Verification, VisitedYardSale, Notification
from database import MarketItemComment, WatchedItem, MarketItemConversation, MarketItemMessage, Event, EventComment, get_mountain_time

def calculate_price_reduction_fields(item: Item) -> dict:
    """Calculate price reduction fields for MarketItemResponse"""
    price_reduced = False
    price_reduction_amount = None
    price_reduction_percentage = None
    
    # Safely handle missing columns (if migration hasn't been run)
    original_price = getattr(item, 'original_price', None)
    current_price = getattr(item, 'price', 0)
    
    if original_price and original_price > 0 and current_price > 0:
        if current_price < original_price:
            price_reduced = True
            price_reduction_amount = original_price - current_price
            price_reduction_percentage = round((price_reduction_amount / original_price) * 100, 2)
    
    return {
        "price_reduced": price_reduced,
        "price_reduction_amount": price_reduction_amount,
        "price_reduction_percentage": price_reduction_percentage
    }

def get_optional_user_from_auth_header(authorization: Optional[str], db: Session) -> Optional[User]:
    """Return current user if Authorization header contains a valid Bearer token, else None."""
    if not authorization:
        return None
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            return None
        if token in token_blacklist:
            return None
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            return None
        user = get_user_by_username(db, username)
        return user
    except Exception:
        return None
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
# Use environment variables if set, otherwise use defaults
# MINIO_ENDPOINT_URL = os.getenv("MINIO_ENDPOINT_URL", "https://s3image.yardsalefinders.com")
# MinIO uses port 9000 for S3 API, port 9001 for web console
MINIO_ENDPOINT_URL = os.getenv("MINIO_ENDPOINT_URL", "http://10.1.2.165:9000") # "https://s3image.yardsalefinders.com"
MINIO_ACCESS_KEY_ID = os.getenv("MINIO_ACCESS_KEY_ID", "minioadmin")
MINIO_SECRET_ACCESS_KEY = os.getenv("MINIO_SECRET_ACCESS_KEY", "minioadmin")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "yardsale")
MINIO_REGION = os.getenv("MINIO_REGION", "us-east-1")  # MinIO ignores this, but boto3 requires it

# Domain configuration for image URLs
# For production, this should be your FastAPI backend domain
DOMAIN_NAME = os.getenv("DOMAIN_NAME", "http://10.1.2.165:8000")  # For local development

# Initialize S3 client for MinIO
# Configure SSL verification (set MINIO_VERIFY_SSL=false for self-signed certs or HTTP)
# Default to false for local HTTP endpoints
verify_ssl = os.getenv("MINIO_VERIFY_SSL", "false").lower() == "true"

# Create boto3 config for S3 client
s3_config = Config(
    signature_version='s3v4',
    retries={'max_attempts': 3, 'mode': 'standard'}
)

# Initialize S3 client for MinIO
# boto3 automatically handles HTTP vs HTTPS based on the endpoint URL
# For HTTP endpoints (like http://10.1.2.165:9001), no SSL is used
# For HTTPS endpoints, SSL verification is based on verify_ssl setting
if not verify_ssl and MINIO_ENDPOINT_URL.startswith('https://'):
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize S3 client (works for both HTTP and HTTPS)`]
s3_client = boto3.client(
    's3',
    endpoint_url=MINIO_ENDPOINT_URL,
    aws_access_key_id=MINIO_ACCESS_KEY_ID,
    aws_secret_access_key=MINIO_SECRET_ACCESS_KEY,
        region_name=MINIO_REGION,
        config=s3_config
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
        print(f"⚠️  Warning: Could not create database tables: {e}")
        print("   The application will start, but database operations may fail.")
        print("   You can create tables manually later with: python setup_docker_database.py")
        import traceback
        traceback.print_exc()
        # Don't crash - let the app start anyway
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

# Customize OpenAPI schema to add username/password support
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add custom security scheme - only Bearer token (username/password handled via Quick Login widget)
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your Bearer token (JWT). You can get this by logging in via /login or /docs-login, or use the Quick Login widget in the top-right corner."
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Add CORS middleware to allow requests from frontend
# Allow both development and production origins
# Can be overridden with CORS_ORIGINS environment variable (comma-separated)
cors_origins_env = os.getenv("CORS_ORIGINS", "").strip()
if cors_origins_env:
    # Use environment variable if set
    cors_origins = [origin.strip() for origin in cors_origins_env.split(",")]
else:
    # Default origins: development and production
    cors_origins = [
        "http://localhost:5173",           # Svelte dev server localhost
        "http://127.0.0.1:5173",           # Svelte dev server 127.0.0.1
        "http://10.1.2.165:5173",          # Svelte dev server on server IP
        "http://localhost:3000",            # Alternative dev port
        "http://10.1.2.165:3000",          # Alternative dev port on server
        "https://yardsalefinders.com",      # Production domain
        "https://main.yardsalefinders.com", # Production subdomain
        "https://api.yardsalefinders.com",  # Backend API subdomain (if frontend needs to call it)
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,  # Allow credentials for authenticated requests
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Helper function to generate login form HTML
def get_login_form_html(error_message: Optional[str] = None) -> str:
    """Generate HTML for the admin login form"""
    error_html = ""
    if error_message:
        error_html = f'<div class="error show" id="errorMessage" style="display: block;">{error_message}</div>'
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Login - API Documentation</title>
        <style>
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                text-align: center; 
                padding: 50px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .container {{
                background: white;
                color: #333;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                max-width: 400px;
                width: 100%;
            }}
            h1 {{ color: #667eea; margin-top: 0; margin-bottom: 30px; }}
            .form-group {{
                margin-bottom: 20px;
                text-align: left;
            }}
            label {{
                display: block;
                margin-bottom: 8px;
                color: #555;
                font-weight: 500;
            }}
            input {{
                width: 100%;
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                font-size: 16px;
                box-sizing: border-box;
            }}
            input:focus {{
                outline: none;
                border-color: #667eea;
            }}
            button {{
                width: 100%;
                padding: 12px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                margin-top: 10px;
            }}
            button:hover {{
                background: #5568d3;
            }}
            button:disabled {{
                background: #ccc;
                cursor: not-allowed;
            }}
            .error {{
                color: #e74c3c;
                margin-top: 10px;
                font-size: 14px;
                display: none;
                padding: 10px;
                background: #fee;
                border-radius: 5px;
                border: 1px solid #fcc;
            }}
            .error.show {{
                display: block;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔒 Admin Login</h1>
            <p style="color: #666; margin-bottom: 30px;">Enter your admin credentials to access the API documentation</p>
            {error_html}
            <form id="loginForm">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" required autocomplete="username">
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required autocomplete="current-password">
                </div>
                <div class="error" id="errorMessage"></div>
                <button type="submit" id="submitBtn">Login</button>
            </form>
        </div>
        
        <script>
            // Clear localStorage token on expired session
            localStorage.removeItem('swagger_token');
            
            document.getElementById('loginForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                const submitBtn = document.getElementById('submitBtn');
                const errorMsg = document.getElementById('errorMessage');
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                
                submitBtn.disabled = true;
                submitBtn.textContent = 'Logging in...';
                errorMsg.classList.remove('show');
                
                try {{
                    const response = await fetch('/docs-login', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        credentials: 'include',
                        body: JSON.stringify({{ username, password }})
                    }});
                    
                    const data = await response.json();
                    
                    if (response.ok) {{
                        // Store token in localStorage for Swagger UI auto-population
                        if (data.access_token) {{
                            localStorage.setItem('swagger_token', data.access_token);
                        }}
                        // Redirect to docs
                        window.location.href = '/docs';
                    }} else {{
                        errorMsg.textContent = data.detail || 'Login failed';
                        errorMsg.classList.add('show');
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'Login';
                    }}
                }} catch (error) {{
                    errorMsg.textContent = 'An error occurred. Please try again.';
                    errorMsg.classList.add('show');
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Login';
                }}
            }});
        </script>
    </body>
    </html>
    """

# Middleware to protect docs endpoints with authentication
class DocsAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to require authentication for /docs, /redoc, and /openapi.json endpoints"""
    
    async def dispatch(self, request: StarletteRequest, call_next):
        # Check if the request is for docs, redoc, or openapi.json
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            # Allow OPTIONS requests for CORS
            if request.method == "OPTIONS":
                return await call_next(request)
            
            # Check for token in Authorization header OR cookie
            auth_header = request.headers.get("Authorization")
            token = None
            
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split("Bearer ")[1]
            else:
                # Check for token in cookie
                token = request.cookies.get("docs_token")
            
            if not token:
                # Return login form for browser requests
                if "text/html" in request.headers.get("Accept", "") or request.url.path in ["/docs", "/redoc"]:
                    return Response(
                        content=get_login_form_html(),
                        status_code=401,
                        media_type="text/html"
                    )
                # For API/JSON requests, return JSON error
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Authentication required to access API documentation",
                        "message": "Please login first using POST /docs-login with admin credentials"
                    }
                )
            
            if not token:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid authorization header format. Expected: Authorization: Bearer <token>"}
                )
            
            # Validate token
            try:
                # Check if token is blacklisted
                if token in token_blacklist:
                    # For browser requests, show login form
                    if "text/html" in request.headers.get("Accept", "") or request.url.path in ["/docs", "/redoc"]:
                        return Response(
                            content=get_login_form_html("Token has been revoked. Please login again."),
                            status_code=401,
                            media_type="text/html"
                        )
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Token has been revoked. Please login again."}
                    )
                
                # Decode and validate token
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                username = payload.get("sub")
                if not username:
                    # For browser requests, show login form
                    if "text/html" in request.headers.get("Accept", "") or request.url.path in ["/docs", "/redoc"]:
                        return Response(
                            content=get_login_form_html("Invalid token. Please login again."),
                            status_code=401,
                            media_type="text/html"
                        )
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Invalid token"}
                    )
                
                # Token is valid, allow request to proceed
                
            except JWTError as e:
                # Token expired or invalid - show login form for browser requests
                if "text/html" in request.headers.get("Accept", "") or request.url.path in ["/docs", "/redoc"]:
                    return Response(
                        content=get_login_form_html("Your session has expired. Please login again."),
                        status_code=401,
                        media_type="text/html"
                    )
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or expired token. Please login again."}
                )
        
        # Inject JavaScript into Swagger UI to auto-populate token and add username/password support
        if request.url.path == "/docs" and request.method == "GET":
            response = await call_next(request)
            
            # Only try to inject JavaScript if it's an HTML response
            if hasattr(response, 'body_iterator') and response.media_type == "text/html":
                try:
                    # Read the response body
                    body = b""
                    async for chunk in response.body_iterator:
                        body += chunk
                    
                    # Convert to string
                    html = body.decode('utf-8')
                    
                    # Inject JavaScript before closing body tag
                    js_injection = """
                <script>
                (function() {
                    // Auto-populate Bearer token from localStorage
                    window.addEventListener('load', function() {
                        const token = localStorage.getItem('swagger_token');
                        if (token) {
                            // Wait for Swagger UI to initialize
                            setTimeout(function() {
                                // Find the authorize button and click it
                                const authorizeBtn = document.querySelector('.btn.authorize');
                                if (authorizeBtn) {
                                    authorizeBtn.click();
                                    
                                    // Wait for modal to open, then fill in token
                                    setTimeout(function() {
                                        const tokenInput = document.querySelector('input[placeholder*="Bearer"], input[type="text"][name*="bearer"], input[type="text"][name*="Bearer"]');
                                        if (tokenInput) {
                                            tokenInput.value = token;
                                            // Trigger input event to update Swagger UI
                                            tokenInput.dispatchEvent(new Event('input', { bubbles: true }));
                                            
                                            // Click authorize button in modal
                                            setTimeout(function() {
                                                const authorizeModalBtn = document.querySelector('.modal-btn.authorize');
                                                if (authorizeModalBtn) {
                                                    authorizeModalBtn.click();
                                                }
                                            }, 100);
                                        }
                                    }, 300);
                                }
                            }, 1000);
                        }
                        
                        // Add username/password login helper
                        const addLoginHelper = function() {
                            const swaggerUI = document.querySelector('.swagger-ui');
                            if (!swaggerUI) return;
                            
                            // Check if helper already exists
                            if (document.getElementById('swagger-login-helper')) return;
                            
                            const helper = document.createElement('div');
                            helper.id = 'swagger-login-helper';
                            helper.style.cssText = 'position: fixed; top: 10px; right: 10px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); z-index: 10000; max-width: 320px; border: 2px solid #667eea;';
                            helper.innerHTML = `
                                <h4 style="margin: 0 0 15px 0; font-size: 16px; color: #667eea; font-weight: bold;">🔐 Quick Login</h4>
                                <button id="swagger-quick-login-btn" style="width: 100%; padding: 10px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; font-weight: bold; margin-bottom: 15px;">⚡ Quick Login (javiddelossantos)</button>
                                <p style="margin: 0 0 15px 0; font-size: 12px; color: #666; text-align: center;">Or enter credentials manually:</p>
                                <div style="margin-bottom: 10px;">
                                    <label style="display: block; margin-bottom: 5px; font-size: 13px; color: #555; font-weight: 500;">Username</label>
                                    <input type="text" id="swagger-username" placeholder="Enter username" style="width: 100%; padding: 8px; margin-bottom: 5px; box-sizing: border-box; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;">
                                </div>
                                <div style="margin-bottom: 15px;">
                                    <label style="display: block; margin-bottom: 5px; font-size: 13px; color: #555; font-weight: 500;">Password</label>
                                    <input type="password" id="swagger-password" placeholder="Enter password" style="width: 100%; padding: 8px; margin-bottom: 5px; box-sizing: border-box; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;">
                                </div>
                                <button id="swagger-login-btn" style="width: 100%; padding: 10px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; font-weight: bold;">Login & Auto-Authorize</button>
                                <div id="swagger-login-error" style="color: #e74c3c; font-size: 12px; margin-top: 10px; padding: 8px; background: #fee; border-radius: 4px; display: none;"></div>
                            `;
                            document.body.appendChild(helper);
                            
                            // Quick login button (auto-fills credentials)
                            document.getElementById('swagger-quick-login-btn').addEventListener('click', async function() {
                                const username = 'javiddelossantos';
                                const password = 'Password';
                                const errorDiv = document.getElementById('swagger-login-error');
                                const quickBtn = document.getElementById('swagger-quick-login-btn');
                                
                                quickBtn.disabled = true;
                                quickBtn.textContent = 'Logging in...';
                                errorDiv.style.display = 'none';
                                
                                try {
                                    const response = await fetch('/login', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        credentials: 'include',
                                        body: JSON.stringify({ username, password })
                                    });
                                    
                                    const data = await response.json();
                                    
                                    if (response.ok && data.access_token) {
                                        // Store token
                                        localStorage.setItem('swagger_token', data.access_token);
                                        
                                        // Auto-populate in Swagger UI
                                        const authorizeBtn = document.querySelector('.btn.authorize');
                                        if (authorizeBtn) {
                                            authorizeBtn.click();
                                            setTimeout(function() {
                                                const tokenInput = document.querySelector('input[placeholder*="Bearer"], input[type="text"][name*="bearer"]');
                                                if (tokenInput) {
                                                    tokenInput.value = data.access_token;
                                                    tokenInput.dispatchEvent(new Event('input', { bubbles: true }));
                                                    setTimeout(function() {
                                                        const authorizeModalBtn = document.querySelector('.modal-btn.authorize');
                                                        if (authorizeModalBtn) authorizeModalBtn.click();
                                                    }, 100);
                                                }
                                            }, 300);
                                        }
                                        
                                        errorDiv.style.display = 'none';
                                        helper.style.display = 'none';
                                    } else {
                                        errorDiv.textContent = data.detail || 'Login failed';
                                        errorDiv.style.display = 'block';
                                        quickBtn.disabled = false;
                                        quickBtn.textContent = '⚡ Quick Login (javiddelossantos)';
                                    }
                                } catch (error) {
                                    errorDiv.textContent = 'Error: ' + error.message;
                                    errorDiv.style.display = 'block';
                                    quickBtn.disabled = false;
                                    quickBtn.textContent = '⚡ Quick Login (javiddelossantos)';
                                }
                            });
                            
                            // Manual login button
                            document.getElementById('swagger-login-btn').addEventListener('click', async function() {
                                const username = document.getElementById('swagger-username').value;
                                const password = document.getElementById('swagger-password').value;
                                const errorDiv = document.getElementById('swagger-login-error');
                                
                                if (!username || !password) {
                                    errorDiv.textContent = 'Please enter username and password';
                                    errorDiv.style.display = 'block';
                                    return;
                                }
                                
                                try {
                                    const response = await fetch('/login', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        credentials: 'include',
                                        body: JSON.stringify({ username, password })
                                    });
                                    
                                    const data = await response.json();
                                    
                                    if (response.ok && data.access_token) {
                                        // Store token
                                        localStorage.setItem('swagger_token', data.access_token);
                                        
                                        // Auto-populate in Swagger UI
                                        const authorizeBtn = document.querySelector('.btn.authorize');
                                        if (authorizeBtn) {
                                            authorizeBtn.click();
                                            setTimeout(function() {
                                                const tokenInput = document.querySelector('input[placeholder*="Bearer"], input[type="text"][name*="bearer"]');
                                                if (tokenInput) {
                                                    tokenInput.value = data.access_token;
                                                    tokenInput.dispatchEvent(new Event('input', { bubbles: true }));
                                                    setTimeout(function() {
                                                        const authorizeModalBtn = document.querySelector('.modal-btn.authorize');
                                                        if (authorizeModalBtn) authorizeModalBtn.click();
                                                    }, 100);
                                                }
                                            }, 300);
                                        }
                                        
                                        errorDiv.style.display = 'none';
                                        helper.style.display = 'none';
                                    } else {
                                        errorDiv.textContent = data.detail || 'Login failed';
                                        errorDiv.style.display = 'block';
                                    }
                                } catch (error) {
                                    errorDiv.textContent = 'Error: ' + error.message;
                                    errorDiv.style.display = 'block';
                                }
                            });
                        };
                        
                        // Wait a bit for Swagger UI to load, then add helper
                        setTimeout(addLoginHelper, 1500);
                    });
                })();
                </script>
                """
                    
                    # Insert before closing body tag
                    html = html.replace('</body>', js_injection + '</body>')
                    
                    # Create new response
                    from starlette.responses import HTMLResponse
                    return HTMLResponse(content=html, status_code=response.status_code, headers=dict(response.headers))
                except Exception as e:
                    # If injection fails, just return the original response
                    # Log the error but don't crash
                    import logging
                    logging.error(f"Failed to inject JavaScript into Swagger UI: {e}")
                    return response
            else:
                # Not an HTML response, return as-is
                return response
        
        # For all other paths, proceed normally
        return await call_next(request)

# Add docs authentication middleware (after CORS, before routes)
app.add_middleware(DocsAuthMiddleware)

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
    password_confirm: str = Field(..., min_length=6, max_length=72, description="Confirm password (must match password)")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")
    company: Optional[str] = Field(None, max_length=150, description="Company name (optional)")
    location: Optional[Location] = None
    bio: Optional[str] = Field(None, max_length=1000, description="User bio")
    # NOTE: permissions field removed - all new users are created with "user" permission
    # Only admins can change permissions via /admin/users/{user_id} endpoint
    
    @model_validator(mode='after')
    def verify_password_match(self):
        """Verify that password and password_confirm match"""
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self
    
    @model_validator(mode='after')
    def verify_password_byte_length(self):
        """Ensure password doesn't exceed 72 bytes (bcrypt limitation)"""
        password_bytes = self.password.encode('utf-8')
        if len(password_bytes) > 72:
            # Truncate to 72 bytes
            password_bytes = password_bytes[:72]
            self.password = password_bytes.decode('utf-8', errors='ignore')
            # Also truncate password_confirm to match
            password_confirm_bytes = self.password_confirm.encode('utf-8')
            if len(password_confirm_bytes) > 72:
                password_confirm_bytes = password_confirm_bytes[:72]
                self.password_confirm = password_confirm_bytes.decode('utf-8', errors='ignore')
        return self

class UserResponse(UserBase):
    id: str
    full_name: Optional[str]
    phone_number: Optional[str]
    company: Optional[str] = None
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    bio: Optional[str]
    profile_picture: Optional[str] = None  # URL to profile picture (optional)
    is_active: bool
    permissions: UserPermission
    created_at: datetime
    updated_at: datetime

class UserUpdate(BaseModel):
    """Model for users to update their own profile"""
    full_name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=150, description="Company name (optional)")
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=2)
    zip_code: Optional[str] = Field(None, max_length=10)
    bio: Optional[str] = Field(None, max_length=1000)
    profile_picture: Optional[str] = Field(None, max_length=500, description="URL to profile picture (optional)")

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
    # Marketplace fields
    is_public: Optional[bool] = True
    status: Optional[str] = "active"
    category: Optional[str] = None
    photos: Optional[List[str]] = None
    featured_image: Optional[str] = None
    price_range: Optional[str] = None
    payment_methods: Optional[List[str]] = None
    created_at: datetime
    owner_id: str

class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, gt=0)
    is_available: Optional[bool] = None
    # Allow updating marketplace fields on private items route too
    is_public: Optional[bool] = None
    status: Optional[str] = Field(None, pattern="^(active|pending|sold|hidden)$")
    category: Optional[str] = Field(None, max_length=100)
    photos: Optional[List[str]] = None
    featured_image: Optional[str] = Field(None, max_length=500)
    price_range: Optional[str] = Field(None, max_length=50)
    payment_methods: Optional[List[str]] = None

# Market Item Models (public marketplace for individual items)
class MarketItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: float = Field(..., ge=0, description="Item price (0 for free items)")
    is_free: bool = Field(False, description="Mark item as free (if True, price should be 0)")
    is_public: bool = True
    status: Optional[str] = Field("active", pattern="^(active|pending|sold|hidden)$")
    category: Optional[str] = Field(None, max_length=100)
    photos: Optional[List[str]] = None
    featured_image: Optional[str] = Field(None, max_length=500)
    price_range: Optional[str] = Field(None, max_length=50)
    accepts_best_offer: bool = Field(False, description="Whether seller accepts best offers")
    payment_methods: Optional[List[str]] = None
    venmo_url: Optional[str] = Field(None, max_length=500)
    facebook_url: Optional[str] = Field(None, max_length=500)
    seller: Optional[str] = Field(None, max_length=100, description="Seller name/contact name (optional)")
    contact_phone: Optional[str] = Field(None, max_length=20, description="Seller's phone number for customer communication")
    contact_email: Optional[str] = Field(None, max_length=100, description="Seller's email for customer communication")
    city: Optional[str] = Field(None, max_length=100, description="City where item is located (optional)")
    state: Optional[str] = Field(None, max_length=2, description="State abbreviation (e.g., UT, CA) (optional)")
    zip_code: Optional[str] = Field(None, max_length=10, description="ZIP code (optional)")
    condition: Optional[str] = Field(None, max_length=50, description="Item condition (e.g., new, like new, good, fair, poor)")
    quantity: Optional[int] = Field(None, ge=1, description="Number of items available (None means not specified/unlimited)")
    miles: Optional[int] = Field(None, ge=0, description="Mileage for automotive items (optional)")
    
    @model_validator(mode='after')
    def validate_free_item(self):
        """Ensure that if is_free is True, price is 0"""
        if self.is_free and self.price != 0:
            # If marked as free, set price to 0
            self.price = 0.0
        elif not self.is_free and self.price == 0:
            # If price is 0, automatically mark as free
            self.is_free = True
        return self

class MarketItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, ge=0, description="Item price (0 for free items)")
    is_free: Optional[bool] = Field(None, description="Mark item as free (if True, price should be 0)")
    is_public: Optional[bool] = None
    status: Optional[str] = Field(None, pattern="^(active|pending|sold|hidden)$")
    category: Optional[str] = Field(None, max_length=100)
    photos: Optional[List[str]] = None
    featured_image: Optional[str] = Field(None, max_length=500)
    price_range: Optional[str] = Field(None, max_length=50)
    accepts_best_offer: Optional[bool] = None
    payment_methods: Optional[List[str]] = None
    venmo_url: Optional[str] = Field(None, max_length=500)
    facebook_url: Optional[str] = Field(None, max_length=500)
    seller: Optional[str] = Field(None, max_length=100, description="Seller name/contact name (optional)")
    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_email: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100, description="City where item is located (optional)")
    state: Optional[str] = Field(None, max_length=2, description="State abbreviation (e.g., UT, CA) (optional)")
    zip_code: Optional[str] = Field(None, max_length=10, description="ZIP code (optional)")
    condition: Optional[str] = Field(None, max_length=50, description="Item condition (e.g., new, like new, good, fair, poor)")
    quantity: Optional[int] = Field(None, ge=1, description="Number of items available (None means not specified/unlimited)")
    miles: Optional[int] = Field(None, ge=0, description="Mileage for automotive items (optional)")
    
    @model_validator(mode='after')
    def validate_free_item(self):
        """Ensure that if is_free is True, price is 0"""
        if self.is_free is not None and self.price is not None:
            if self.is_free and self.price != 0:
                # If marked as free, set price to 0
                self.price = 0.0
            elif not self.is_free and self.price == 0:
                # If price is 0, automatically mark as free
                self.is_free = True
        elif self.is_free is True and self.price is None:
            # If marking as free but price not provided, set to 0
            self.price = 0.0
        elif self.price == 0 and self.is_free is None:
            # If price is 0, automatically mark as free
            self.is_free = True
        return self

class MarketItemResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    price: float
    is_available: bool
    is_public: bool
    status: str
    category: Optional[str]
    photos: Optional[List[str]]
    featured_image: Optional[str]
    price_range: Optional[str]
    accepts_best_offer: bool
    payment_methods: Optional[List[str]]
    venmo_url: Optional[str]
    facebook_url: Optional[str]
    seller: Optional[str] = None  # Seller name/contact name (optional)
    contact_phone: Optional[str]
    contact_email: Optional[str]
    city: Optional[str] = None  # City where item is located (optional)
    state: Optional[str] = None  # State abbreviation (optional)
    zip_code: Optional[str] = None  # ZIP code (optional)
    condition: Optional[str] = None
    quantity: Optional[int] = None
    miles: Optional[int] = None  # Mileage for automotive items
    is_free: bool = False  # Whether the item is free (price == 0 or is_free flag set)
    comment_count: int = 0
    created_at: datetime
    owner_id: str
    owner_username: str
    owner_is_admin: bool = False  # Whether the owner has admin permissions
    owner_profile_picture: Optional[str] = None  # Profile picture of the owner
    is_watched: Optional[bool] = None
    # Price reduction tracking
    original_price: Optional[float] = None
    last_price_change_date: Optional[datetime] = None
    price_reduced: bool = False  # True if current price < original price
    price_reduction_amount: Optional[float] = None  # original_price - current_price
    price_reduction_percentage: Optional[float] = None  # percentage reduction

# Market item comments
class MarketItemCommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)

class MarketItemCommentResponse(BaseModel):
    id: str
    content: str
    created_at: datetime
    updated_at: datetime
    user_id: str
    username: str
    user_is_admin: bool = False
    user_profile_picture: Optional[str] = None  # Profile picture of the commenter
    item_id: str

# Market Item Messaging Models
class MarketItemMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000, description="Message content")
    recipient_id: Optional[str] = Field(None, description="Recipient user ID (usually the seller, auto-detected if not provided)")

class MarketItemMessageResponse(BaseModel):
    id: str
    content: str
    is_read: bool
    created_at: datetime
    conversation_id: str
    sender_id: str
    sender_username: str
    sender_is_admin: bool = False
    sender_profile_picture: Optional[str] = None  # Profile picture of the sender
    recipient_id: str
    recipient_username: str

class MarketItemsPaginatedResponse(BaseModel):
    """Paginated response for market items"""
    items: List[MarketItemResponse]
    total: int
    limit: int
    offset: int
    has_more: bool

# Featured Image Management Models (used by both yard sales and market items)
class SetFeaturedImageRequest(BaseModel):
    image_url: Optional[str] = Field(None, description="Full image URL to set as featured")
    image_key: Optional[str] = Field(None, description="Image key (e.g., 'images/user_id/filename.jpg') to set as featured")
    photo_index: Optional[int] = Field(None, description="Index in the photos array to set as featured")

class FeaturedImageResponse(BaseModel):
    success: bool
    message: str
    featured_image: Optional[str] = None

class MarketItemConversationResponse(BaseModel):
    id: str
    item_id: str
    item_name: str
    participant1_id: str
    participant1_username: str
    participant2_id: str
    participant2_username: str
    created_at: datetime
    updated_at: datetime
    last_message: Optional[MarketItemMessageResponse] = None
    unread_count: int = 0

# Yard Sale Messaging Models
class YardSaleMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000, description="Message content")

class YardSaleMessageResponse(BaseModel):
    id: str
    content: str
    is_read: bool
    created_at: datetime
    sender_id: str
    sender_username: str
    sender_is_admin: bool = False
    sender_profile_picture: Optional[str] = None  # Profile picture of the sender
    recipient_id: str
    recipient_username: str
    yard_sale_id: str
    conversation_id: str

class YardSaleConversationResponse(BaseModel):
    id: str
    yard_sale_id: str
    yard_sale_title: Optional[str] = None
    participant1_id: str
    participant1_username: Optional[str] = None
    participant2_id: str
    participant2_username: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_message: Optional[YardSaleMessageResponse] = None
    unread_count: int = 0

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
    facebook_url: Optional[str] = Field(None, max_length=500, description="Facebook listing/profile URL")
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
    facebook_url: Optional[str] = Field(None, max_length=500)
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
    facebook_url: Optional[str]
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
    owner_is_admin: bool = False  # Whether the owner has admin permissions
    owner_profile_picture: Optional[str] = None  # Profile picture of the owner
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
    user_is_admin: bool = False
    user_profile_picture: Optional[str] = None  # Profile picture of the commenter
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
    sender_is_admin: bool = False
    sender_profile_picture: Optional[str] = None  # Profile picture of the sender
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
    reviewer_profile_picture: Optional[str] = None  # Profile picture of the reviewer
    rated_user_id: str
    rated_user_username: str
    rated_user_profile_picture: Optional[str] = None  # Profile picture of the rated user
    yard_sale_id: Optional[str]
    yard_sale_title: Optional[str]

class UserProfileResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str]
    phone_number: Optional[str]
    company: Optional[str] = None
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    bio: Optional[str]
    profile_picture: Optional[str] = None  # URL to profile picture (optional)
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

# Event Models
class EventCreate(BaseModel):
    type: str = Field(
        default="event", 
        pattern="^(event|informational|advertisement|announcement|lost_found|request_help|offer_help|service_offer|weather|job_posting)$"
    )
    title: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = Field(None)
    category: Optional[str] = Field(None, max_length=50)
    status: str = Field(default="upcoming", pattern="^(upcoming|ongoing|ended|cancelled)$")
    is_public: bool = Field(default=True)
    
    # Location & Time
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    zip: Optional[str] = Field(None, max_length=10)
    location_type: Optional[str] = Field(None, pattern="^(indoor|outdoor|virtual)$", description="Location setting: indoor, outdoor, or virtual")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    timezone: Optional[str] = Field(None, max_length=50)
    
    # Pricing
    price: Optional[float] = Field(None, ge=0, description="Price for paid events, entrance fees, or vendor booth costs")
    is_free: bool = Field(default=False, description="Quick filter toggle for 'free events only'")
    
    # Filtering & Search
    tags: Optional[List[str]] = Field(None, description="List of tags for filtering and search (e.g., ['kids', 'music', 'outdoor'])")
    age_restriction: Optional[str] = Field(None, max_length=20, description="Age restriction (e.g., 'all', '18+', '21+')")
    
    # Job Posting Fields
    job_title: Optional[str] = Field(None, max_length=150, description="Job title for job_posting type events")
    employment_type: Optional[str] = Field(None, pattern="^(full_time|part_time|contract|temporary|seasonal|internship)$", description="Employment type for job_posting events")
    
    # Weather Fields
    weather_conditions: Optional[str] = Field(None, max_length=255, description="Weather conditions for weather type events")
    
    # Organizer
    organizer_name: Optional[str] = Field(None, max_length=150)
    company: Optional[str] = Field(None, max_length=150)
    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_email: Optional[str] = Field(None, max_length=150)
    facebook_url: Optional[str] = Field(None, max_length=255)
    instagram_url: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=255)
    
    # Engagement
    comments_enabled: bool = Field(default=True)
    
    # Media
    gallery_urls: Optional[List[str]] = None
    featured_image: Optional[str] = Field(None, max_length=500)

class EventUpdate(BaseModel):
    type: Optional[str] = Field(
        None, 
        pattern="^(event|informational|advertisement|announcement|lost_found|request_help|offer_help|service_offer|weather|job_posting)$"
    )
    title: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, pattern="^(upcoming|ongoing|ended|cancelled)$")
    is_public: Optional[bool] = None
    
    # Location & Time
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    zip: Optional[str] = Field(None, max_length=10)
    location_type: Optional[str] = Field(None, pattern="^(indoor|outdoor|virtual)$")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    timezone: Optional[str] = Field(None, max_length=50)
    
    # Pricing
    price: Optional[float] = Field(None, ge=0)
    is_free: Optional[bool] = None
    
    # Filtering & Search
    tags: Optional[List[str]] = None
    age_restriction: Optional[str] = Field(None, max_length=20)
    
    # Job Posting Fields
    job_title: Optional[str] = Field(None, max_length=150)
    employment_type: Optional[str] = Field(None, pattern="^(full_time|part_time|contract|temporary|seasonal|internship)$")
    
    # Weather Fields
    weather_conditions: Optional[str] = Field(None, max_length=255)
    
    # Organizer
    organizer_name: Optional[str] = Field(None, max_length=150)
    company: Optional[str] = Field(None, max_length=150)
    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_email: Optional[str] = Field(None, max_length=150)
    facebook_url: Optional[str] = Field(None, max_length=255)
    instagram_url: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=255)
    
    # Engagement
    comments_enabled: Optional[bool] = None
    
    # Media
    gallery_urls: Optional[List[str]] = None
    featured_image: Optional[str] = Field(None, max_length=500)

class EventResponse(BaseModel):
    id: str
    type: str
    title: str
    description: Optional[str]
    category: Optional[str]
    status: str
    is_public: bool
    
    # Location & Time
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    location_type: Optional[str] = None  # indoor, outdoor, virtual
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    timezone: Optional[str] = None
    
    # Pricing
    price: Optional[float] = None
    is_free: bool = False
    
    # Filtering & Search
    tags: Optional[List[str]] = None
    age_restriction: Optional[str] = None
    
    # Job Posting Fields
    job_title: Optional[str] = None
    employment_type: Optional[str] = None  # full_time, part_time, contract, temporary, seasonal, internship
    
    # Weather Fields
    weather_conditions: Optional[str] = None
    
    # Organizer
    organizer_id: str
    organizer_username: str
    organizer_name: Optional[str] = None
    company: Optional[str] = None
    organizer_profile_picture: Optional[str] = None
    organizer_is_admin: bool = False
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    website: Optional[str] = None
    
    # Engagement
    comments_enabled: bool
    comment_count: int = 0
    
    # Media
    gallery_urls: Optional[List[str]] = None
    featured_image: Optional[str] = None
    
    # Metadata
    created_at: datetime
    last_updated: datetime

class EventCommentCreate(BaseModel):
    content: str = Field(..., min_length=1)

class EventCommentResponse(BaseModel):
    id: str
    event_id: str
    user_id: str
    username: str
    user_profile_picture: Optional[str] = None
    user_is_admin: bool = False
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None

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
    # Convert to bytes to check actual byte length (not character length)
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        # Truncate to 72 bytes and decode back to string
        password_bytes = password_bytes[:72]
        password = password_bytes.decode('utf-8', errors='ignore')
    
    # Passlib expects a string, but we need to ensure it won't exceed 72 bytes
    # when passlib encodes it internally
    try:
        return pwd_context.hash(password)
    except ValueError as e:
        # If passlib still complains about length, try one more truncation
        if "72 bytes" in str(e).lower():
            # Double-check byte length
            final_bytes = password.encode('utf-8')
            if len(final_bytes) > 72:
                final_bytes = final_bytes[:72]
                password = final_bytes.decode('utf-8', errors='ignore')
        return pwd_context.hash(password)
        raise

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

def get_user_by_id_helper(db: Session, user_id: str):
    """Get user by ID (helper function)"""
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
        company=user.company,
        city=city,
        state=state,
        zip_code=zip_code,
        bio=user.bio,
        is_active=True,
        permissions="user"  # Always create new users with "user" permission - only admins can change this
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
        company=db_user.company,
        city=db_user.city,
        state=db_user.state,
        zip_code=db_user.zip_code,
        bio=db_user.bio,
        profile_picture=db_user.profile_picture,
        is_active=db_user.is_active,
        permissions=UserPermission(db_user.permissions),
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

@app.post("/docs-login")
async def docs_login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """Login endpoint specifically for docs access - admin only"""
    user = authenticate_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Check if user is admin
    if user.permissions != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to view API documentation"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Create JSON response with token (JavaScript will handle redirect)
    response = JSONResponse(
        content={
            "message": "Login successful",
            "redirect": "/docs",
            "access_token": access_token,  # Include token for localStorage
            "token_type": "bearer"
        }
    )
    
    # Set HTTP-only cookie with token (expires in 3 hours)
    # Use secure=True in production (HTTPS), secure=False for local dev
    is_https = os.getenv("DOMAIN_NAME", "").startswith("https://") or "api.yardsalefinders.com" in os.getenv("DOMAIN_NAME", "")
    response.set_cookie(
        key="docs_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=is_https,  # Only send over HTTPS in production
        samesite="lax"
    )
    
    return response

@app.post("/logout", status_code=status.HTTP_200_OK)
async def logout_user(current_user: User = Depends(get_current_active_user)):
    """Logout user by blacklisting their token"""
    # Note: In a real application, you'd need to store the token to blacklist it
    # For this example, we'll return a success message
    return {"message": "Successfully logged out"}

@app.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        phone_number=current_user.phone_number,
        company=current_user.company,
        city=current_user.city,
        state=current_user.state,
        zip_code=current_user.zip_code,
        bio=current_user.bio,
        profile_picture=current_user.profile_picture,
        is_active=current_user.is_active,
        permissions=UserPermission(current_user.permissions),
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )

@app.put("/me", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile"""
    # Update fields if provided (handle empty strings as None)
    if user_update.full_name is not None:
        value = user_update.full_name.strip() if isinstance(user_update.full_name, str) else user_update.full_name
        current_user.full_name = value if value else None
    if user_update.phone_number is not None:
        value = user_update.phone_number.strip() if isinstance(user_update.phone_number, str) else user_update.phone_number
        current_user.phone_number = value if value else None
    if user_update.city is not None:
        value = user_update.city.strip() if isinstance(user_update.city, str) else user_update.city
        current_user.city = value if value else None
    if user_update.state is not None:
        value = user_update.state.strip() if isinstance(user_update.state, str) else user_update.state
        current_user.state = value if value else None
    if user_update.zip_code is not None:
        value = user_update.zip_code.strip() if isinstance(user_update.zip_code, str) else user_update.zip_code
        current_user.zip_code = value if value else None
    if user_update.bio is not None:
        value = user_update.bio.strip() if isinstance(user_update.bio, str) else user_update.bio
        current_user.bio = value if value else None
    if user_update.profile_picture is not None:
        value = user_update.profile_picture.strip() if isinstance(user_update.profile_picture, str) else user_update.profile_picture
        current_user.profile_picture = value if value else None
    if user_update.company is not None:
        value = user_update.company.strip() if isinstance(user_update.company, str) else user_update.company
        current_user.company = value if value else None
    
    current_user.updated_at = get_mountain_time()
    
    try:
        db.commit()
        db.refresh(current_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        phone_number=current_user.phone_number,
        company=current_user.company,
        city=current_user.city,
        state=current_user.state,
        zip_code=current_user.zip_code,
        bio=current_user.bio,
        profile_picture=current_user.profile_picture,
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

"""Removed legacy /items CRUD and search endpoints in favor of /market-items"""

# Utility Endpoints
@app.get("/payment-methods", response_model=List[str])
async def get_payment_methods():
    """Get list of available payment methods"""
    return get_standard_payment_methods()

# Market Item Endpoints (public marketplace)
@app.post("/market-items", response_model=MarketItemResponse, status_code=status.HTTP_201_CREATED)
async def create_market_item(item: MarketItemCreate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Create a market item (public by default)"""
    # Ensure price is 0 if is_free is True
    final_price = 0.0 if item.is_free else item.price
    final_is_free = item.is_free or (item.price == 0)
    
    db_item = Item(
        name=item.name,
        description=item.description,
        price=final_price,
        original_price=final_price,  # Set original price on creation
        is_available=True,
        is_public=item.is_public,
        status=item.status or "active",
        category=item.category,
        photos=item.photos,
        featured_image=item.featured_image,
        price_range=item.price_range,
        accepts_best_offer=item.accepts_best_offer,
        payment_methods=item.payment_methods,
        venmo_url=item.venmo_url,
        facebook_url=item.facebook_url,
        seller=item.seller,
        contact_phone=item.contact_phone,
        contact_email=item.contact_email,
        city=item.city,
        state=item.state,
        zip_code=item.zip_code,
        condition=item.condition,
        quantity=item.quantity,
        miles=item.miles,
        is_free=final_is_free,
        owner_id=current_user.id
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    price_reduction = calculate_price_reduction_fields(db_item)
    
    # Check if owner is admin
    owner_is_admin = current_user.permissions == "admin"
    
    # Build response manually to avoid duplicate keyword arguments
    return MarketItemResponse(
        id=str(db_item.id),
        name=db_item.name,
        description=db_item.description,
        price=db_item.price,
        is_available=db_item.is_available,
        is_public=db_item.is_public,
        status=db_item.status,
        category=db_item.category,
        photos=db_item.photos,
        featured_image=db_item.featured_image,
        price_range=db_item.price_range,
        accepts_best_offer=db_item.accepts_best_offer,
        payment_methods=db_item.payment_methods,
        venmo_url=db_item.venmo_url,
        facebook_url=db_item.facebook_url,
        seller=db_item.seller,
        contact_phone=db_item.contact_phone,
        contact_email=db_item.contact_email,
        city=db_item.city,
        state=db_item.state,
        zip_code=db_item.zip_code,
        condition=db_item.condition,
        quantity=db_item.quantity,
        miles=db_item.miles,
        is_free=final_is_free,
        comment_count=0,
        created_at=db_item.created_at,
        owner_id=str(db_item.owner_id),
        owner_username=current_user.username,
        owner_is_admin=owner_is_admin,
        owner_profile_picture=current_user.profile_picture,
        is_watched=None,
        **price_reduction
    )

@app.get("/market-items", response_model=MarketItemsPaginatedResponse)
async def list_market_items(
    search: Optional[str] = Query(None, description="Search term to match in name or description"),
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    item_status: Optional[str] = Query(None, pattern="^(active|pending|sold|hidden|all)$", alias="status", description="Filter by status (active, pending, sold, hidden, or all)"),
    accepts_best_offer: Optional[bool] = Query(None, description="Filter items that accept best offers"),
    price_reduced: Optional[bool] = Query(None, description="Filter items with reduced prices"),
    is_free: Optional[bool] = Query(None, description="Filter free items (true) or paid items (false)"),
    owner_is_admin: Optional[bool] = Query(None, description="Filter items by admin owners (true) or non-admin owners (false)"),
    sort_by: Optional[str] = Query(None, pattern="^(price|created_at|price_reduction_percentage|name)$", description="Sort field (price, created_at, price_reduction_percentage, name)"),
    sort_order: Optional[str] = Query(None, pattern="^(asc|desc)$", description="Sort order (asc or desc)"),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Public listing of market items with filtering, sorting, and pagination"""
    try:
        from sqlalchemy.orm import joinedload
        from sqlalchemy.exc import OperationalError, ProgrammingError
        from sqlalchemy import or_, and_
        
        query = db.query(Item)
        
        # Try to add filters, but skip if columns don't exist
        try:
            query = query.filter(Item.is_public == True)
        except (OperationalError, ProgrammingError, AttributeError):
            pass  # Column doesn't exist, skip filter
        
        try:
            if item_status and item_status != "all":
                query = query.filter(Item.status == item_status)
            elif not item_status:
                # Default: exclude hidden and pending items (only show active and sold)
                query = query.filter(Item.status != "hidden", Item.status != "pending")
            # If status is "all", don't filter by status
        except (OperationalError, ProgrammingError, AttributeError):
            pass  # Column doesn't exist, skip filter
        
        # Search filter: searches both name and description
        if search:
            try:
                query = query.filter(
                    or_(
                        Item.name.ilike(f"%{search}%"),
                        Item.description.ilike(f"%{search}%")
                    )
                )
            except (OperationalError, ProgrammingError, AttributeError):
                # Fallback to name only if description column doesn't exist
                try:
                    query = query.filter(Item.name.ilike(f"%{search}%"))
                except Exception:
                    pass
        
        # Category filter
        if category:
            query = query.filter(Item.category == category)
        
        # Price filters
        if min_price is not None:
            query = query.filter(Item.price >= min_price)
        if max_price is not None:
            query = query.filter(Item.price <= max_price)
        
        # Accepts best offer filter
        if accepts_best_offer is not None:
            try:
                query = query.filter(Item.accepts_best_offer == accepts_best_offer)
            except (OperationalError, ProgrammingError, AttributeError):
                pass  # Column doesn't exist, skip filter
        
        # Price reduced filter
        if price_reduced is not None:
            try:
                if price_reduced:
                    # Filter items where price < original_price
                    query = query.filter(
                        and_(
                            Item.original_price.isnot(None),
                            Item.price < Item.original_price,
                            Item.original_price > 0,
                            Item.price > 0
                        )
                    )
                else:
                    # Filter items where price >= original_price or original_price is None
                    query = query.filter(
                        or_(
                            Item.original_price.is_(None),
                            Item.price >= Item.original_price
                        )
                    )
            except (OperationalError, ProgrammingError, AttributeError):
                pass  # Columns don't exist, skip filter
        
        # is_free filter: filter items where is_free = true OR price = 0
        if is_free is not None:
            try:
                if is_free:
                    # Filter free items: is_free = true OR price = 0
                    query = query.filter(
                        or_(
                            Item.is_free == True,
                            Item.price == 0.0
                        )
                    )
                else:
                    # Filter paid items: is_free = false AND price > 0
                    query = query.filter(
                        and_(
                            or_(Item.is_free == False, Item.is_free.is_(None)),
                            Item.price > 0.0
                        )
                    )
            except (OperationalError, ProgrammingError, AttributeError):
                # If is_free column doesn't exist, fallback to price-based filtering
                if is_free:
                    query = query.filter(Item.price == 0.0)
                else:
                    query = query.filter(Item.price > 0.0)
        
        # owner_is_admin filter: filter items by owner's admin status
        if owner_is_admin is not None:
            try:
                # Join with User table to filter by owner permissions
                # Use distinct() to avoid duplicate rows if needed
                from database import User
                query = query.join(User, Item.owner_id == User.id)
                
                if owner_is_admin:
                    # Filter items where owner has admin permissions
                    query = query.filter(User.permissions == "admin")
                else:
                    # Filter items where owner does NOT have admin permissions
                    query = query.filter(User.permissions != "admin")
                
                # Use distinct() to avoid duplicate items if join creates duplicates
                query = query.distinct()
            except (OperationalError, ProgrammingError, AttributeError) as e:
                print(f"Error filtering by owner_is_admin: {e}")
                # If join fails, skip this filter
                pass
        
        # Get total count before pagination (for price_reduced filter calculation)
        try:
            total_count = query.count()
        except Exception as e:
            print(f"Error counting items: {e}")
            total_count = 0
        
        # Sorting
        sort_field = sort_by or "created_at"
        sort_direction = sort_order or "desc"
        
        try:
            if sort_field == "price":
                order_expr = Item.price.desc() if sort_direction == "desc" else Item.price.asc()
            elif sort_field == "name":
                order_expr = Item.name.asc() if sort_direction == "asc" else Item.name.desc()
            elif sort_field == "price_reduction_percentage":
                # Sort by price reduction percentage (calculated)
                # This requires a subquery or raw SQL for accuracy, but we'll sort by (original_price - price) as proxy
                try:
                    if sort_direction == "desc":
                        # Highest reduction first
                        order_expr = (Item.original_price - Item.price).desc()
                    else:
                        order_expr = (Item.original_price - Item.price).asc()
                except Exception:
                    # Fallback to created_at if calculation fails
                    order_expr = Item.created_at.desc()
            else:  # created_at (default)
                order_expr = Item.created_at.desc() if sort_direction == "desc" else Item.created_at.asc()
            
            query = query.order_by(order_expr)
        except (OperationalError, ProgrammingError, AttributeError) as sort_error:
            print(f"Sorting error, using default: {sort_error}")
            # Fallback to default sorting
            query = query.order_by(Item.created_at.desc())
        
        # Apply pagination
        try:
            items = query.options(joinedload(Item.owner)).offset(offset).limit(limit).all()
        except (OperationalError, ProgrammingError) as db_error:
            # If query fails due to missing columns, try a simpler query
            print(f"Query failed with columns, trying simpler query: {db_error}")
            query = db.query(Item)
            if search:
                try:
                    query = query.filter(
                        or_(
                            Item.name.ilike(f"%{search}%"),
                            Item.description.ilike(f"%{search}%")
                        )
                    )
                except Exception:
                    query = query.filter(Item.name.ilike(f"%{search}%"))
            if category:
                query = query.filter(Item.category == category)
            if min_price is not None:
                query = query.filter(Item.price >= min_price)
            if max_price is not None:
                query = query.filter(Item.price <= max_price)
            query = query.order_by(Item.created_at.desc())
            total_count = query.count()
            items = query.options(joinedload(Item.owner)).offset(offset).limit(limit).all()
        
        # Optional current user for is_watched
        current_user = None
        watched_ids: set = set()
        if authorization:
            try:
                current_user = get_optional_user_from_auth_header(authorization, db)
                if current_user:
                    try:
                        watched = db.query(WatchedItem).filter(WatchedItem.user_id == current_user.id).all()
                        watched_ids = {w.item_id for w in watched}
                    except Exception:
                        # WatchedItem table might not exist, skip
                        watched_ids = set()
            except Exception:
                # Auth might fail, continue without user
                current_user = None
                watched_ids = set()
        
        result: List[MarketItemResponse] = []
        for i in items:
            try:
                # Count comments for item (safe if table doesn't exist)
                try:
                    comment_count = db.query(MarketItemComment).filter(MarketItemComment.item_id == i.id).count()
                except Exception:
                    comment_count = 0
                
                price_reduction = calculate_price_reduction_fields(i)
                
                # Ensure we have owner relationship loaded
                owner_username = i.owner.username if i.owner else "unknown"
                owner_is_admin = i.owner.permissions == "admin" if i.owner else False
                
                # Get price reduction fields safely
                original_price = getattr(i, 'original_price', None)
                last_price_change_date = getattr(i, 'last_price_change_date', None)
                
                # Get is_free from database or calculate from price
                is_free = getattr(i, 'is_free', False)
                if not is_free and i.price == 0.0:
                    is_free = True
                
                # Build response manually to avoid duplicate keyword arguments
                result.append(MarketItemResponse(
                    id=str(i.id),
                    name=i.name,
                    description=i.description,
                    price=i.price,
                    is_available=i.is_available,
                    is_public=i.is_public,
                    status=i.status,
                    category=i.category,
                    photos=i.photos,
                    featured_image=i.featured_image,
                    price_range=i.price_range,
                    accepts_best_offer=i.accepts_best_offer,
                    payment_methods=i.payment_methods,
                    venmo_url=i.venmo_url,
                    facebook_url=i.facebook_url,
                    seller=i.seller,
                    contact_phone=i.contact_phone,
                    contact_email=i.contact_email,
                    city=i.city,
                    state=i.state,
                    zip_code=i.zip_code,
                    condition=i.condition,
                    quantity=i.quantity,
                    miles=i.miles,
                    is_free=is_free,
                    comment_count=comment_count,
                    created_at=i.created_at,
                    owner_id=str(i.owner_id),
                    owner_username=owner_username,
                    owner_is_admin=owner_is_admin,
                    owner_profile_picture=i.owner.profile_picture if i.owner else None,
                    is_watched=(i.id in watched_ids) if current_user else None,
                    original_price=original_price,
                    last_price_change_date=last_price_change_date,
                    **price_reduction
                ))
            except Exception as item_error:
                import traceback
                print(f"Error processing item {i.id}: {item_error}")
                print(traceback.format_exc())
                # Skip this item and continue
                continue
        
        # Calculate has_more
        has_more = (offset + len(result)) < total_count
        
        return MarketItemsPaginatedResponse(
            items=result,
            total=total_count,
            limit=limit,
            offset=offset,
            has_more=has_more
        )
    except Exception as e:
        import traceback
        print(f"Error in list_market_items: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}")

# Market Item Messaging Endpoints (must be before /market-items/{item_id} route)
@app.get("/market-items/conversations", response_model=List[MarketItemConversationResponse])
async def get_market_item_conversations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all market item conversations for the current user"""
    # Get all conversations where user is a participant
    conversations = db.query(MarketItemConversation).filter(
        (MarketItemConversation.participant1_id == current_user.id) | 
        (MarketItemConversation.participant2_id == current_user.id)
    ).order_by(MarketItemConversation.updated_at.desc()).all()
    
    result: List[MarketItemConversationResponse] = []
    for conv in conversations:
        # Get item info
        item = db.query(Item).filter(Item.id == conv.item_id).first()
        
        # Get participant usernames
        p1 = db.query(User).filter(User.id == conv.participant1_id).first()
        p2 = db.query(User).filter(User.id == conv.participant2_id).first()
        
        # Get last message
        last_msg = db.query(MarketItemMessage).filter(
            MarketItemMessage.conversation_id == conv.id
        ).order_by(MarketItemMessage.created_at.desc()).first()
        
        last_message_response = None
        if last_msg:
            sender = db.query(User).filter(User.id == last_msg.sender_id).first()
            recipient = db.query(User).filter(User.id == last_msg.recipient_id).first()
            last_message_response = MarketItemMessageResponse(
                id=last_msg.id,
                content=last_msg.content,
                is_read=last_msg.is_read,
                created_at=last_msg.created_at,
                conversation_id=last_msg.conversation_id,
                sender_id=last_msg.sender_id,
                sender_username=sender.username if sender else "unknown",
                sender_is_admin=(sender.permissions == "admin") if sender else False,
                sender_profile_picture=sender.profile_picture if sender else None,
                recipient_id=last_msg.recipient_id,
                recipient_username=recipient.username if recipient else "unknown"
            )
        
        # Count unread messages for current user
        unread_count = db.query(MarketItemMessage).filter(
            MarketItemMessage.conversation_id == conv.id,
            MarketItemMessage.recipient_id == current_user.id,
            MarketItemMessage.is_read == False
        ).count()
        
        result.append(MarketItemConversationResponse(
            id=conv.id,
            item_id=conv.item_id,
            item_name=item.name if item else "Unknown Item",
            participant1_id=conv.participant1_id,
            participant1_username=p1.username if p1 else "unknown",
            participant2_id=conv.participant2_id,
            participant2_username=p2.username if p2 else "unknown",
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            last_message=last_message_response,
            unread_count=unread_count
        ))
    return result

@app.post("/market-items/conversations/{conversation_id}/messages", response_model=MarketItemMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_market_item_conversation_message(
    conversation_id: str,
    message: MarketItemMessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send a message in an existing market item conversation"""
    # Get conversation
    conversation = db.query(MarketItemConversation).filter(MarketItemConversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    
    # Verify user is a participant
    if current_user.id not in [conversation.participant1_id, conversation.participant2_id]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to send messages in this conversation")
    
    # Determine recipient (the other participant)
    recipient_id = conversation.participant2_id if current_user.id == conversation.participant1_id else conversation.participant1_id
    
    # Override with provided recipient_id if specified
    if message.recipient_id:
        if message.recipient_id not in [conversation.participant1_id, conversation.participant2_id]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recipient must be a conversation participant")
        recipient_id = message.recipient_id
    
    # Create message
    db_message = MarketItemMessage(
        content=message.content,
        conversation_id=conversation_id,
        sender_id=current_user.id,
        recipient_id=recipient_id
    )
    db.add(db_message)
    
    # Update conversation updated_at
    conversation.updated_at = get_mountain_time()
    
    db.commit()
    db.refresh(db_message)
    
    # Get usernames
    recipient = db.query(User).filter(User.id == recipient_id).first()
    
    return MarketItemMessageResponse(
        id=db_message.id,
        content=db_message.content,
        is_read=db_message.is_read,
        created_at=db_message.created_at,
        conversation_id=db_message.conversation_id,
        sender_id=current_user.id,
        sender_username=current_user.username,
        sender_is_admin=(current_user.permissions == "admin"),
        sender_profile_picture=current_user.profile_picture,
        recipient_id=recipient_id,
        recipient_username=recipient.username if recipient else "unknown"
    )

@app.get("/market-items/conversations/{conversation_id}/messages", response_model=List[MarketItemMessageResponse])
async def get_market_item_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all messages for a specific market item conversation"""
    # Get conversation
    conversation = db.query(MarketItemConversation).filter(MarketItemConversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    
    # Verify user is a participant
    if current_user.id not in [conversation.participant1_id, conversation.participant2_id]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this conversation")
    
    # Get all messages
    messages = db.query(MarketItemMessage).filter(
        MarketItemMessage.conversation_id == conversation_id
    ).order_by(MarketItemMessage.created_at.asc()).all()
    
    result: List[MarketItemMessageResponse] = []
    for msg in messages:
        sender = db.query(User).filter(User.id == msg.sender_id).first()
        recipient = db.query(User).filter(User.id == msg.recipient_id).first()
        result.append(MarketItemMessageResponse(
            id=msg.id,
            content=msg.content,
            is_read=msg.is_read,
            created_at=msg.created_at,
            conversation_id=msg.conversation_id,
            sender_id=msg.sender_id,
            sender_username=sender.username if sender else "unknown",
            sender_is_admin=(sender.permissions == "admin") if sender else False,
            sender_profile_picture=sender.profile_picture if sender else None,
            recipient_id=msg.recipient_id,
            recipient_username=recipient.username if recipient else "unknown"
        ))
    return result

@app.put("/market-items/messages/{message_id}/read", status_code=status.HTTP_200_OK)
async def mark_market_item_message_read(
    message_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark a market item message as read"""
    message = db.query(MarketItemMessage).filter(MarketItemMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    
    # Only recipient can mark as read
    if message.recipient_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to mark this message as read")
    
    message.is_read = True
    db.commit()
    
    return {"message": "Message marked as read"}

@app.get("/market-items/messages/unread-count", response_model=dict)
async def get_market_item_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get unread message count for market items"""
    unread_count = db.query(MarketItemMessage).filter(
        MarketItemMessage.recipient_id == current_user.id,
        MarketItemMessage.is_read == False
    ).count()
    
    return {"unread_count": unread_count}

@app.post("/market-items/{item_id}/messages", response_model=MarketItemMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_market_item_message(
    item_id: str,
    message: MarketItemMessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send a message to the seller about a market item (creates conversation if needed)"""
    # Get the item
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    # Determine recipient (seller is the item owner)
    seller_id = item.owner_id
    recipient_id = message.recipient_id or seller_id
    
    # Can't message yourself
    if current_user.id == recipient_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot send message to yourself")
    
    # Find or create conversation
    conversation = db.query(MarketItemConversation).filter(
        MarketItemConversation.item_id == item_id,
        ((MarketItemConversation.participant1_id == current_user.id) & (MarketItemConversation.participant2_id == recipient_id)) |
        ((MarketItemConversation.participant1_id == recipient_id) & (MarketItemConversation.participant2_id == current_user.id))
    ).first()
    
    if not conversation:
        # Create new conversation (participant1 is the buyer/inquirer, participant2 is the seller)
        if current_user.id == seller_id:
            # Seller messaging someone (shouldn't happen normally, but handle it)
            conversation = MarketItemConversation(
                item_id=item_id,
                participant1_id=recipient_id,
                participant2_id=current_user.id
            )
        else:
            # Buyer messaging seller
            conversation = MarketItemConversation(
                item_id=item_id,
                participant1_id=current_user.id,
                participant2_id=seller_id
            )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    # Create message
    db_message = MarketItemMessage(
        content=message.content,
        conversation_id=conversation.id,
        sender_id=current_user.id,
        recipient_id=recipient_id
    )
    db.add(db_message)
    
    # Update conversation updated_at
    conversation.updated_at = get_mountain_time()
    
    db.commit()
    db.refresh(db_message)
    
    # Get usernames
    recipient = db.query(User).filter(User.id == recipient_id).first()
    
    return MarketItemMessageResponse(
        id=db_message.id,
        content=db_message.content,
        is_read=db_message.is_read,
        created_at=db_message.created_at,
        conversation_id=db_message.conversation_id,
        sender_id=current_user.id,
        sender_username=current_user.username,
        sender_is_admin=(current_user.permissions == "admin"),
        sender_profile_picture=current_user.profile_picture,
        recipient_id=recipient_id,
        recipient_username=recipient.username if recipient else "unknown"
    )

@app.get("/market-items/{item_id}/messages", response_model=List[MarketItemMessageResponse])
async def get_market_item_messages(
    item_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all messages for a conversation about a specific market item"""
    # Get the item
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    # Find conversation for this item involving current user
    conversation = db.query(MarketItemConversation).filter(
        MarketItemConversation.item_id == item_id,
        ((MarketItemConversation.participant1_id == current_user.id) | (MarketItemConversation.participant2_id == current_user.id))
    ).first()
    
    if not conversation:
        return []  # No conversation yet
    
    # Get all messages for this conversation
    messages = db.query(MarketItemMessage).filter(
        MarketItemMessage.conversation_id == conversation.id
    ).order_by(MarketItemMessage.created_at.asc()).all()
    
    result: List[MarketItemMessageResponse] = []
    for msg in messages:
        sender = db.query(User).filter(User.id == msg.sender_id).first()
        recipient = db.query(User).filter(User.id == msg.recipient_id).first()
        result.append(MarketItemMessageResponse(
            id=msg.id,
            content=msg.content,
            is_read=msg.is_read,
            created_at=msg.created_at,
            conversation_id=msg.conversation_id,
            sender_id=msg.sender_id,
            sender_username=sender.username if sender else "unknown",
            sender_is_admin=(sender.permissions == "admin") if sender else False,
            sender_profile_picture=sender.profile_picture if sender else None,
            recipient_id=msg.recipient_id,
            recipient_username=recipient.username if recipient else "unknown"
        ))
    return result

# Market Item Featured Image Endpoints (must be before /market-items/{item_id} route)
@app.put("/market-items/{item_id}/featured-image", response_model=FeaturedImageResponse)
async def set_market_item_featured_image(
    item_id: str,
    request: Request,
    featured_request: SetFeaturedImageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Set the featured image for a market item (owner only)"""
    item = db.query(Item).filter(
        Item.id == item_id,
        Item.owner_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Market item not found or you don't have permission"
        )
    
    featured_image_url = None
    
    # Determine base URL for image URLs
    forwarded_host = request.headers.get("X-Forwarded-Host")
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
    origin = request.headers.get("Origin")
    
    if forwarded_host:
        base_url = f"{forwarded_proto}://{forwarded_host.split(',')[0].strip()}"
    elif origin:
        base_url = origin.rstrip('/')
    else:
        base_url = str(request.base_url).rstrip('/')
    
    # Method 1: Use provided image_url directly
    if featured_request.image_url:
        featured_image_url = featured_request.image_url
    
    # Method 2: Use image_key to generate URL
    elif featured_request.image_key:
        featured_image_url = f"{base_url}/image-proxy/{featured_request.image_key}"
    
    # Method 3: Use photo_index to get from photos array
    elif featured_request.photo_index is not None:
        if item.photos and isinstance(item.photos, list):
            if 0 <= featured_request.photo_index < len(item.photos):
                featured_image_url = item.photos[featured_request.photo_index]
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Photo index {featured_request.photo_index} is out of range. Market item has {len(item.photos)} photos."
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Market item has no photos to select from"
            )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either image_url, image_key, or photo_index"
        )
    
    # Update the featured image
    item.featured_image = featured_image_url
    db.commit()
    db.refresh(item)
    
    return FeaturedImageResponse(
        success=True,
        message="Featured image set successfully",
        featured_image=featured_image_url
    )

@app.delete("/market-items/{item_id}/featured-image", response_model=FeaturedImageResponse)
async def remove_market_item_featured_image(
    item_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove the featured image from a market item (owner only)"""
    item = db.query(Item).filter(
        Item.id == item_id,
        Item.owner_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Market item not found or you don't have permission"
        )
    
    item.featured_image = None
    db.commit()
    
    return FeaturedImageResponse(
        success=True,
        message="Featured image removed successfully",
        featured_image=None
    )

@app.get("/market-items/{item_id}/images", response_model=dict)
async def get_market_item_images(
    item_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all available images for a market item (photos + user's uploaded images)"""
    item = db.query(Item).filter(Item.id == item_id).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Market item not found"
        )
    
    # Determine base URL for image URLs
    forwarded_host = request.headers.get("X-Forwarded-Host")
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
    origin = request.headers.get("Origin")
    
    if forwarded_host:
        base_url = f"{forwarded_proto}://{forwarded_host.split(',')[0].strip()}"
    elif origin:
        base_url = origin.rstrip('/')
    else:
        base_url = str(request.base_url).rstrip('/')
    
    # Get photos from market item
    photos = item.photos if item.photos else []
    
    # Get user's uploaded images from MinIO (if owner)
    uploaded_images = []
    if item.owner_id == current_user.id:
        try:
            prefix = f"images/{current_user.id}/"
            response = s3_client.list_objects_v2(
                Bucket=MINIO_BUCKET_NAME,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    image_url = f"{base_url}/image-proxy/{obj['Key']}"
                    uploaded_images.append({
                        'key': obj['Key'],
                        'url': image_url,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'filename': obj['Key'].split('/')[-1]
                    })
        except Exception as e:
            print(f"Error fetching uploaded images: {e}")
    
    return {
        "item_id": item_id,
        "featured_image": item.featured_image,
        "photos": photos,
        "uploaded_images": uploaded_images,
        "all_images": photos + [img['url'] for img in uploaded_images]
    }

@app.get("/market-items/{item_id}", response_model=MarketItemResponse)
async def get_market_item(item_id: str, authorization: Optional[str] = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    """Get a single market item (must be public unless hidden)"""
    try:
        from sqlalchemy.orm import joinedload
        item = db.query(Item).options(joinedload(Item.owner)).filter(Item.id == item_id).first()
        if not item or item.status == "hidden":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        comment_count = db.query(MarketItemComment).filter(MarketItemComment.item_id == item.id).count()
        current_user = None
        is_watched = None
        if authorization:
            current_user = get_optional_user_from_auth_header(authorization, db)
            if current_user:
                is_watched = db.query(WatchedItem).filter(WatchedItem.user_id == current_user.id, WatchedItem.item_id == item.id).first() is not None
        price_reduction = calculate_price_reduction_fields(item)
        owner_username = item.owner.username if item.owner else "unknown"
        owner_is_admin = item.owner.permissions == "admin" if item.owner else False
        
        # Get is_free from database or calculate from price
        is_free = getattr(item, 'is_free', False)
        if not is_free and item.price == 0.0:
            is_free = True
        
        # Build response manually to avoid duplicate keyword arguments
        # Extract all fields from item, excluding is_free which we'll pass explicitly
        return MarketItemResponse(
            id=str(item.id),
            name=item.name,
            description=item.description,
            price=item.price,
            is_available=item.is_available,
            is_public=item.is_public,
            status=item.status,
            category=item.category,
            photos=item.photos,
            featured_image=item.featured_image,
            price_range=item.price_range,
            accepts_best_offer=item.accepts_best_offer,
            payment_methods=item.payment_methods,
            venmo_url=item.venmo_url,
            facebook_url=item.facebook_url,
            seller=item.seller,
            contact_phone=item.contact_phone,
            contact_email=item.contact_email,
            city=item.city,
            state=item.state,
            zip_code=item.zip_code,
            condition=item.condition,
            quantity=item.quantity,
            miles=item.miles,
            is_free=is_free,
            comment_count=comment_count,
            created_at=item.created_at,
            owner_id=str(item.owner_id),
            owner_username=owner_username,
            owner_is_admin=owner_is_admin,
            owner_profile_picture=item.owner.profile_picture if item.owner else None,
            is_watched=is_watched,
            **price_reduction
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in get_market_item: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}")

@app.post("/market-items/{item_id}/comments", response_model=MarketItemCommentResponse, status_code=status.HTTP_201_CREATED)
async def create_market_item_comment(
    item_id: str,
    comment: MarketItemCommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    db_comment = MarketItemComment(
        content=comment.content,
        item_id=item_id,
        user_id=current_user.id
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return MarketItemCommentResponse(
        id=db_comment.id,
        content=db_comment.content,
        created_at=db_comment.created_at,
        updated_at=db_comment.updated_at,
        user_id=current_user.id,
        username=current_user.username,
        user_is_admin=(current_user.permissions == "admin"),
        user_profile_picture=current_user.profile_picture,
        item_id=item_id
    )

@app.get("/market-items/{item_id}/comments", response_model=List[MarketItemCommentResponse])
async def get_market_item_comments(item_id: str, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    comments = db.query(MarketItemComment).filter(MarketItemComment.item_id == item_id).order_by(MarketItemComment.created_at.asc()).all()
    result: List[MarketItemCommentResponse] = []
    for c in comments:
        # fetch username
        user = db.query(User).filter(User.id == c.user_id).first()
        result.append(MarketItemCommentResponse(
            id=c.id,
            content=c.content,
            created_at=c.created_at,
            updated_at=c.updated_at,
            user_id=c.user_id,
            username=user.username if user else "",
            user_is_admin=(user.permissions == "admin") if user else False,
            user_profile_picture=user.profile_picture if user else None,
            item_id=c.item_id
        ))
    return result

@app.delete("/market-items/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_market_item_comment(
    comment_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_comment = db.query(MarketItemComment).filter(MarketItemComment.id == comment_id).first()
    if not db_comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    if db_comment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this comment")
    db.delete(db_comment)
    db.commit()
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

@app.post("/market-items/{item_id}/watch", status_code=status.HTTP_204_NO_CONTENT)
async def watch_market_item(item_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    existing = db.query(WatchedItem).filter(WatchedItem.user_id == current_user.id, WatchedItem.item_id == item_id).first()
    if not existing:
        db_watch = WatchedItem(user_id=current_user.id, item_id=item_id)
        db.add(db_watch)
        db.commit()
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

@app.delete("/market-items/{item_id}/watch", status_code=status.HTTP_204_NO_CONTENT)
async def unwatch_market_item(item_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    existing = db.query(WatchedItem).filter(WatchedItem.user_id == current_user.id, WatchedItem.item_id == item_id).first()
    if existing:
        db.delete(existing)
        db.commit()
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

@app.get("/user/watched-items", response_model=List[MarketItemResponse])
async def get_watched_items(
    current_user: User = Depends(get_current_active_user),
    item_status: Optional[str] = Query(None, pattern="^(active|pending|sold|hidden)$", alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get all market items the authenticated user has watched"""
    # Query watched items for the user, joining with items
    query = db.query(WatchedItem, Item).join(Item, WatchedItem.item_id == Item.id).filter(
        WatchedItem.user_id == current_user.id,
        Item.is_public == True
    )
    
    # Filter by status if provided (default: active)
    if item_status:
        query = query.filter(Item.status == item_status)
    else:
        query = query.filter(Item.status == "active")
    
    # Order by most recently watched (watched_items.created_at desc), fallback to item.created_at
    query = query.order_by(WatchedItem.created_at.desc(), Item.created_at.desc())
    
    # Apply pagination
    watched_items_pairs = query.offset(offset).limit(limit).all()
    
    # Build response
    result: List[MarketItemResponse] = []
    for watched_item, item in watched_items_pairs:
        comment_count = db.query(MarketItemComment).filter(MarketItemComment.item_id == item.id).count()
        price_reduction = calculate_price_reduction_fields(item)
        owner_username = item.owner.username if item.owner else "unknown"
        owner_is_admin = item.owner.permissions == "admin" if item.owner else False
        
        # Get is_free from database or calculate from price
        is_free = getattr(item, 'is_free', False)
        if not is_free and item.price == 0.0:
            is_free = True
        
        # Build response manually to avoid duplicate keyword arguments
        result.append(MarketItemResponse(
            id=str(item.id),
            name=item.name,
            description=item.description,
            price=item.price,
            is_available=item.is_available,
            is_public=item.is_public,
            status=item.status,
            category=item.category,
            photos=item.photos,
            featured_image=item.featured_image,
            price_range=item.price_range,
            accepts_best_offer=item.accepts_best_offer,
            payment_methods=item.payment_methods,
            venmo_url=item.venmo_url,
            facebook_url=item.facebook_url,
            seller=item.seller,
            contact_phone=item.contact_phone,
            contact_email=item.contact_email,
            city=item.city,
            state=item.state,
            zip_code=item.zip_code,
            condition=item.condition,
            quantity=item.quantity,
            miles=item.miles,
            is_free=is_free,
            comment_count=comment_count,
            created_at=item.created_at,
            owner_id=str(item.owner_id),
            owner_username=owner_username,
            owner_is_admin=owner_is_admin,
            owner_profile_picture=item.owner.profile_picture if item.owner else None,
            is_watched=True,  # Always true since these are from watchlist
            **price_reduction
        ))
    return result

@app.put("/market-items/{item_id}", response_model=MarketItemResponse)
async def update_market_item(item_id: str, update: MarketItemUpdate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Update a market item (owner only, or admin can edit any item)"""
    # Allow admins to edit any item, otherwise only owner can edit
    if current_user.permissions == "admin":
        item = db.query(Item).filter(Item.id == item_id).first()
    else:
        item = db.query(Item).filter(Item.id == item_id, Item.owner_id == current_user.id).first()
    
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    # Track price changes
    old_price = item.price
    update_data = update.dict(exclude_unset=True)
    
    # Handle is_free and price synchronization
    if "is_free" in update_data or "price" in update_data:
        if update_data.get("is_free") is True:
            # If marking as free, set price to 0
            update_data["price"] = 0.0
            update_data["is_free"] = True
        elif "price" in update_data and update_data["price"] == 0.0:
            # If price is 0, automatically mark as free
            update_data["is_free"] = True
        elif "price" in update_data and update_data["price"] > 0.0 and update_data.get("is_free") is False:
            # If price > 0 and explicitly not free, update is_free
            update_data["is_free"] = False
    
    # If original_price is not set (legacy items), set it to current price before updating
    if item.original_price is None:
        item.original_price = old_price
    
    # Check if price is being changed
    if "price" in update_data:
        new_price = update_data["price"]
        if new_price != old_price:
            item.last_price_change_date = get_mountain_time()
    
    for field, value in update_data.items():
        # Handle empty strings for optional string fields (convert to None)
        if field in ['seller', 'contact_phone', 'contact_email', 'city', 'state', 'zip_code', 'description', 'category', 'condition'] and value == "":
            setattr(item, field, None)
        else:
            setattr(item, field, value)
    
    db.commit()
    db.refresh(item)
    price_reduction = calculate_price_reduction_fields(item)
    
    # Get is_free from database or calculate from price
    is_free = getattr(item, 'is_free', False)
    if not is_free and item.price == 0.0:
        is_free = True
    
    # Check if owner is admin
    owner_is_admin = current_user.permissions == "admin"
    
    # Build response manually to avoid duplicate keyword arguments
    return MarketItemResponse(
        id=str(item.id),
        name=item.name,
        description=item.description,
        price=item.price,
        is_available=item.is_available,
        is_public=item.is_public,
        status=item.status,
        category=item.category,
        photos=item.photos,
        featured_image=item.featured_image,
        price_range=item.price_range,
        accepts_best_offer=item.accepts_best_offer,
        payment_methods=item.payment_methods,
        venmo_url=item.venmo_url,
        facebook_url=item.facebook_url,
        seller=item.seller,
        contact_phone=item.contact_phone,
        contact_email=item.contact_email,
        city=item.city,
        state=item.state,
        zip_code=item.zip_code,
        condition=item.condition,
        quantity=item.quantity,
        miles=item.miles,
        is_free=is_free,
        comment_count=db.query(MarketItemComment).filter(MarketItemComment.item_id == item.id).count(),
        created_at=item.created_at,
        owner_id=str(item.owner_id),
        owner_username=current_user.username,
        owner_is_admin=owner_is_admin,
        owner_profile_picture=current_user.profile_picture,
        is_watched=None,
        **price_reduction
    )

@app.delete("/market-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_market_item(item_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Delete a market item (owner only, or admin can delete any item)"""
    # Allow admins to delete any item, otherwise only owner can delete
    if current_user.permissions == "admin":
        item = db.query(Item).filter(Item.id == item_id).first()
    else:
        item = db.query(Item).filter(Item.id == item_id, Item.owner_id == current_user.id).first()
    
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    try:
        # Delete related records first to avoid foreign key constraint errors
        # Delete item's comments
        db.query(MarketItemComment).filter(MarketItemComment.item_id == item_id).delete()
        
        # Delete item's watched items
        db.query(WatchedItem).filter(WatchedItem.item_id == item_id).delete()
        
        # Delete item's conversations and their messages
        # First get all conversations for this item
        conversations = db.query(MarketItemConversation).filter(MarketItemConversation.item_id == item_id).all()
        conversation_ids = [conv.id for conv in conversations]
        
        # Delete messages in those conversations
        if conversation_ids:
            db.query(MarketItemMessage).filter(MarketItemMessage.conversation_id.in_(conversation_ids)).delete()
        
        # Delete the conversations
        db.query(MarketItemConversation).filter(MarketItemConversation.item_id == item_id).delete()
        
        # Finally, delete the item
        db.delete(item)
        db.commit()
        
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete item: {str(e)}"
        )

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
        facebook_url=yard_sale.facebook_url,
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
    
    # Check if owner is admin
    owner_is_admin = current_user.permissions == "admin"
    
    return YardSaleResponse(
        **db_yard_sale.__dict__,
        owner_username=current_user.username,
        owner_is_admin=owner_is_admin,
        owner_profile_picture=current_user.profile_picture,
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
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
):
    """Get all active yard sales with optional filtering"""
    # Get optional current user for visited status
    current_user = None
    if authorization:
        try:
            current_user = get_optional_user_from_auth_header(authorization, db)
        except Exception:
            # If auth fails, continue without user
            current_user = None
    
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
        
        # Check if owner is admin
        owner_is_admin = yard_sale.owner.permissions == "admin" if yard_sale.owner else False
        
        result.append(YardSaleResponse(
            **yard_sale.__dict__,
            owner_username=yard_sale.owner.username if yard_sale.owner else "unknown",
            owner_is_admin=owner_is_admin,
            owner_profile_picture=yard_sale.owner.profile_picture if yard_sale.owner else None,
            comment_count=comment_count,
            is_visited=is_visited,
            visit_count=visit_count,
            last_visited=last_visited
        ))
    
    return result

# Yard Sale Messaging Endpoints (must be before /yard-sales/{yard_sale_id} route)
@app.post("/yard-sales/{yard_sale_id}/messages", response_model=YardSaleMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_yard_sale_message(
    yard_sale_id: str,
    message: YardSaleMessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send initial message to a yard sale (creates a conversation)"""
    # Get the yard sale
    yard_sale = db.query(YardSale).filter(YardSale.id == yard_sale_id).first()
    if not yard_sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yard sale not found")
    
    # Check if yard sale allows messages
    if not yard_sale.allow_messages:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This yard sale does not allow messages")
    
    # Determine recipient (seller is the yard sale owner)
    seller_id = yard_sale.owner_id
    recipient_id = seller_id
    
    # Can't message yourself
    if current_user.id == recipient_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot send message to yourself")
    
    # Find or create conversation
    conversation = db.query(Conversation).filter(
        Conversation.yard_sale_id == yard_sale_id,
        ((Conversation.participant1_id == current_user.id) & (Conversation.participant2_id == recipient_id)) |
        ((Conversation.participant1_id == recipient_id) & (Conversation.participant2_id == current_user.id))
    ).first()
    
    if not conversation:
        # Create new conversation (participant1 is the buyer/inquirer, participant2 is the seller)
        if current_user.id == seller_id:
            # Seller messaging someone (shouldn't happen normally, but handle it)
            conversation = Conversation(
                yard_sale_id=yard_sale_id,
                participant1_id=recipient_id,
                participant2_id=current_user.id
            )
        else:
            # Buyer messaging seller
            conversation = Conversation(
                yard_sale_id=yard_sale_id,
                participant1_id=current_user.id,
                participant2_id=seller_id
            )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    # Create message
    db_message = Message(
        content=message.content,
        conversation_id=conversation.id,
        sender_id=current_user.id,
        recipient_id=recipient_id
    )
    db.add(db_message)
    
    # Update conversation updated_at
    conversation.updated_at = get_mountain_time()
    
    db.commit()
    db.refresh(db_message)
    
    # Get usernames
    recipient = db.query(User).filter(User.id == recipient_id).first()
    
    return YardSaleMessageResponse(
        id=db_message.id,
        content=db_message.content,
        is_read=db_message.is_read,
        created_at=db_message.created_at,
        conversation_id=db_message.conversation_id,
        sender_id=current_user.id,
        sender_username=current_user.username,
        sender_is_admin=(current_user.permissions == "admin"),
        sender_profile_picture=current_user.profile_picture,
        recipient_id=recipient_id,
        recipient_username=recipient.username if recipient else "unknown",
        yard_sale_id=yard_sale_id
    )

@app.get("/yard-sales/conversations", response_model=List[YardSaleConversationResponse])
async def get_yard_sale_conversations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all yard sale conversations for the current authenticated user"""
    # Get all conversations where user is a participant
    conversations = db.query(Conversation).filter(
        (Conversation.participant1_id == current_user.id) | 
        (Conversation.participant2_id == current_user.id)
    ).order_by(Conversation.updated_at.desc()).all()
    
    result: List[YardSaleConversationResponse] = []
    for conv in conversations:
        # Get yard sale info
        yard_sale = db.query(YardSale).filter(YardSale.id == conv.yard_sale_id).first()
        
        # Get participant usernames
        p1 = db.query(User).filter(User.id == conv.participant1_id).first()
        p2 = db.query(User).filter(User.id == conv.participant2_id).first()
        
        # Get last message
        last_msg = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).order_by(Message.created_at.desc()).first()
        
        last_message_response = None
        if last_msg:
            sender = db.query(User).filter(User.id == last_msg.sender_id).first()
            recipient = db.query(User).filter(User.id == last_msg.recipient_id).first()
            # Handle None timestamp (fallback to current time)
            last_msg_created_at = last_msg.created_at if last_msg.created_at else get_mountain_time()
            last_message_response = YardSaleMessageResponse(
                id=last_msg.id,
                content=last_msg.content,
                is_read=last_msg.is_read,
                created_at=last_msg_created_at,
                conversation_id=last_msg.conversation_id,
                sender_id=last_msg.sender_id,
                sender_username=sender.username if sender else "unknown",
                sender_is_admin=(sender.permissions == "admin") if sender else False,
                sender_profile_picture=sender.profile_picture if sender else None,
                recipient_id=last_msg.recipient_id,
                recipient_username=recipient.username if recipient else "unknown",
                yard_sale_id=conv.yard_sale_id
            )
        
        # Count unread messages for current user
        unread_count = db.query(Message).filter(
            Message.conversation_id == conv.id,
            Message.recipient_id == current_user.id,
            Message.is_read == False
        ).count()
        
        # Handle None timestamps (fallback to current time)
        created_at = conv.created_at if conv.created_at else get_mountain_time()
        updated_at = conv.updated_at if conv.updated_at else get_mountain_time()
        
        result.append(YardSaleConversationResponse(
            id=conv.id,
            yard_sale_id=conv.yard_sale_id,
            yard_sale_title=yard_sale.title if yard_sale else None,
            participant1_id=conv.participant1_id,
            participant1_username=p1.username if p1 else None,
            participant2_id=conv.participant2_id,
            participant2_username=p2.username if p2 else None,
            created_at=created_at,
            updated_at=updated_at,
            last_message=last_message_response,
            unread_count=unread_count
        ))
    return result

@app.get("/yard-sales/conversations/{conversation_id}/messages", response_model=List[YardSaleMessageResponse])
async def get_yard_sale_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all messages for a specific conversation"""
    # Get conversation
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    
    # Verify user is a participant
    if current_user.id not in [conversation.participant1_id, conversation.participant2_id]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this conversation")
    
    # Get all messages
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()
    
    result: List[YardSaleMessageResponse] = []
    for msg in messages:
        sender = db.query(User).filter(User.id == msg.sender_id).first()
        recipient = db.query(User).filter(User.id == msg.recipient_id).first()
        # Handle None timestamp (fallback to current time)
        msg_created_at = msg.created_at if msg.created_at else get_mountain_time()
        result.append(YardSaleMessageResponse(
            id=msg.id,
            content=msg.content,
            is_read=msg.is_read,
            created_at=msg_created_at,
            conversation_id=msg.conversation_id,
            sender_id=msg.sender_id,
            sender_username=sender.username if sender else "unknown",
            sender_is_admin=(sender.permissions == "admin") if sender else False,
            sender_profile_picture=sender.profile_picture if sender else None,
            recipient_id=msg.recipient_id,
            recipient_username=recipient.username if recipient else "unknown",
            yard_sale_id=conversation.yard_sale_id
        ))
    return result

@app.post("/yard-sales/conversations/{conversation_id}/messages", response_model=YardSaleMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_yard_sale_conversation_message(
    conversation_id: str,
    message: YardSaleMessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send a message in an existing conversation"""
    # Get conversation
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    
    # Verify user is a participant
    if current_user.id not in [conversation.participant1_id, conversation.participant2_id]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to send messages in this conversation")
    
    # Determine recipient (the other participant)
    recipient_id = conversation.participant2_id if current_user.id == conversation.participant1_id else conversation.participant1_id
    
    # Create message
    db_message = Message(
        content=message.content,
        conversation_id=conversation_id,
        sender_id=current_user.id,
        recipient_id=recipient_id
    )
    db.add(db_message)
    
    # Update conversation updated_at
    conversation.updated_at = get_mountain_time()
    
    db.commit()
    db.refresh(db_message)
    
    # Get usernames
    recipient = db.query(User).filter(User.id == recipient_id).first()
    
    return YardSaleMessageResponse(
        id=db_message.id,
        content=db_message.content,
        is_read=db_message.is_read,
        created_at=db_message.created_at,
        conversation_id=db_message.conversation_id,
        sender_id=current_user.id,
        sender_username=current_user.username,
        sender_is_admin=(current_user.permissions == "admin"),
        recipient_id=recipient_id,
        recipient_username=recipient.username if recipient else "unknown",
        yard_sale_id=conversation.yard_sale_id
    )

@app.put("/yard-sales/messages/{message_id}/read", status_code=status.HTTP_200_OK)
async def mark_yard_sale_message_read(
    message_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark a specific message as read"""
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    
    # Only recipient can mark as read
    if message.recipient_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to mark this message as read")
    
    message.is_read = True
    db.commit()
    
    return {"success": True}

@app.get("/yard-sales/messages/unread-count", response_model=dict)
async def get_yard_sale_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get total count of unread yard sale messages for current user"""
    # Get conversations where user is a participant
    conversations = db.query(Conversation).filter(
        (Conversation.participant1_id == current_user.id) | 
        (Conversation.participant2_id == current_user.id)
    ).all()
    
    conversation_ids = [conv.id for conv in conversations]
    
    # Count unread messages in these conversations
    unread_count = db.query(Message).filter(
        Message.conversation_id.in_(conversation_ids),
        Message.recipient_id == current_user.id,
        Message.is_read == False
    ).count() if conversation_ids else 0
    
    return {"unread_count": unread_count}

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
    
    # Check if owner is admin
    owner_is_admin = yard_sale.owner.permissions == "admin" if yard_sale.owner else False
    
    return YardSaleResponse(
        **yard_sale.__dict__,
        owner_username=yard_sale.owner.username if yard_sale.owner else "unknown",
        owner_is_admin=owner_is_admin,
        owner_profile_picture=yard_sale.owner.profile_picture if yard_sale.owner else None,
        comment_count=comment_count
    )

@app.put("/yard-sales/{yard_sale_id}", response_model=YardSaleResponse)
async def update_yard_sale(
    yard_sale_id: str, 
    yard_sale_update: YardSaleUpdate, 
    current_user: User = Depends(get_current_active_user), 
    db: Session = Depends(get_db)
):
    """Update a yard sale (owner only, or admin can edit any yard sale)"""
    # Allow admins to edit any yard sale, otherwise only owner can edit
    if current_user.permissions == "admin":
        yard_sale = db.query(YardSale).filter(YardSale.id == yard_sale_id).first()
    else:
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
    
    # Check if owner is admin
    owner_is_admin = yard_sale.owner.permissions == "admin" if yard_sale.owner else False
    
    return YardSaleResponse(
        **yard_sale.__dict__,
        owner_username=yard_sale.owner.username if yard_sale.owner else "unknown",
        owner_is_admin=owner_is_admin,
        owner_profile_picture=yard_sale.owner.profile_picture if yard_sale.owner else None,
        comment_count=comment_count
    )

@app.delete("/yard-sales/{yard_sale_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_yard_sale(
    yard_sale_id: str, 
    current_user: User = Depends(get_current_active_user), 
    db: Session = Depends(get_db)
):
    """Delete a yard sale (owner only, or admin can delete any yard sale)"""
    # Allow admins to delete any yard sale, otherwise only owner can delete
    if current_user.permissions == "admin":
        yard_sale = db.query(YardSale).filter(YardSale.id == yard_sale_id).first()
    else:
        yard_sale = db.query(YardSale).filter(
            YardSale.id == yard_sale_id, 
            YardSale.owner_id == current_user.id
        ).first()
    
    if not yard_sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Yard sale with id {yard_sale_id} not found"
        )
    
    try:
        # Delete related records first to avoid foreign key constraint errors
        # Note: Comments and conversations have cascade delete, but we'll delete messages explicitly
        
        # Get all conversations for this yard sale
        conversations = db.query(Conversation).filter(Conversation.yard_sale_id == yard_sale_id).all()
        conversation_ids = [conv.id for conv in conversations]
        
        # Delete messages in those conversations
        if conversation_ids:
            db.query(Message).filter(Message.conversation_id.in_(conversation_ids)).delete()
        
        # Delete conversations (cascade should handle this, but being explicit)
        db.query(Conversation).filter(Conversation.yard_sale_id == yard_sale_id).delete()
        
        # Delete comments (cascade should handle this, but being explicit)
        db.query(Comment).filter(Comment.yard_sale_id == yard_sale_id).delete()
        
        # Delete yard sale's ratings
        db.query(UserRating).filter(UserRating.yard_sale_id == yard_sale_id).delete()
        
        # Delete yard sale's reports
        db.query(Report).filter(Report.reported_yard_sale_id == yard_sale_id).delete()
        
        # Delete yard sale's visits
        db.query(VisitedYardSale).filter(VisitedYardSale.yard_sale_id == yard_sale_id).delete()
        
        # Delete notifications related to this yard sale
        db.query(Notification).filter(Notification.related_yard_sale_id == yard_sale_id).delete()
        
        # Finally, delete the yard sale
        db.delete(yard_sale)
        db.commit()
        
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete yard sale: {str(e)}"
        )

@app.put("/yard-sales/{yard_sale_id}/featured-image", response_model=FeaturedImageResponse)
async def set_featured_image(
    yard_sale_id: str,
    request: Request,
    featured_request: SetFeaturedImageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Set the featured image for a yard sale (owner only)"""
    yard_sale = db.query(YardSale).filter(
        YardSale.id == yard_sale_id,
        YardSale.owner_id == current_user.id
    ).first()
    
    if not yard_sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Yard sale not found or you don't have permission"
        )
    
    featured_image_url = None
    
    # Determine base URL for image URLs
    forwarded_host = request.headers.get("X-Forwarded-Host")
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
    origin = request.headers.get("Origin")
    
    if forwarded_host:
        base_url = f"{forwarded_proto}://{forwarded_host.split(',')[0].strip()}"
    elif origin:
        base_url = origin.rstrip('/')
    else:
        base_url = str(request.base_url).rstrip('/')
    
    # Method 1: Use provided image_url directly
    if featured_request.image_url:
        featured_image_url = featured_request.image_url
    
    # Method 2: Use image_key to generate URL
    elif featured_request.image_key:
        featured_image_url = f"{base_url}/image-proxy/{featured_request.image_key}"
    
    # Method 3: Use photo_index to get from photos array
    elif featured_request.photo_index is not None:
        if yard_sale.photos and isinstance(yard_sale.photos, list):
            if 0 <= featured_request.photo_index < len(yard_sale.photos):
                featured_image_url = yard_sale.photos[featured_request.photo_index]
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Photo index {featured_request.photo_index} is out of range. Yard sale has {len(yard_sale.photos)} photos."
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Yard sale has no photos to select from"
            )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either image_url, image_key, or photo_index"
        )
    
    # Update the featured image
    yard_sale.featured_image = featured_image_url
    yard_sale.updated_at = get_mountain_time()
    db.commit()
    db.refresh(yard_sale)
    
    return FeaturedImageResponse(
        success=True,
        message="Featured image set successfully",
        featured_image=featured_image_url
    )

@app.delete("/yard-sales/{yard_sale_id}/featured-image", response_model=FeaturedImageResponse)
async def remove_featured_image(
    yard_sale_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove the featured image from a yard sale (owner only)"""
    yard_sale = db.query(YardSale).filter(
        YardSale.id == yard_sale_id,
        YardSale.owner_id == current_user.id
    ).first()
    
    if not yard_sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Yard sale not found or you don't have permission"
        )
    
    yard_sale.featured_image = None
    yard_sale.updated_at = get_mountain_time()
    db.commit()
    
    return FeaturedImageResponse(
        success=True,
        message="Featured image removed successfully",
        featured_image=None
    )

@app.get("/yard-sales/{yard_sale_id}/images", response_model=dict)
async def get_yard_sale_images(
    yard_sale_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all available images for a yard sale (photos + user's uploaded images)"""
    yard_sale = db.query(YardSale).filter(YardSale.id == yard_sale_id).first()
    
    if not yard_sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Yard sale not found"
        )
    
    # Determine base URL for image URLs
    forwarded_host = request.headers.get("X-Forwarded-Host")
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
    origin = request.headers.get("Origin")
    
    if forwarded_host:
        base_url = f"{forwarded_proto}://{forwarded_host.split(',')[0].strip()}"
    elif origin:
        base_url = origin.rstrip('/')
    else:
        base_url = str(request.base_url).rstrip('/')
    
    # Get photos from yard sale
    photos = yard_sale.photos if yard_sale.photos else []
    
    # Get user's uploaded images from MinIO (if owner)
    uploaded_images = []
    if yard_sale.owner_id == current_user.id:
        try:
            prefix = f"images/{current_user.id}/"
            response = s3_client.list_objects_v2(
                Bucket=MINIO_BUCKET_NAME,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    image_url = f"{base_url}/image-proxy/{obj['Key']}"
                    uploaded_images.append({
                        'key': obj['Key'],
                        'url': image_url,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'filename': obj['Key'].split('/')[-1]
                    })
        except Exception as e:
            print(f"Error fetching uploaded images: {e}")
    
    return {
        "yard_sale_id": yard_sale_id,
        "featured_image": yard_sale.featured_image,
        "photos": photos,
        "uploaded_images": uploaded_images,
        "all_images": photos + [img['url'] for img in uploaded_images]
    }

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
        # Check if owner is admin
        owner_is_admin = yard_sale.owner.permissions == "admin" if yard_sale.owner else False
        result.append(YardSaleResponse(
            **yard_sale.__dict__,
            owner_username=yard_sale.owner.username if yard_sale.owner else "unknown",
            owner_is_admin=owner_is_admin,
            owner_profile_picture=yard_sale.owner.profile_picture if yard_sale.owner else None,
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
        username=current_user.username,
        user_is_admin=(current_user.permissions == "admin"),
        user_profile_picture=current_user.profile_picture
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
    
    return [CommentResponse(
        **comment.__dict__, 
        username=comment.user.username,
        user_is_admin=(comment.user.permissions == "admin"),
        user_profile_picture=comment.user.profile_picture
    ) for comment in comments]

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
            sender_is_admin=(sender.permissions == "admin"),
            sender_profile_picture=sender.profile_picture if sender else None,
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
        sender_is_admin=(current_user.permissions == "admin"),
        sender_profile_picture=current_user.profile_picture,
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
            sender_is_admin=(sender.permissions == "admin"),
            sender_profile_picture=sender.profile_picture if sender else None,
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
            sender_is_admin=(current_user.permissions == "admin"),
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
            sender_is_admin=(current_user.permissions == "admin"),
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
        reviewer_profile_picture=current_user.profile_picture,
        rated_user_id=rating.rated_user_id,
        rated_user_username=rated_user.username,
        rated_user_profile_picture=rated_user.profile_picture,
        yard_sale_id=rating.yard_sale_id,
        yard_sale_title=yard_sale.title if yard_sale else None
    )

@app.get("/users/{user_id}/ratings", response_model=List[UserRatingResponse])
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
            reviewer_profile_picture=rating.reviewer.profile_picture if rating.reviewer else None,
            rated_user_id=rating.rated_user_id,
            rated_user_username=rating.rated_user.username,
            rated_user_profile_picture=rating.rated_user.profile_picture if rating.rated_user else None,
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
            reviewer_profile_picture=rating.reviewer.profile_picture if rating.reviewer else None,
            rated_user_id=rating.rated_user_id,
            rated_user_username=rating.rated_user.username,
            rated_user_profile_picture=rating.rated_user.profile_picture if rating.rated_user else None,
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
        company=user.company,
        city=user.city,
        state=user.state,
        zip_code=user.zip_code,
        bio=user.bio,
        profile_picture=user.profile_picture,
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
        company=user.company,
        city=user.city,
        state=user.state,
        zip_code=user.zip_code,
        bio=user.bio,
        profile_picture=user.profile_picture,
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
    
    # Notify all admins about the new report
    try:
        admins = db.query(User).filter(User.permissions == "admin").all()
        
        # Build notification message with report details
        report_target = ""
        if reported_user:
            report_target = f"User: {reported_user.username}"
        elif reported_yard_sale:
            report_target = f"Yard Sale: {reported_yard_sale.title}"
        else:
            report_target = "Unknown target"
        
        notification_title = f"New {report_data.report_type} report"
        notification_message = (
            f"Report submitted by {current_user.username}.\n"
            f"Target: {report_target}\n"
            f"Description: {report_data.description[:200]}{'...' if len(report_data.description) > 200 else ''}"
        )
        
        # Create notification for each admin
        for admin in admins:
            create_notification(
                db=db,
                user_id=admin.id,
                notification_type="report",
                title=notification_title,
                message=notification_message,
                related_user_id=current_user.id,  # The reporter
                related_yard_sale_id=report_data.reported_yard_sale_id
            )
    except Exception as e:
        # Don't fail report creation if notification fails
        print(f"Error notifying admins about report: {e}")
        import traceback
        traceback.print_exc()
    
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
@app.get("/users/{user_id}", response_model=UserProfileResponse)
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
        company=user.company,
        city=user.city,
        state=user.state,
        zip_code=user.zip_code,
        bio=user.bio,
        profile_picture=user.profile_picture,
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
        reviewer_profile_picture=current_user.profile_picture,
        rated_user_id=rating.rated_user_id,
        rated_user_username=rated_user.username,
        rated_user_profile_picture=rated_user.profile_picture,
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

# Event Endpoints
@app.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event: EventCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new event"""
    # Create event
    new_event = Event(
        id=str(uuid.uuid4()),
        type=event.type,
        title=event.title,
        description=event.description,
        category=event.category,
        status=event.status,
        is_public=event.is_public,
        address=event.address,
        city=event.city,
        state=event.state,
        zip=event.zip,
        location_type=event.location_type,
        start_date=event.start_date,
        end_date=event.end_date,
        start_time=event.start_time,
        end_time=event.end_time,
        timezone=event.timezone,
        price=event.price,
        is_free=event.is_free,
        tags=event.tags if event.tags else None,
        age_restriction=event.age_restriction,
        job_title=event.job_title,
        employment_type=event.employment_type,
        weather_conditions=event.weather_conditions,
        organizer_id=current_user.id,
        organizer_name=event.organizer_name or current_user.full_name,
        company=event.company,
        contact_phone=event.contact_phone,
        contact_email=event.contact_email,
        facebook_url=event.facebook_url,
        instagram_url=event.instagram_url,
        website=event.website,
        comments_enabled=event.comments_enabled,
        gallery_urls=event.gallery_urls if event.gallery_urls else None,
        featured_image=event.featured_image,
        created_at=get_mountain_time(),
        last_updated=get_mountain_time()
    )
    
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    
    # Get organizer info
    organizer = get_user_by_id_helper(db, new_event.organizer_id)
    
    # Get comment count
    comment_count = db.query(EventComment).filter(EventComment.event_id == new_event.id).count()
    
    return EventResponse(
        id=new_event.id,
        type=new_event.type,
        title=new_event.title,
        description=new_event.description,
        category=new_event.category,
        status=new_event.status,
        is_public=new_event.is_public,
        address=new_event.address,
        city=new_event.city,
        state=new_event.state,
        zip=new_event.zip,
        location_type=new_event.location_type,
        start_date=new_event.start_date,
        end_date=new_event.end_date,
        start_time=new_event.start_time,
        end_time=new_event.end_time,
        timezone=new_event.timezone,
        price=float(new_event.price) if new_event.price else None,
        is_free=new_event.is_free,
        tags=new_event.tags if new_event.tags else None,
        age_restriction=new_event.age_restriction,
        job_title=new_event.job_title,
        employment_type=new_event.employment_type,
        weather_conditions=new_event.weather_conditions,
        organizer_id=new_event.organizer_id,
        organizer_username=organizer.username,
        organizer_name=new_event.organizer_name,
        company=new_event.company,
        organizer_profile_picture=organizer.profile_picture,
        organizer_is_admin=(organizer.permissions == "admin"),
        contact_phone=new_event.contact_phone,
        contact_email=new_event.contact_email,
        facebook_url=new_event.facebook_url,
        instagram_url=getattr(new_event, 'instagram_url', None),
        website=new_event.website,
        comments_enabled=new_event.comments_enabled,
        comment_count=comment_count,
        gallery_urls=new_event.gallery_urls if new_event.gallery_urls else None,
        featured_image=new_event.featured_image,
        created_at=new_event.created_at,
        last_updated=new_event.last_updated
    )

@app.get("/events", response_model=List[EventResponse])
async def get_events(
    skip: int = 0,
    limit: int = 100,
    type: Optional[str] = None,
    status: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    location_type: Optional[str] = None,
    is_free: Optional[bool] = None,
    category: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated tags
    age_restriction: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all events with optional filtering"""
    query = db.query(Event).filter(Event.is_public == True)
    
    # Apply filters
    if type:
        query = query.filter(Event.type == type)
    if status:
        query = query.filter(Event.status == status)
    if city:
        query = query.filter(Event.city.ilike(f"%{city}%"))
    if state:
        query = query.filter(Event.state.ilike(f"%{state}%"))
    if location_type:
        query = query.filter(Event.location_type == location_type)
    if is_free is not None:
        query = query.filter(Event.is_free == is_free)
    if category:
        query = query.filter(Event.category == category)
    if age_restriction:
        query = query.filter(Event.age_restriction == age_restriction)
    if tags:
        # Filter by tags (JSON contains)
        tag_list = [tag.strip() for tag in tags.split(",")]
        from sqlalchemy import func
        for tag in tag_list:
            query = query.filter(func.json_contains(Event.tags, f'"{tag}"'))
    
    events = query.order_by(Event.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for event in events:
        organizer = get_user_by_id_helper(db, event.organizer_id)
        comment_count = db.query(EventComment).filter(EventComment.event_id == event.id).count()
        
        result.append(EventResponse(
            id=event.id,
            type=event.type,
            title=event.title,
            description=event.description,
            category=event.category,
            status=event.status,
            is_public=event.is_public,
            address=event.address,
            city=event.city,
            state=event.state,
            zip=event.zip,
            location_type=event.location_type,
            start_date=event.start_date,
            end_date=event.end_date,
            start_time=event.start_time,
            end_time=event.end_time,
            timezone=event.timezone,
            price=float(event.price) if event.price else None,
            is_free=event.is_free,
            tags=event.tags if event.tags else None,
            age_restriction=event.age_restriction,
            job_title=event.job_title,
            employment_type=event.employment_type,
            weather_conditions=event.weather_conditions,
            organizer_id=event.organizer_id,
            organizer_username=organizer.username,
            organizer_name=event.organizer_name,
            company=event.company,
            organizer_profile_picture=organizer.profile_picture,
            organizer_is_admin=(organizer.permissions == "admin"),
            contact_phone=event.contact_phone,
            contact_email=event.contact_email,
            facebook_url=event.facebook_url,
            instagram_url=getattr(event, 'instagram_url', None),
            website=event.website,
            comments_enabled=event.comments_enabled,
            comment_count=comment_count,
            gallery_urls=event.gallery_urls if event.gallery_urls else None,
            featured_image=event.featured_image,
            created_at=event.created_at,
            last_updated=event.last_updated
        ))
    
    return result

@app.get("/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, db: Session = Depends(get_db)):
    """Get a specific event by ID"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    organizer = get_user_by_id_helper(db, event.organizer_id)
    comment_count = db.query(EventComment).filter(EventComment.event_id == event.id).count()
    
    return EventResponse(
        id=event.id,
        type=event.type,
        title=event.title,
        description=event.description,
        category=event.category,
        status=event.status,
        is_public=event.is_public,
        address=event.address,
        city=event.city,
        state=event.state,
        zip=event.zip,
        location_type=event.location_type,
        start_date=event.start_date,
        end_date=event.end_date,
        start_time=event.start_time,
        end_time=event.end_time,
        timezone=event.timezone,
        price=float(event.price) if event.price else None,
        is_free=event.is_free,
        tags=event.tags if event.tags else None,
        age_restriction=event.age_restriction,
        job_title=event.job_title,
        employment_type=event.employment_type,
        weather_conditions=event.weather_conditions,
        organizer_id=event.organizer_id,
        organizer_username=organizer.username,
        organizer_name=event.organizer_name,
        company=event.company,
        organizer_profile_picture=organizer.profile_picture,
        organizer_is_admin=(organizer.permissions == "admin"),
        contact_phone=event.contact_phone,
        contact_email=event.contact_email,
        facebook_url=event.facebook_url,
        instagram_url=getattr(event, 'instagram_url', None),
        website=event.website,
        comments_enabled=event.comments_enabled,
        comment_count=comment_count,
        gallery_urls=event.gallery_urls if event.gallery_urls else None,
        featured_image=event.featured_image,
        created_at=event.created_at,
        last_updated=event.last_updated
    )

@app.put("/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    event_update: EventUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an event (organizer only, or admin can edit any event)"""
    # Allow admins to edit any event, otherwise only organizer can edit
    if current_user.permissions == "admin":
        event = db.query(Event).filter(Event.id == event_id).first()
    else:
        event = db.query(Event).filter(
            Event.id == event_id,
            Event.organizer_id == current_user.id
        ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found"
        )
    
    # Update only provided fields
    update_data = event_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "tags" and value is not None:
            setattr(event, field, value)
        elif field == "gallery_urls" and value is not None:
            setattr(event, field, value)
        else:
            setattr(event, field, value)
    
    event.last_updated = get_mountain_time()
    db.commit()
    db.refresh(event)
    
    # Get organizer info
    organizer = get_user_by_id_helper(db, event.organizer_id)
    comment_count = db.query(EventComment).filter(EventComment.event_id == event.id).count()
    
    return EventResponse(
        id=event.id,
        type=event.type,
        title=event.title,
        description=event.description,
        category=event.category,
        status=event.status,
        is_public=event.is_public,
        address=event.address,
        city=event.city,
        state=event.state,
        zip=event.zip,
        location_type=event.location_type,
        start_date=event.start_date,
        end_date=event.end_date,
        start_time=event.start_time,
        end_time=event.end_time,
        timezone=event.timezone,
        price=float(event.price) if event.price else None,
        is_free=event.is_free,
        tags=event.tags if event.tags else None,
        age_restriction=event.age_restriction,
        job_title=event.job_title,
        employment_type=event.employment_type,
        weather_conditions=event.weather_conditions,
        organizer_id=event.organizer_id,
        organizer_username=organizer.username,
        organizer_name=event.organizer_name,
        company=event.company,
        organizer_profile_picture=organizer.profile_picture,
        organizer_is_admin=(organizer.permissions == "admin"),
        contact_phone=event.contact_phone,
        contact_email=event.contact_email,
        facebook_url=event.facebook_url,
        instagram_url=getattr(event, 'instagram_url', None),
        website=event.website,
        comments_enabled=event.comments_enabled,
        comment_count=comment_count,
        gallery_urls=event.gallery_urls if event.gallery_urls else None,
        featured_image=event.featured_image,
        created_at=event.created_at,
        last_updated=event.last_updated
    )

@app.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an event (organizer only, or admin can delete any event)"""
    # Allow admins to delete any event, otherwise only organizer can delete
    if current_user.permissions == "admin":
        event = db.query(Event).filter(Event.id == event_id).first()
    else:
        event = db.query(Event).filter(
            Event.id == event_id,
            Event.organizer_id == current_user.id
        ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found"
        )
    
    # Delete related comments first (cascade should handle this, but being explicit)
    db.query(EventComment).filter(EventComment.event_id == event_id).delete()
    
    # Delete the event
    db.delete(event)
    db.commit()
    
    return None

# Event Comment Endpoints
@app.post("/events/{event_id}/comments", response_model=EventCommentResponse, status_code=status.HTTP_201_CREATED)
async def create_event_comment(
    event_id: str,
    comment: EventCommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a comment on an event"""
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if comments are enabled
    if not event.comments_enabled:
        raise HTTPException(status_code=400, detail="Comments are disabled for this event")
    
    # Create comment
    new_comment = EventComment(
        id=str(uuid.uuid4()),
        event_id=event_id,
        user_id=current_user.id,
        content=comment.content,
        created_at=get_mountain_time(),
        updated_at=None
    )
    
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    
    return EventCommentResponse(
        id=new_comment.id,
        event_id=new_comment.event_id,
        user_id=new_comment.user_id,
        username=current_user.username,
        user_profile_picture=current_user.profile_picture,
        user_is_admin=(current_user.permissions == "admin"),
        content=new_comment.content,
        created_at=new_comment.created_at,
        updated_at=new_comment.updated_at
    )

@app.get("/events/{event_id}/comments", response_model=List[EventCommentResponse])
async def get_event_comments(
    event_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all comments for an event"""
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    comments = db.query(EventComment).filter(
        EventComment.event_id == event_id
    ).order_by(EventComment.created_at.asc()).offset(skip).limit(limit).all()
    
    result = []
    for comment in comments:
        user = get_user_by_id_helper(db, comment.user_id)
        result.append(EventCommentResponse(
            id=comment.id,
            event_id=comment.event_id,
            user_id=comment.user_id,
            username=user.username,
            user_profile_picture=user.profile_picture,
            user_is_admin=(user.permissions == "admin"),
            content=comment.content,
            created_at=comment.created_at,
            updated_at=comment.updated_at
        ))
    
    return result

# Event Featured Image Endpoints
@app.put("/events/{event_id}/featured-image", response_model=FeaturedImageResponse)
async def set_event_featured_image(
    event_id: str,
    request: Request,
    featured_request: SetFeaturedImageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Set the featured image for an event (organizer only, or admin can edit any event)"""
    # Allow admins to edit any event, otherwise only organizer can edit
    if current_user.permissions == "admin":
        event = db.query(Event).filter(Event.id == event_id).first()
    else:
        event = db.query(Event).filter(
            Event.id == event_id,
            Event.organizer_id == current_user.id
        ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found or you don't have permission"
        )
    
    featured_image_url = None
    
    # Determine base URL for image URLs
    forwarded_host = request.headers.get("X-Forwarded-Host")
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
    origin = request.headers.get("Origin")
    
    if forwarded_host:
        base_url = f"{forwarded_proto}://{forwarded_host.split(',')[0].strip()}"
    elif origin:
        base_url = origin.rstrip('/')
    else:
        base_url = str(request.base_url).rstrip('/')
    
    # Method 1: Use provided image_url directly
    if featured_request.image_url:
        featured_image_url = featured_request.image_url
    
    # Method 2: Use image_key to generate URL
    elif featured_request.image_key:
        featured_image_url = f"{base_url}/image-proxy/{featured_request.image_key}"
    
    # Method 3: Use photo_index to get from gallery_urls array
    elif featured_request.photo_index is not None:
        if event.gallery_urls and isinstance(event.gallery_urls, list):
            if 0 <= featured_request.photo_index < len(event.gallery_urls):
                featured_image_url = event.gallery_urls[featured_request.photo_index]
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Photo index {featured_request.photo_index} is out of range. Event has {len(event.gallery_urls)} images in gallery."
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event has no gallery images to select from"
            )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either image_url, image_key, or photo_index"
        )
    
    # Update the featured image
    event.featured_image = featured_image_url
    event.last_updated = get_mountain_time()
    db.commit()
    db.refresh(event)
    
    return FeaturedImageResponse(
        success=True,
        message="Featured image set successfully",
        featured_image=featured_image_url
    )

@app.delete("/events/{event_id}/featured-image", response_model=FeaturedImageResponse)
async def remove_event_featured_image(
    event_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove the featured image from an event (organizer only, or admin can edit any event)"""
    # Allow admins to edit any event, otherwise only organizer can edit
    if current_user.permissions == "admin":
        event = db.query(Event).filter(Event.id == event_id).first()
    else:
        event = db.query(Event).filter(
            Event.id == event_id,
            Event.organizer_id == current_user.id
        ).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found or you don't have permission"
        )
    
    event.featured_image = None
    event.last_updated = get_mountain_time()
    db.commit()
    
    return FeaturedImageResponse(
        success=True,
        message="Featured image removed successfully",
        featured_image=None
    )

@app.get("/events/{event_id}/images", response_model=dict)
async def get_event_images(
    event_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all images for an event (authenticated users only)"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Determine base URL for image URLs
    forwarded_host = request.headers.get("X-Forwarded-Host")
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
    origin = request.headers.get("Origin")
    
    if forwarded_host:
        base_url = f"{forwarded_proto}://{forwarded_host.split(',')[0].strip()}"
    elif origin:
        base_url = origin.rstrip('/')
    else:
        base_url = str(request.base_url).rstrip('/')
    
    # Get images from MinIO
    try:
        images = []
        paginator = s3_client.get_paginator('list_objects_v2')
        user_folder = f"images/{current_user.id}/"
        
        for page in paginator.paginate(Bucket=MINIO_BUCKET_NAME, Prefix=user_folder):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if key.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                        image_url = f"{base_url}/image-proxy/{key}"
                        images.append({
                            "key": key,
                            "url": image_url,
                            "size": obj['Size'],
                            "last_modified": obj['LastModified'].isoformat() if obj.get('LastModified') else None,
                            "filename": key.split('/')[-1]
                        })
        
        return {
            "images": images,
            "total": len(images),
            "event_gallery_urls": event.gallery_urls if event.gallery_urls else [],
            "featured_image": event.featured_image
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load images: {str(e)}"
        )

# Admin-only endpoints
@app.get("/admin/users", response_model=dict)
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all users (admin only) with pagination"""
    try:
        query = db.query(User)
        
        # Search filter (username or email)
        if search:
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    User.username.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                    User.full_name.ilike(f"%{search}%")
                )
            )
        
        total_count = query.count()
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        
        result = [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            phone_number=user.phone_number,
            company=user.company,
            city=user.city,
            state=user.state,
            zip_code=user.zip_code,
            bio=user.bio,
            profile_picture=user.profile_picture,
            is_active=user.is_active,
            permissions=UserPermission(user.permissions),
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        for user in users
    ]
        
        return {
            "users": result,
            "total": total_count,
            "limit": limit,
            "offset": skip,
            "has_more": (skip + len(result)) < total_count
        }
    except Exception as e:
        import traceback
        print(f"Error getting admin users: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/admin/users/{user_id}", response_model=UserResponse)
async def get_user_by_id_admin(
    user_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get user by ID (admin only)"""
    user = get_user_by_id_helper(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        company=user.company,
        city=user.city,
        state=user.state,
        zip_code=user.zip_code,
        bio=user.bio,
        profile_picture=user.profile_picture,
        is_active=user.is_active,
        permissions=UserPermission(user.permissions),
        created_at=user.created_at,
        updated_at=user.updated_at
    )

class UserUpdateAdmin(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None)
    phone_number: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=150, description="Company name (optional)")
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=2)
    zip_code: Optional[str] = Field(None, max_length=10)
    bio: Optional[str] = Field(None, max_length=1000)
    profile_picture: Optional[str] = Field(None, max_length=500, description="URL to profile picture (optional)")
    is_active: Optional[bool] = None
    permissions: Optional[str] = Field(None, description="User permission level: 'user', 'moderator', or 'admin'")
    
    def model_post_init(self, __context):
        """Validate permissions value if provided"""
        if self.permissions is not None:
            valid_permissions = ["user", "moderator", "admin"]
            if self.permissions not in valid_permissions:
                raise ValueError(f"permissions must be one of: {', '.join(valid_permissions)}")

@app.put("/admin/users/{user_id}", response_model=UserResponse)
async def update_user_admin(
    user_id: str,
    user_update: UserUpdateAdmin,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update user (admin only)"""
    user = get_user_by_id_helper(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields if provided (handle empty strings as None)
    if user_update.full_name is not None:
        value = user_update.full_name.strip() if isinstance(user_update.full_name, str) else user_update.full_name
        user.full_name = value if value else None
    if user_update.email is not None:
        value = user_update.email.strip() if isinstance(user_update.email, str) else user_update.email
        user.email = value if value else None
    if user_update.phone_number is not None:
        value = user_update.phone_number.strip() if isinstance(user_update.phone_number, str) else user_update.phone_number
        user.phone_number = value if value else None
    if user_update.city is not None:
        value = user_update.city.strip() if isinstance(user_update.city, str) else user_update.city
        user.city = value if value else None
    if user_update.state is not None:
        value = user_update.state.strip() if isinstance(user_update.state, str) else user_update.state
        user.state = value if value else None
    if user_update.zip_code is not None:
        value = user_update.zip_code.strip() if isinstance(user_update.zip_code, str) else user_update.zip_code
        user.zip_code = value if value else None
    if user_update.bio is not None:
        value = user_update.bio.strip() if isinstance(user_update.bio, str) else user_update.bio
        user.bio = value if value else None
    if user_update.profile_picture is not None:
        value = user_update.profile_picture.strip() if isinstance(user_update.profile_picture, str) else user_update.profile_picture
        user.profile_picture = value if value else None
    if user_update.company is not None:
        value = user_update.company.strip() if isinstance(user_update.company, str) else user_update.company
        user.company = value if value else None
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    if user_update.permissions is not None:
        # Permissions is now a string (validated in the model)
        user.permissions = user_update.permissions
    
    user.updated_at = get_mountain_time()
    
    try:
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        company=user.company,
        city=user.city,
        state=user.state,
        zip_code=user.zip_code,
        bio=user.bio,
        profile_picture=user.profile_picture,
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
    user = get_user_by_id_helper(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    try:
        # Delete related records first to avoid foreign key constraint errors
        # Order matters: delete child records before parent records
        
        # Step 1: Delete messages in conversations (must be before conversations)
        # Get all conversations the user is part of
        user_conversations = db.query(Conversation).filter(
            (Conversation.participant1_id == user.id) | (Conversation.participant2_id == user.id)
        ).all()
        conversation_ids = [conv.id for conv in user_conversations]
        if conversation_ids:
            db.query(Message).filter(Message.conversation_id.in_(conversation_ids)).delete()
        
        # Get all market item conversations the user is part of
        user_market_conversations = db.query(MarketItemConversation).filter(
            (MarketItemConversation.participant1_id == user.id) | (MarketItemConversation.participant2_id == user.id)
        ).all()
        market_conversation_ids = [conv.id for conv in user_market_conversations]
        if market_conversation_ids:
            db.query(MarketItemMessage).filter(MarketItemMessage.conversation_id.in_(market_conversation_ids)).delete()
        
        # Step 2: Get user's yard sales and items IDs first (needed for proper deletion order)
        user_yard_sales = db.query(YardSale).filter(YardSale.owner_id == user.id).all()
        yard_sale_ids = [ys.id for ys in user_yard_sales] if user_yard_sales else []
        
        user_items = db.query(Item).filter(Item.owner_id == user.id).all()
        item_ids = [item.id for item in user_items] if user_items else []
        
        # Step 3: Delete comments on user's yard sales (must be before deleting yard sales)
        if yard_sale_ids:
            db.query(Comment).filter(Comment.yard_sale_id.in_(yard_sale_ids)).delete()
        
        # Step 4: Delete comments on user's items (must be before deleting items)
        if item_ids:
            db.query(MarketItemComment).filter(MarketItemComment.item_id.in_(item_ids)).delete()
        
        # Step 5: Delete conversations related to user's yard sales (must be before deleting yard sales)
        if yard_sale_ids:
            yard_conversations = db.query(Conversation).filter(Conversation.yard_sale_id.in_(yard_sale_ids)).all()
            yard_conv_ids = [conv.id for conv in yard_conversations]
            if yard_conv_ids:
                db.query(Message).filter(Message.conversation_id.in_(yard_conv_ids)).delete()
            db.query(Conversation).filter(Conversation.yard_sale_id.in_(yard_sale_ids)).delete()
        
        # Step 6: Delete conversations related to user's items (must be before deleting items)
        if item_ids:
            item_conversations = db.query(MarketItemConversation).filter(MarketItemConversation.item_id.in_(item_ids)).all()
            item_conv_ids = [conv.id for conv in item_conversations]
            if item_conv_ids:
                db.query(MarketItemMessage).filter(MarketItemMessage.conversation_id.in_(item_conv_ids)).delete()
            db.query(MarketItemConversation).filter(MarketItemConversation.item_id.in_(item_ids)).delete()
        
        # Step 7: Delete conversations where user is a participant (not related to user's yard sales/items)
        db.query(Conversation).filter(Conversation.participant1_id == user.id).delete()
        db.query(Conversation).filter(Conversation.participant2_id == user.id).delete()
        db.query(MarketItemConversation).filter(MarketItemConversation.participant1_id == user.id).delete()
        db.query(MarketItemConversation).filter(MarketItemConversation.participant2_id == user.id).delete()
        
        # Step 8: Delete comments made by user (not on user's yard sales/items/events - those are already deleted)
        db.query(Comment).filter(Comment.user_id == user.id).delete()
        db.query(MarketItemComment).filter(MarketItemComment.user_id == user.id).delete()
        db.query(EventComment).filter(EventComment.user_id == user.id).delete()
        
        # Step 9: Delete messages sent/received by user (standalone messages)
        db.query(Message).filter(Message.sender_id == user.id).delete()
        db.query(Message).filter(Message.recipient_id == user.id).delete()
        db.query(MarketItemMessage).filter(MarketItemMessage.sender_id == user.id).delete()
        db.query(MarketItemMessage).filter(MarketItemMessage.recipient_id == user.id).delete()
        
        # Step 10: Delete user's items (market items) - related records already deleted
        if item_ids:
            db.query(WatchedItem).filter(WatchedItem.item_id.in_(item_ids)).delete()
        db.query(Item).filter(Item.owner_id == user.id).delete()
        
        # Step 11: Delete user's yard sales - related records already deleted
        if yard_sale_ids:
            # Delete ratings for user's yard sales
            db.query(UserRating).filter(UserRating.yard_sale_id.in_(yard_sale_ids)).delete()
            # Delete reports for user's yard sales
            db.query(Report).filter(Report.reported_yard_sale_id.in_(yard_sale_ids)).delete()
            # Delete visits for user's yard sales
            db.query(VisitedYardSale).filter(VisitedYardSale.yard_sale_id.in_(yard_sale_ids)).delete()
            # Delete notifications for user's yard sales
            db.query(Notification).filter(Notification.related_yard_sale_id.in_(yard_sale_ids)).delete()
        db.query(YardSale).filter(YardSale.owner_id == user.id).delete()
        
        # Step 12: Delete user's events - comments will cascade
        user_events = db.query(Event).filter(Event.organizer_id == user.id).all()
        event_ids = [event.id for event in user_events] if user_events else []
        if event_ids:
            # Delete comments on user's events (cascade should handle this, but being explicit)
            db.query(EventComment).filter(EventComment.event_id.in_(event_ids)).delete()
        db.query(Event).filter(Event.organizer_id == user.id).delete()
        
        # Delete user's ratings (both given and received)
        db.query(UserRating).filter(UserRating.reviewer_id == user.id).delete()
        db.query(UserRating).filter(UserRating.rated_user_id == user.id).delete()
        
        # Delete user's reports
        db.query(Report).filter(Report.reporter_id == user.id).delete()
        
        # Delete user's watched items
        db.query(WatchedItem).filter(WatchedItem.user_id == user.id).delete()
        
        # Delete user's visited yard sales
        db.query(VisitedYardSale).filter(VisitedYardSale.user_id == user.id).delete()
        
        # Delete user's notifications
        db.query(Notification).filter(Notification.user_id == user.id).delete()
        db.query(Notification).filter(Notification.related_user_id == user.id).delete()
        
        # Delete user's verifications
        db.query(Verification).filter(Verification.user_id == user.id).delete()
        
        # Finally, delete the user
        db.delete(user)
        db.commit()
        
        return {"message": "User deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )

# Admin Dashboard Endpoints
@app.get("/admin/dashboard/stats", response_model=dict)
async def get_admin_dashboard_stats(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get admin dashboard statistics"""
    try:
        total_users = db.query(User).count()
        total_items = db.query(Item).count()
        total_yard_sales = db.query(YardSale).count()
        active_items = db.query(Item).filter(Item.status == "active", Item.is_public == True).count()
        active_yard_sales = db.query(YardSale).filter(YardSale.is_active == True).count()
        from sqlalchemy import or_
        free_items = db.query(Item).filter(
            or_(Item.is_free == True, Item.price == 0.0)
        ).count()
        admin_users = db.query(User).filter(User.permissions == "admin").count()
        
        # Recent activity (last 7 days)
        from datetime import timedelta
        seven_days_ago = get_mountain_time() - timedelta(days=7)
        recent_items = db.query(Item).filter(Item.created_at >= seven_days_ago).count()
        recent_yard_sales = db.query(YardSale).filter(YardSale.created_at >= seven_days_ago).count()
        recent_users = db.query(User).filter(User.created_at >= seven_days_ago).count()
        
        return {
            "total_users": total_users,
            "total_items": total_items,
            "total_yard_sales": total_yard_sales,
            "active_items": active_items,
            "active_yard_sales": active_yard_sales,
            "free_items": free_items,
            "admin_users": admin_users,
            "recent_activity": {
                "items_last_7_days": recent_items,
                "yard_sales_last_7_days": recent_yard_sales,
                "users_last_7_days": recent_users
            }
        }
    except Exception as e:
        import traceback
        print(f"Error getting dashboard stats: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/admin/items", response_model=dict)
async def get_all_items_admin(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all market items (admin only) - includes hidden items"""
    try:
        from sqlalchemy import or_
        query = db.query(Item)
        
        if status:
            query = query.filter(Item.status == status)
        
        total_count = query.count()
        items = query.order_by(Item.created_at.desc()).offset(skip).limit(limit).all()
        
        result = []
        for item in items:
            owner = db.query(User).filter(User.id == item.owner_id).first()
            comment_count = db.query(MarketItemComment).filter(MarketItemComment.item_id == item.id).count()
            is_free = getattr(item, 'is_free', False) or item.price == 0.0
            
            result.append({
                "id": str(item.id),
                "name": item.name,
                "description": item.description,
                "price": item.price,
                "is_free": is_free,
                "status": item.status,
                "is_public": item.is_public,
                "category": item.category,
                "owner_id": str(item.owner_id),
                "owner_username": owner.username if owner else "unknown",
                "owner_is_admin": owner.permissions == "admin" if owner else False,
                "owner_profile_picture": owner.profile_picture if owner else None,
                "comment_count": comment_count,
                "created_at": item.created_at.isoformat() if item.created_at else None
            })
        
        return {
            "items": result,
            "total": total_count,
            "limit": limit,
            "offset": skip,
            "has_more": (skip + len(result)) < total_count
        }
    except Exception as e:
        import traceback
        print(f"Error getting admin items: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/admin/yard-sales", response_model=dict)
async def get_all_yard_sales_admin(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all yard sales (admin only) - includes inactive/hidden sales"""
    try:
        query = db.query(YardSale)
        
        if status:
            query = query.filter(YardSale.status == status)
        
        total_count = query.count()
        yard_sales = query.order_by(YardSale.created_at.desc()).offset(skip).limit(limit).all()
        
        result = []
        for yard_sale in yard_sales:
            owner = db.query(User).filter(User.id == yard_sale.owner_id).first()
            comment_count = db.query(Comment).filter(Comment.yard_sale_id == yard_sale.id).count()
            
            result.append({
                "id": str(yard_sale.id),
                "title": yard_sale.title,
                "description": yard_sale.description,
                "city": yard_sale.city,
                "state": yard_sale.state,
                "status": yard_sale.status,
                "is_active": yard_sale.is_active,
                "owner_id": str(yard_sale.owner_id),
                "owner_username": owner.username if owner else "unknown",
                "owner_is_admin": owner.permissions == "admin" if owner else False,
                "owner_profile_picture": owner.profile_picture if owner else None,
                "comment_count": comment_count,
                "created_at": yard_sale.created_at.isoformat() if yard_sale.created_at else None,
                "start_date": yard_sale.start_date.isoformat() if yard_sale.start_date else None
            })
        
        return {
            "yard_sales": result,
            "total": total_count,
            "limit": limit,
            "offset": skip,
            "has_more": (skip + len(result)) < total_count
        }
    except Exception as e:
        import traceback
        print(f"Error getting admin yard sales: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/admin/events", response_model=dict)
async def get_all_events_admin(
    skip: int = 0,
    limit: int = 100,
    type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all events (admin only) - includes private events"""
    try:
        query = db.query(Event)
        
        if type:
            query = query.filter(Event.type == type)
        if status:
            query = query.filter(Event.status == status)
        
        total_count = query.count()
        events = query.order_by(Event.created_at.desc()).offset(skip).limit(limit).all()
        
        result = []
        for event in events:
            organizer = get_user_by_id_helper(db, event.organizer_id)
            comment_count = db.query(EventComment).filter(EventComment.event_id == event.id).count()
            
            result.append({
                "id": str(event.id),
                "type": event.type,
                "title": event.title,
                "description": event.description,
                "category": event.category,
                "status": event.status,
                "is_public": event.is_public,
                "city": event.city,
                "state": event.state,
                "location_type": event.location_type,
                "is_free": event.is_free,
                "price": float(event.price) if event.price else None,
                "organizer_id": str(event.organizer_id),
                "organizer_username": organizer.username if organizer else "unknown",
                "organizer_is_admin": organizer.permissions == "admin" if organizer else False,
                "organizer_profile_picture": organizer.profile_picture if organizer else None,
                "comment_count": comment_count,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "last_updated": event.last_updated.isoformat() if event.last_updated else None
            })
        
        return {
            "events": result,
            "total": total_count,
            "limit": limit,
            "offset": skip,
            "has_more": (skip + len(result)) < total_count
        }
    except Exception as e:
        import traceback
        print(f"Error getting admin events: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

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
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload an image to MinIO S3 storage"""
    import traceback
    try:
        print(f"📤 Starting image upload for user {current_user.username}")
        print(f"🔗 MinIO Endpoint: {MINIO_ENDPOINT_URL}")
        print(f"📦 Bucket: {MINIO_BUCKET_NAME}")
        
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )
        
        # Validate file size (max 10MB)
        file_content = await file.read()
        print(f"📏 File size: {len(file_content)} bytes")
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size must be less than 10MB"
            )
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix if file.filename else '.jpg'
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        s3_key = f"images/{current_user.id}/{unique_filename}"
        print(f"🔑 S3 Key: {s3_key}")
        
        # Test connection first
        try:
            print("🔍 Testing MinIO connection...")
            s3_client.head_bucket(Bucket=MINIO_BUCKET_NAME)
            print("✅ Bucket access confirmed")
        except Exception as conn_error:
            print(f"❌ Connection test failed: {conn_error}")
            print(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cannot connect to MinIO: {str(conn_error)}"
            )
        
        # Upload to MinIO S3
        # MinIO is strict about signed headers - start with minimal headers
        print("⬆️ Uploading to MinIO...")
        put_params = {
            'Bucket': MINIO_BUCKET_NAME,
            'Key': s3_key,
            'Body': file_content,
            'ContentType': file.content_type
        }
        
        # Only add metadata if needed (can cause signature issues with some MinIO configs)
        # Uncomment below if you need metadata:
        # put_params['Metadata'] = {
        #     'uploaded-by': current_user.username,
        #     'uploaded-at': datetime.now().isoformat(),
        #     'original-filename': file.filename or 'unknown'
        # }
        
        s3_client.put_object(**put_params)
        print("✅ Upload successful")
        
        # Generate proxy URL using request origin (works for both localhost and IP access)
        # Check for X-Forwarded-Host header (used by reverse proxies like Vite)
        forwarded_host = request.headers.get("X-Forwarded-Host")
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
        origin = request.headers.get("Origin")
        
        if forwarded_host:
            # Use forwarded host from proxy (e.g., from Vite dev server)
            base_url = f"{forwarded_proto}://{forwarded_host.split(',')[0].strip()}"
        elif origin:
            # Use Origin header (frontend's actual URL)
            base_url = origin.rstrip('/')
        else:
            # Fallback to request.base_url
            base_url = str(request.base_url).rstrip('/')
        
        image_url = f"{base_url}/image-proxy/{s3_key}"
        print(f"🌐 Using base URL: {base_url} (from {forwarded_host or origin or 'request.base_url'})")
        
        return ImageUploadResponse(
            success=True,
            message="Image uploaded successfully",
            image_url=image_url,
            file_name=unique_filename,
            file_size=len(file_content)
        )
        
    except ClientError as e:
        error_code = 'Unknown'
        error_message = str(e)
        try:
            if hasattr(e, 'response') and e.response:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_message = e.response.get('Error', {}).get('Message', str(e))
        except:
            pass
        
        error_details = {
            'error_code': error_code,
            'error_message': error_message,
            'endpoint': MINIO_ENDPOINT_URL,
            'bucket': MINIO_BUCKET_NAME
        }
        print(f"❌ MinIO ClientError during upload:")
        print(f"   Error Code: {error_code}")
        print(f"   Error Message: {error_message}")
        print(f"   Endpoint: {MINIO_ENDPOINT_URL}")
        print(f"   Bucket: {MINIO_BUCKET_NAME}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {error_message} (Code: {error_code})"
        )
    except HTTPException:
        # Re-raise HTTP exceptions (like validation errors)
        raise
    except Exception as e:
        print(f"❌ Unexpected error during image upload:")
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Error Message: {str(e)}")
        print(f"   Endpoint: {MINIO_ENDPOINT_URL}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )

@app.get("/images", response_model=ImageListResponse)
async def list_user_images(
    request: Request,
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
        
        # Determine base URL for image URLs using request origin
        # Check for X-Forwarded-Host header (used by reverse proxies like Vite)
        forwarded_host = request.headers.get("X-Forwarded-Host")
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
        origin = request.headers.get("Origin")
        
        if forwarded_host:
            # Use forwarded host from proxy (e.g., from Vite dev server)
            base_url = f"{forwarded_proto}://{forwarded_host.split(',')[0].strip()}"
        elif origin:
            # Use Origin header (frontend's actual URL)
            base_url = origin.rstrip('/')
        else:
            # Fallback to request.base_url
            base_url = str(request.base_url).rstrip('/')
        
        images = []
        if 'Contents' in response:
            for obj in response['Contents']:
                image_url = f"{base_url}/image-proxy/{obj['Key']}"
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
        #         detail="You can only access your own image"
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

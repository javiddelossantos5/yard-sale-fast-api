#!/bin/bash
# Run FastAPI locally for development
# This script loads environment variables and starts the server with auto-reload

set -e

echo "🚀 Starting local development server..."
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "   Creating .env from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "   ✅ Created .env file"
        echo "   ⚠️  Please update .env with your local MySQL credentials"
        echo ""
    else
        echo "   ❌ .env.example not found either"
        echo "   Please create .env file manually"
        exit 1
    fi
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Check if database is accessible
echo "🔍 Checking database connection..."
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
db_url = os.getenv('DATABASE_URL', '')
if 'fastapi_db_dev' in db_url:
    print('   ✅ Database URL configured for dev')
else:
    print('   ⚠️  Warning: Database URL might not be for dev environment')
" || echo "   ⚠️  Could not verify database URL"

echo ""
echo "🌐 Starting FastAPI server..."
echo "   Local URL: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo "   ReDoc: http://localhost:8000/redoc"
echo ""
echo "   Press Ctrl+C to stop"
echo ""

# Run with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000


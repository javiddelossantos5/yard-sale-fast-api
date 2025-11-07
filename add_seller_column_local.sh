#!/bin/bash
# Script to add the 'seller' column to the items table (LOCAL DEVELOPMENT)
# Uses Python script that connects via the same database connection as the app

echo "🚀 Adding 'seller' column to items table (LOCAL DEV)..."
echo ""

# Check if venv exists and activate it
if [ -d "venv" ]; then
    echo "🔌 Activating virtual environment..."
    source venv/bin/activate
    echo "✅ Virtual environment activated"
    echo ""
elif [ -d ".venv" ]; then
    echo "🔌 Activating virtual environment..."
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
    echo ""
fi

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python not found in PATH"
    echo ""
    echo "💡 Please run this SQL directly in TablePlus:"
    echo ""
    echo "   ALTER TABLE items"
    echo "   ADD COLUMN seller VARCHAR(100) NULL COMMENT 'Seller name/contact name (optional)'"
    echo "   AFTER facebook_url;"
    echo ""
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# Run the Python script
$PYTHON_CMD add_seller_column.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Script completed!"
else
    echo ""
    echo "💡 If the script failed, you can run the SQL directly in TablePlus:"
    echo ""
    echo "   ALTER TABLE items"
    echo "   ADD COLUMN seller VARCHAR(100) NULL COMMENT 'Seller name/contact name (optional)'"
    echo "   AFTER facebook_url;"
    exit 1
fi


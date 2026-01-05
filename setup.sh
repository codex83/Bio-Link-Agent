#!/bin/bash

# Bio-Link Agent Setup Script
# This script sets up the virtual environment and installs dependencies

set -e  # Exit on error

echo "=========================================="
echo "Bio-Link Agent Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "⚠️  Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies (this may take a few minutes)..."
pip install -r requirements.txt

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Create .env file with your credentials (see SETUP_TEST_GUIDE.md)"
echo ""
echo "3. Run tests:"
echo "   python test_setup.py"
echo ""
echo "4. Run the app:"
echo "   streamlit run app.py"
echo ""


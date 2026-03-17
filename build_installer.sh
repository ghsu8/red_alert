#!/bin/bash
# Build script for Red Alert installer (for Linux/Mac developers)
# This creates the executable that can then be packaged with NSIS on Windows

echo "======================================"
echo "   Red Alert Application Builder"
echo "======================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    exit 1
fi

echo "✓ Python found: $(python3 --version)"
echo ""

# Install dependencies
echo "Installing dependencies..."
python3 -m pip install -q -r requirements.txt

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

# Install PyInstaller
echo "Installing PyInstaller..."
python3 -m pip install -q pyinstaller

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Build executable
echo ""
echo "Running PyInstaller..."
python3 -m PyInstaller --name "Red Alert" \
    --onefile \
    --windowed \
    --add-data "oref_alert:oref_alert" \
    --distpath "dist" \
    --buildpath "build" \
    --specpath "build" \
    --clean \
    main.py

if [ $? -ne 0 ]; then
    echo "ERROR: PyInstaller build failed!"
    exit 1
fi

echo ""
echo "======================================"
echo "   Build Successful!"
echo "======================================"
echo ""
echo "Executable created at: dist/Red Alert"
echo ""
echo "Note: To create the Windows installer:"
echo "  1. Transfer this to a Windows machine"
echo "  2. Install NSIS"
echo "  3. Run the .nsi file with NSIS"
echo ""

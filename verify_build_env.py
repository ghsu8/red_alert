"""
Quick verification script to ensure the build environment is ready
"""
import sys
import subprocess

def check_python():
    """Check Python version"""
    version = sys.version_info
    print(f"✓ Python {version.major}.{version.minor}.{version.micro} found")
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("✗ Python 3.8+ is required")
        return False
    return True

def check_package(package_name, import_name=None):
    """Check if a package is installed"""
    import_name = import_name or package_name
    try:
        __import__(import_name)
        print(f"✓ {package_name} is installed")
        return True
    except ImportError:
        print(f"✗ {package_name} is NOT installed")
        return False

def main():
    print("\n" + "="*50)
    print("  Red Alert Build Environment Check")
    print("="*50 + "\n")
    
    all_ok = True
    
    # Check Python
    print("Checking Python...")
    if not check_python():
        all_ok = False
    
    print("\nChecking required packages...")
    required = [
        ("PySide6", "PySide6"),
        ("requests", "requests"),
        ("PyInstaller", "PyInstaller"),
    ]
    
    for package, import_name in required:
        if not check_package(package, import_name):
            all_ok = False
    
    print("\n" + "="*50)
    
    if all_ok:
        print("✓ All checks passed! Ready to build.")
        print("\nRun: build_installer.bat")
    else:
        print("✗ Some checks failed!")
        print("\nTo fix, run:")
        print("  pip install -r requirements.txt")
    
    print("="*50 + "\n")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())

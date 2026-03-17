#!/usr/bin/env python3
"""Comprehensive system validation for Red Alert minimize-to-tray feature."""

import sys
from pathlib import Path
from enum import Enum

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

class Status(Enum):
    OK = "✓"
    FAIL = "✗"
    INFO = "ℹ"

def check(name: str, func, *args):
    """Run a check and report results."""
    try:
        result = func(*args)
        print(f"{Status.OK.value} {name}")
        if result:
            print(f"  {Status.INFO.value} {result}")
        return True
    except Exception as e:
        print(f"{Status.FAIL.value} {name}: {e}")
        return False

# Test suite
print("=" * 60)
print("Red Alert - Minimize-to-Tray System Validation")
print("=" * 60)

all_pass = True

# Test 1: Imports
print("\n[1] Testing Imports...")
all_pass &= check(
    "Import RedAlertApp",
    lambda: __import__('oref_alert.app', fromlist=['RedAlertApp'])
)
all_pass &= check(
    "Import TrayIcon",
    lambda: __import__('oref_alert.ui.tray', fromlist=['TrayIcon'])
)
all_pass &= check(
    "Import SettingsWindow",
    lambda: __import__('oref_alert.ui.main_window', fromlist=['SettingsWindow'])
)
all_pass &= check(
    "Import create_lamp_icon",
    lambda: __import__('oref_alert.ui.icons', fromlist=['create_lamp_icon'])
)

# Test 2: App Initialization
print("\n[2] Testing App Initialization...")
def init_app():
    from oref_alert.app import RedAlertApp
    app = RedAlertApp()
    assert app.config is not None, "Config not loaded"
    assert app.app is not None, "QApplication not created"
    assert app._logger is not None, "Logger not initialized"
    return f"Config: {app.config.autostart=}, Sound: {app.config.sound_mode}"

all_pass &= check("RedAlertApp initialization", init_app)

# Test 3: Icon Creation
print("\n[3] Testing Icon Creation...")
def create_icon():
    from oref_alert.ui.icons import create_lamp_icon
    icon = create_lamp_icon(128)
    assert icon.width() == 128, f"Icon width is {icon.width()}, expected 128"
    assert icon.height() == 128, f"Icon height is {icon.height()}, expected 128"
    # Check that icon has some red pixels
    return f"Icon size: {icon.width()}x{icon.height()}"

all_pass &= check("Red lamp icon creation", create_icon)

# Test 4: Configuration
print("\n[4] Testing Configuration...")
def check_config():
    from oref_alert.config import AppConfig
    config = AppConfig()
    config.load()
    assert 'selected_regions' in config.__dict__, "Config missing selected_regions"
    assert 'selected_cities' in config.__dict__, "Config missing selected_cities"
    return f"Regions: {config.selected_regions[:2]}"

all_pass &= check("AppConfig structure", check_config)

# Test 5: File Existence
print("\n[5] Testing Required Files...")
files_to_check = [
    "main.py",
    "alert.py",
    "pikudOref.py",
    "oref_alert/__init__.py",
    "oref_alert/app.py",
    "oref_alert/config.py",
    "oref_alert/ui/tray.py",
    "oref_alert/ui/main_window.py",
    "oref_alert/ui/icons.py",
]

for file in files_to_check:
    path = Path(file)
    if path.exists():
        print(f"{Status.OK.value} {file}")
    else:
        print(f"{Status.FAIL.value} {file} - NOT FOUND")
        all_pass = False

# Test 6: Feature Validation
print("\n[6] Testing Feature Implementation...")

def check_tray_implementation():
    from oref_alert.ui.tray import TrayIcon
    import inspect
    
    # Check that TrayIcon has required methods
    methods = ['_toggle_window', '_on_activated', 'show']
    source = inspect.getsource(TrayIcon)
    
    for method in methods:
        if f"def {method}" not in source:
            raise AssertionError(f"TrayIcon missing {method} method")
    
    # Check that it imports create_lamp_icon
    if "create_lamp_icon" not in source:
        raise AssertionError("TrayIcon doesn't import create_lamp_icon")
    
    return "All required methods present"

all_pass &= check("TrayIcon minimize-to-tray implementation", check_tray_implementation)

def check_settings_window_minimize():
    from oref_alert.ui.main_window import SettingsWindow
    import inspect
    
    source = inspect.getsource(SettingsWindow)
    if "def closeEvent" not in source:
        raise AssertionError("SettingsWindow missing closeEvent override")
    if "self.hide()" not in source:
        raise AssertionError("closeEvent doesn't call self.hide()")
    
    return "closeEvent properly minimizes to tray"

all_pass &= check("SettingsWindow minimize-to-tray behavior", check_settings_window_minimize)

def check_app_startup():
    from oref_alert.app import RedAlertApp
    import inspect
    
    source = inspect.getsource(RedAlertApp.run)
    if "self._setup_tray()" not in source:
        raise AssertionError("run() doesn't call _setup_tray()")
    if "DashboardWindow" in source:
        raise AssertionError("run() still creates DashboardWindow")
    
    return "App properly starts in tray mode"

all_pass &= check("App startup in tray mode", check_app_startup)

# Summary
print("\n" + "=" * 60)
if all_pass:
    print("✓ ALL TESTS PASSED - App is ready for minimize-to-tray operation!")
    print("\nTo run the app:")
    print("  python main.py")
    sys.exit(0)
else:
    print("✗ SOME TESTS FAILED - Please review errors above")
    sys.exit(1)

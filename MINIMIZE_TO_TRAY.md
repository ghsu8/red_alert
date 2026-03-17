## Red Alert Minimize-to-Tray Implementation - Summary

### Overview
Implemented full minimize-to-tray functionality with a custom red lamp icon in the Windows system tray. The app now starts silently in the background and can be controlled entirely from the tray.

### Key Changes Made

#### 1. **app.py** - Application Startup and Window Management
- **Changed startup behavior**: App no longer shows a dashboard window on startup. Instead:
  - Creates SettingsWindow during `_setup_tray()` initialization
  - Shows a brief green notification confirming the app is running
  - Starts the fetcher and sits quietly in the tray
  - Users access everything via the red lamp icon in the system tray

- **Modified `_setup_tray()`**:
  - Now creates the SettingsWindow before creating TrayIcon
  - Passes the SettingsWindow as `main_window` parameter to TrayIcon
  - This allows tray to show/hide the window

- **Updated `_open_settings()`**:
  - Simply shows/raises the existing window instead of creating a new one
  - No more duplicate windows

#### 2. **ui/tray.py** - System Tray Icon with Window Toggle
- **Added imports**: 
  - `create_lamp_icon` from `oref_alert.ui.icons`
  - `QMainWindow` type hint

- **New parameters**:
  - `main_window: Optional[QMainWindow]` parameter to constructor
  - Stores reference to control window visibility

- **Red lamp icon**:
  - Uses `create_lamp_icon(128)` to generate red lamp icon if no file path provided
  - Icon displays clearly in Windows system tray

- **New methods**:
  - `_toggle_window()`: Shows/hides the SettingsWindow when tray icon is clicked
  - Updates activation behavior to toggle window instead of just opening settings

- **Menu changes**:
  - Added "הראה/הסתר" (Show/Hide) menu item at the top (if main_window provided)
  - Separator after show/hide option

#### 3. **ui/main_window.py** - Settings Window Minimize-to-Tray
- **Added `closeEvent()` override**:
  - When user clicks the X button to close, the window hides instead of closing
  - Calls `self.hide()` instead of accepting the close event
  - Window remains in memory and can be shown again via tray

#### 4. **ui/icons.py** - RED LAMP ICON CREATION (NEW FILE)
- **New utility module** for icon generation
- **`create_lamp_icon(size: int = 64) -> QPixmap`**:
  - Creates a red lamp/alert icon dynamically at runtime
  - Draws red circle (bulb) using QImage pixel manipulation
  - Draws dark rectangle (base) below the bulb
  - Returns a transparent QPixmap suitable for tray icon
  - No external image files needed

### User Experience Flow

#### First Time Running
1. User double-clicks `main.py` or starts app from command line
2. App initializes silently - only a brief green notification shows: "Red Alert רץ - האפליקציה רצה ברקע"
3. Red lamp icon appears in Windows system tray
4. App starts polling OREF API in background (every 5 seconds)

#### During Operation
1. **Open Settings/Logs**: Click lamp icon in tray → menu appears with:
   - "הראה/הסתר" (Show/Hide) - toggle settings window
   - "הגדרות" (Settings) - open settings directly
   - "יומן התראות" (Log) - view alert history
   - "יציאה" (Exit) - close app

2. **Quick Toggle**: Left-click lamp icon → Settings window shows/hides

3. **When Alert Arrives**: Red popup with siren sound (if configured)

4. **Minimize**: Click X button in SettingsWindow → hides to tray, doesn't exit

### Testing
Run `python test_app.py` to verify:
- ✓ All imports work
- ✓ RedAlertApp initializes
- ✓ Red lamp icon creates successfully
- ✓ Config loads properly

### Files Modified
1. `oref_alert/app.py` - Startup and window management
2. `oref_alert/ui/tray.py` - Tray icon with toggle functionality
3. `oref_alert/ui/main_window.py` - Minimize-to-tray behavior on close
4. `oref_alert/ui/icons.py` - Red lamp icon generator (NEW)

### How to Run
```bash
# Install dependencies
pip install PySide6 requests

# Run the app
python main.py
```

### Future Enhancements (Optional)
- Change lamp color based on alert status (brighter red when alert active)
- Add notification badge showing alert count
- Auto-show window on new alert instead of staying hidden
- Save/restore window position and size

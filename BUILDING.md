# Building the Red Alert Installer

This guide explains how to create a standalone Windows installer for the Red Alert application.

## Prerequisites

You need the following software installed:

1. **Python 3.8+** - Download from [python.org](https://www.python.org)
2. **NSIS (Nullsoft Scriptable Install System)** - Download from [nsis.sourceforge.io](https://nsis.sourceforge.io)

## Installation Steps

### Step 1: Install Python Dependencies and PyInstaller

```bash
# From the project directory (c:\redalert)
pip install -r requirements.txt
pip install pyinstaller
```

### Step 2: Build the Executable

Run the build script:

```bash
cd c:\redalert
build_installer.bat
```

This will:
- Install all dependencies
- Run PyInstaller to create a standalone `Red Alert.exe` in the `dist` folder
- Build folder will contain temporary files (can be deleted after)

The executable will be located at: `c:\redalert\dist\Red Alert.exe`

### Step 3: Create the Installer

1. **Install NSIS** if you haven't already (download from the link above)
2. **Open NSIS**:
   - Launch the NSIS application
   - Click "Compile NSI Scripts"
   - Select `RedAlert_Installer.nsi` from the project folder
   - Click "Compile"

The installer will be created as: `c:\redalert\dist\RedAlert_Setup_1.0.0.exe`

## What the Installer Does

- **Installs to**: `C:\Program Files\Red Alert` (user can choose different location)
- **Creates Start Menu shortcuts**: Quick access to the application
- **Optional Desktop shortcut**: User is asked during installation
- **Adds to Add/Remove Programs**: Users can uninstall via Control Panel
- **Creates Uninstaller**: Users can remove the application cleanly

## Running the Installer

1. Run `RedAlert_Setup_1.0.0.exe`
2. Click through the installation wizard
3. Choose installation location (default: `C:\Program Files\Red Alert`)
4. Choose whether to create a Desktop shortcut
5. Click Install
6. Application is ready to use - launch from Start Menu or Desktop shortcut

## User Experience

Once installed, users:
- **Don't need to install anything else** - all dependencies are bundled in the executable
- **Just click the shortcut** to launch the application
- Can **uninstall via Control Panel** → Programs → Red Alert

## Troubleshooting

### "PyInstaller failed!" error
- Ensure Python is in PATH: `python --version`
- Reinstall PyInstaller: `pip install -U pyinstaller`

### NSIS compilation fails
- Ensure NSIS is properly installed
- Check that the file path to `dist\Red Alert.exe` is correct
- Try running NSIS in Administrator mode

### Standalone exe fails to run
- Check that all Python modules are correctly packaged
- Run: `python -m PyInstaller -F --windowed main.py` manually to debug

## Creating Updates

To create a new installer version:
1. Update `PRODUCT_VERSION` in `RedAlert_Installer.nsi`
2. Run `build_installer.bat` again
3. Compile the NSIS script

The new installer will replace the old one in the `dist` folder.

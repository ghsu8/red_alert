!include "MUI2.nsh"
!include "x64.nsh"

; Define constants
!define PRODUCT_NAME "Red Alert"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "Red Alert"
!define PRODUCT_WEB_SITE "https://github.com"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\RedAlert.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"

; MUI Settings
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_INSTFILES

; Language
!insertmacro MUI_LANGUAGE "English"

; Installer attributes
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "dist\RedAlert_Setup_${PRODUCT_VERSION}.exe"
InstallDir "$PROGRAMFILES\${PRODUCT_NAME}"
ShowInstDetails show
ShowUnInstDetails show

; Request admin privileges
RequestExecutionLevel admin

; Variables
Var StartMenuFolder
Var CreateDesktopShortcut

; Installer sections
Section "Install"
  SetOutPath "$INSTDIR"
  
  ; Copy the executable
  File "dist\Red Alert.exe"
  
  ; Create shortcuts in Start Menu
  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\Red Alert.exe"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  
  ; Create Desktop shortcut if requested
  ${If} $CreateDesktopShortcut == 1
    CreateShortCut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\Red Alert.exe"
  ${EndIf}
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  
  ; Write registry entries
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\Red Alert.exe"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  
  SetOutPath "$INSTDIR"
  MessageBox MB_OK "Installation completed successfully!$\n$\nYou can launch ${PRODUCT_NAME} from the Start Menu or Desktop shortcut."
SectionEnd

; Uninstaller section
Section "Uninstall"
  ; Remove shortcuts
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall.lnk"
  RMDir "$SMPROGRAMS\${PRODUCT_NAME}"
  Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
  
  ; Remove executable
  Delete "$INSTDIR\Red Alert.exe"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  
  ; Remove registry entries
  DeleteRegKey HKLM "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
SectionEnd

; Installer init
Function .onInit
  ; Check for Windows x64 and set appropriate installer
  ${If} ${RunningX64}
    ; 64-bit Windows
  ${Else}
    MessageBox MB_OK "This application requires Windows (32-bit or 64-bit) with Python runtime support."
  ${EndIf}
  
  ; Show dialog for desktop shortcut
  MessageBox MB_YESNO "Would you like to create a shortcut on the Desktop?" IDYES create_desktop
  StrCpy $CreateDesktopShortcut 0
  Goto end_create
  create_desktop:
  StrCpy $CreateDesktopShortcut 1
  end_create:
FunctionEnd

; Uninstaller init
Function un.onInit
  MessageBox MB_ICONQUESTION "Are you sure you want to uninstall ${PRODUCT_NAME}?" IDYES +2
  Abort "Uninstall cancelled."
FunctionEnd

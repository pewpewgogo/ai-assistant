@echo off
title AI Assistant Installer
echo ============================================
echo   AI Assistant - Windows Installer
echo ============================================
echo.

set "INSTALL_DIR=%LOCALAPPDATA%\AI Assistant"
set "EXE_NAME=AI Assistant.exe"
set "REPO=pewpewgogo/ai-assistant"

echo Installing to: %INSTALL_DIR%
echo.

:: Create install directory
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Download latest release
echo Downloading latest version...
powershell -Command "& { $releases = Invoke-RestMethod -Uri 'https://api.github.com/repos/%REPO%/releases/latest'; $asset = $releases.assets | Where-Object { $_.name -like '*.exe' } | Select-Object -First 1; if ($asset) { Invoke-WebRequest -Uri $asset.browser_download_url -OutFile '%INSTALL_DIR%\%EXE_NAME%' -UseBasicParsing; Write-Host 'Download complete.' } else { Write-Host 'ERROR: No .exe found in latest release.'; exit 1 } }"

if %errorlevel% neq 0 (
    echo.
    echo Download failed. Please check your internet connection.
    pause
    exit /b 1
)

:: Create desktop shortcut
echo Creating desktop shortcut...
powershell -Command "& { $ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%USERPROFILE%\Desktop\AI Assistant.lnk'); $sc.TargetPath = '%INSTALL_DIR%\%EXE_NAME%'; $sc.WorkingDirectory = '%INSTALL_DIR%'; $sc.Description = 'AI Assistant - Voice-controlled desktop helper'; $sc.Save() }"

:: Create Start Menu shortcut
set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
powershell -Command "& { $ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%START_MENU%\AI Assistant.lnk'); $sc.TargetPath = '%INSTALL_DIR%\%EXE_NAME%'; $sc.WorkingDirectory = '%INSTALL_DIR%'; $sc.Description = 'AI Assistant - Voice-controlled desktop helper'; $sc.Save() }"

echo.
echo ============================================
echo   Installation complete!
echo ============================================
echo.
echo A shortcut has been placed on your Desktop.
echo.
echo FIRST TIME SETUP:
echo   1. Double-click "AI Assistant" on your Desktop
echo   2. Right-click the blue "A" icon in your system tray
echo   3. Click "Settings"
echo   4. Paste your OpenAI API key and click Save
echo   5. Click "Hold to Talk" and speak!
echo.
pause

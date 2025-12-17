@echo off
echo ========================================
echo Redmine File Organizer Installer Build
echo ========================================
echo.

REM Change to script directory
cd /d "%~dp0"
echo Working directory: %CD%
echo.

REM Inno Setup path check
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
) else if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
)

if "%ISCC%"=="" (
    echo [ERROR] Inno Setup 6 not found.
    echo.
    echo Please install Inno Setup 6:
    echo https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

echo [1/2] Building EXE...
pip install pyinstaller pystray pillow watchdog requests -q
pyinstaller --onefile --windowed --name RedmineFileOrganizer --hidden-import pystray._win32 --hidden-import PIL._tkinter_finder redmine_file_organizer.py
if errorlevel 1 (
    echo [ERROR] EXE build failed.
    pause
    exit /b 1
)

echo.
echo [2/2] Building Installer...
"%ISCC%" installer.iss
if errorlevel 1 (
    echo [ERROR] Installer build failed.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build Complete!
echo Installer: installer_output\RedmineFileOrganizer_Setup_1.0.0.exe
echo ========================================
pause

@echo off
chcp 65001 >nul
echo ========================================
echo Redmine File Organizer Installer Build
echo ========================================
echo.

:: Inno Setup のパスを検索
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
) else if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
)

if "%ISCC%"=="" (
    echo [ERROR] Inno Setup 6 が見つかりません。
    echo.
    echo Inno Setup 6 をインストールしてください:
    echo https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

echo [1/2] EXE をビルド中...
call build.bat
if errorlevel 1 (
    echo [ERROR] EXE ビルドに失敗しました。
    pause
    exit /b 1
)

echo.
echo [2/2] インストーラーをビルド中...
"%ISCC%" installer.iss
if errorlevel 1 (
    echo [ERROR] インストーラービルドに失敗しました。
    pause
    exit /b 1
)

echo.
echo ========================================
echo ビルド完了！
echo インストーラー: installer_output\RedmineFileOrganizer_Setup_1.0.0.exe
echo ========================================
pause

@echo off
chcp 65001 > nul
echo ======================================
echo Redmine ファイル整理ツール EXE ビルド
echo ======================================
echo.

echo 依存パッケージをインストール中...
pip install pyinstaller pystray pillow watchdog requests -q

echo.
echo EXE ファイルをビルド中...
pyinstaller --onefile --windowed --name RedmineFileOrganizer ^
    --hidden-import pystray._win32 ^
    --hidden-import PIL._tkinter_finder ^
    redmine_file_organizer.py

echo.
if exist dist\RedmineFileOrganizer.exe (
    echo ======================================
    echo ビルド成功!
    echo EXE: dist\RedmineFileOrganizer.exe
    echo ======================================
) else (
    echo ビルド失敗
)

pause

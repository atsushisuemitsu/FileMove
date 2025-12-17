# -*- coding: utf-8 -*-
"""
Redmine ファイル整理ツール EXE ビルドスクリプト
"""

import subprocess
import sys
import os

def main():
    # 必要なパッケージをインストール
    print("必要なパッケージをインストール中...")
    packages = ['pyinstaller', 'pystray', 'pillow', 'watchdog', 'requests']
    for pkg in packages:
        subprocess.run([sys.executable, '-m', 'pip', 'install', pkg, '-q'])

    # PyInstallerでビルド
    print("\nEXEファイルをビルド中...")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, 'redmine_file_organizer.py')

    # PyInstallerコマンド
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',           # 単一EXEファイル
        '--windowed',          # コンソールウィンドウなし
        '--name', 'RedmineFileOrganizer',
        '--hidden-import', 'pystray._win32',
        '--hidden-import', 'PIL._tkinter_finder',
        main_script
    ]

    result = subprocess.run(cmd, cwd=script_dir)

    if result.returncode == 0:
        print("\n" + "="*50)
        print("ビルド成功!")
        print(f"EXEファイル: {script_dir}\dist\RedmineFileOrganizer.exe")
        print("="*50)
    else:
        print("\nビルド失敗")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())

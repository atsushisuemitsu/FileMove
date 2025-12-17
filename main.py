"""
FileMove - Windows 11 File Monitoring and Organization App

A system tray application that:
1. Monitors a folder for new files and helps organize them
2. Generates Python scripts using OpenRouter API

Usage:
    python main.py

Requirements:
    pip install -r requirements.txt
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app import main

if __name__ == "__main__":
    main()

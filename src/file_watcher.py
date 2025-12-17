"""File Watcher - Monitor folder for new files using watchdog"""

import os
import time
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent


class FileCreationHandler(FileSystemEventHandler):
    """Handler for file creation events"""

    def __init__(self, callback: Callable[[str], None], debounce_seconds: float = 1.0):
        super().__init__()
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._pending_files: dict[str, float] = {}

    def _is_file_ready(self, filepath: str) -> bool:
        """Check if file is completely written (not being copied)"""
        try:
            initial_size = os.path.getsize(filepath)
            time.sleep(0.5)
            final_size = os.path.getsize(filepath)
            return initial_size == final_size and final_size > 0
        except (OSError, FileNotFoundError):
            return False

    def _process_file(self, filepath: str):
        """Process a newly created file"""
        if not os.path.isfile(filepath):
            return

        # Wait for file to be fully written
        max_attempts = 10
        for _ in range(max_attempts):
            if self._is_file_ready(filepath):
                self.callback(filepath)
                return
            time.sleep(0.5)

    def on_created(self, event: FileCreatedEvent):
        """Handle file creation event"""
        if event.is_directory:
            return
        self._process_file(event.src_path)

    def on_moved(self, event: FileMovedEvent):
        """Handle file moved event (e.g., download completion)"""
        if event.is_directory:
            return
        # For moved files, check destination
        self._process_file(event.dest_path)


class FileWatcher:
    """Watch a folder for new files"""

    def __init__(self, watch_folder: str, callback: Callable[[str], None]):
        self.watch_folder = Path(watch_folder)
        self.callback = callback
        self.observer: Optional[Observer] = None
        self.handler: Optional[FileCreationHandler] = None
        self._running = False

    def start(self):
        """Start watching the folder"""
        if self._running:
            return

        if not self.watch_folder.exists():
            self.watch_folder.mkdir(parents=True, exist_ok=True)

        self.handler = FileCreationHandler(self.callback)
        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.watch_folder), recursive=False)
        self.observer.start()
        self._running = True

    def stop(self):
        """Stop watching the folder"""
        if not self._running:
            return

        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.observer = None

        self._running = False

    def is_running(self) -> bool:
        """Check if watcher is running"""
        return self._running

    def set_watch_folder(self, folder: str):
        """Change the watch folder"""
        was_running = self._running
        if was_running:
            self.stop()

        self.watch_folder = Path(folder)

        if was_running:
            self.start()

"""Main Application - Integrates all components"""

import os
import sys
import threading
from pathlib import Path
from typing import Optional
import customtkinter as ctk

from .settings_window import Config, SettingsWindow
from .file_watcher import FileWatcher
from .folder_selector import FolderSelector, FolderSelectorDialog
from .tray_icon import TrayIcon
from .api_client import OpenRouterClient
from .prompt_manager import PromptStorage, PromptManagerWindow
from .script_executor import ScriptExecutor, ScriptExecutorWindow


class FileMoveApp:
    """Main application class"""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)

        # Initialize CustomTkinter
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        # Create hidden root window
        self.root = ctk.CTk()
        self.root.withdraw()
        self.root.title("FileMove")

        # Initialize paths
        self.config_path = self.base_dir / "config.json"
        self.prompts_dir = self.base_dir / "prompts"
        self.scripts_dir = self.base_dir / "generated_scripts"

        # Ensure directories exist
        self.prompts_dir.mkdir(exist_ok=True)
        self.scripts_dir.mkdir(exist_ok=True)

        # Load configuration
        self.config = Config(str(self.config_path))

        # Initialize components
        self._init_components()

        # File queue for processing
        self._file_queue: list[str] = []
        self._processing = False

    def _init_components(self):
        """Initialize all components"""
        # API Client
        self.api_client = OpenRouterClient(
            self.config.api_url,
            self.config.api_key,
            self.config.api_model
        )

        # Prompt Storage
        self.prompt_storage = PromptStorage(str(self.prompts_dir))

        # Script Executor
        self.script_executor = ScriptExecutor(
            str(self.scripts_dir),
            self.api_client
        )

        # Folder Selector
        self.folder_selector = FolderSelector(self.config.destination_folder)

        # File Watcher
        self.file_watcher = FileWatcher(
            self.config.watch_folder,
            self._on_file_created
        )

        # Tray Icon
        self.tray_icon = TrayIcon(
            on_settings=self._show_settings,
            on_prompts=self._show_prompts,
            on_scripts=self._show_scripts,
            on_quit=self._quit,
            on_toggle_watch=self._toggle_watch
        )

    def _on_file_created(self, filepath: str):
        """Handle new file creation"""
        # Add to queue and process
        self._file_queue.append(filepath)
        if not self._processing:
            self._process_queue()

    def _process_queue(self):
        """Process file queue"""
        if not self._file_queue:
            self._processing = False
            return

        self._processing = True
        filepath = self._file_queue.pop(0)

        # Check if destination is configured
        if not self.config.destination_folder:
            self.tray_icon.notify(
                "FileMove",
                f"新しいファイル: {os.path.basename(filepath)}\n移動先フォルダが設定されていません"
            )
            self._process_queue()
            return

        # Show folder selector dialog
        def show_dialog():
            dialog = self.folder_selector.show_dialog(
                self.root,
                filepath,
                on_complete=self._on_move_complete
            )
            if dialog:
                dialog.wait_window()

        self.root.after(0, show_dialog)

    def _on_move_complete(self, source: str, destination: Optional[str]):
        """Handle file move completion"""
        if destination:
            self.tray_icon.notify(
                "FileMove",
                f"ファイルを移動しました:\n{os.path.basename(destination)}"
            )
        # Process next file
        self.root.after(100, self._process_queue)

    def _show_settings(self):
        """Show settings window"""
        def show():
            SettingsWindow(self.root, self.config, on_save=self._on_settings_saved)

        self.root.after(0, show)

    def _on_settings_saved(self):
        """Handle settings saved"""
        # Update components with new config
        self.api_client.update_config(
            self.config.api_url,
            self.config.api_key,
            self.config.api_model
        )

        self.folder_selector.set_destination_root(self.config.destination_folder)

        # Restart watcher if folder changed
        if self.file_watcher.is_running():
            self.file_watcher.stop()
            self.file_watcher.set_watch_folder(self.config.watch_folder)
            if self.config.watch_folder:
                self.file_watcher.start()
                self.tray_icon.set_watching(True)

    def _show_prompts(self):
        """Show prompt manager window"""
        def show():
            PromptManagerWindow(self.root, self.prompt_storage)

        self.root.after(0, show)

    def _show_scripts(self):
        """Show script executor window"""
        def show():
            ScriptExecutorWindow(self.root, self.script_executor, self.prompt_storage)

        self.root.after(0, show)

    def _toggle_watch(self):
        """Toggle file watching"""
        if self.file_watcher.is_running():
            self.file_watcher.stop()
            self.tray_icon.set_watching(False)
            self.tray_icon.update_tooltip("FileMove - 停止中")
        else:
            if not self.config.watch_folder:
                self._show_settings()
                return

            self.file_watcher.set_watch_folder(self.config.watch_folder)
            self.file_watcher.start()
            self.tray_icon.set_watching(True)
            self.tray_icon.update_tooltip(f"FileMove - 監視中: {self.config.watch_folder}")

    def _quit(self):
        """Quit the application"""
        self.file_watcher.stop()
        self.api_client.close()
        self.tray_icon.stop()
        self.root.quit()

    def run(self):
        """Run the application"""
        # Start tray icon
        self.tray_icon.start()

        # Start watching if configured
        if self.config.watch_folder:
            self.file_watcher.start()
            self.tray_icon.set_watching(True)
            self.tray_icon.update_tooltip(f"FileMove - 監視中: {self.config.watch_folder}")
        else:
            self.tray_icon.update_tooltip("FileMove - 設定が必要です")

        # Run main loop
        self.root.mainloop()


def main():
    """Entry point"""
    # Get base directory
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    app = FileMoveApp(base_dir)
    app.run()


if __name__ == "__main__":
    main()

"""Folder Selector UI - CustomTkinter dialog for selecting destination folder"""

import os
import shutil
from pathlib import Path
from typing import Optional, Callable
import customtkinter as ctk


class FolderSelectorDialog(ctk.CTkToplevel):
    """Dialog for selecting destination folder for a file"""

    def __init__(
        self,
        parent,
        filepath: str,
        destination_root: str,
        on_complete: Optional[Callable[[str, Optional[str]], None]] = None
    ):
        super().__init__(parent)

        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.destination_root = Path(destination_root)
        self.current_folder = self.destination_root
        self.on_complete = on_complete
        self.result: Optional[str] = None

        self._setup_window()
        self._create_widgets()
        self._update_folder_list()

        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        self.focus_force()

        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _setup_window(self):
        """Configure window properties"""
        self.title("ファイル移動先を選択")
        self.geometry("500x450")
        self.minsize(400, 350)
        self.resizable(True, True)

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_skip)

    def _create_widgets(self):
        """Create UI widgets"""
        # File info frame
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            file_frame,
            text="新しいファイル:",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=10, pady=(5, 0))

        ctk.CTkLabel(
            file_frame,
            text=self.filename,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=450
        ).pack(anchor="w", padx=10, pady=(0, 5))

        # Current path label
        self.path_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.path_label.pack(fill="x", padx=10, pady=5)

        # Navigation buttons
        nav_frame = ctk.CTkFrame(self)
        nav_frame.pack(fill="x", padx=10, pady=5)

        self.back_btn = ctk.CTkButton(
            nav_frame,
            text="← 戻る",
            width=80,
            command=self._go_back
        )
        self.back_btn.pack(side="left", padx=5)

        self.new_folder_btn = ctk.CTkButton(
            nav_frame,
            text="+ 新規フォルダ",
            width=120,
            command=self._create_new_folder
        )
        self.new_folder_btn.pack(side="right", padx=5)

        # Folder list
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.folder_listbox = ctk.CTkScrollableFrame(list_frame)
        self.folder_listbox.pack(fill="both", expand=True, padx=5, pady=5)

        # Action buttons
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            action_frame,
            text="スキップ",
            width=100,
            fg_color="gray",
            command=self._on_skip
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            action_frame,
            text="ここに移動",
            width=120,
            fg_color="green",
            command=self._on_move_here
        ).pack(side="right", padx=5)

    def _update_folder_list(self):
        """Update the folder list display"""
        # Update path label
        try:
            rel_path = self.current_folder.relative_to(self.destination_root)
            path_text = f"現在: /{rel_path}" if str(rel_path) != "." else "現在: /"
        except ValueError:
            path_text = f"現在: {self.current_folder}"
        self.path_label.configure(text=path_text)

        # Update back button state
        self.back_btn.configure(
            state="normal" if self.current_folder != self.destination_root else "disabled"
        )

        # Clear existing items
        for widget in self.folder_listbox.winfo_children():
            widget.destroy()

        # List subfolders
        try:
            subfolders = sorted([
                f for f in self.current_folder.iterdir()
                if f.is_dir() and not f.name.startswith('.')
            ], key=lambda x: x.name.lower())

            if not subfolders:
                ctk.CTkLabel(
                    self.folder_listbox,
                    text="(サブフォルダなし)",
                    text_color="gray"
                ).pack(pady=20)
            else:
                for folder in subfolders:
                    self._create_folder_button(folder)

        except PermissionError:
            ctk.CTkLabel(
                self.folder_listbox,
                text="(アクセス権限がありません)",
                text_color="red"
            ).pack(pady=20)

    def _create_folder_button(self, folder: Path):
        """Create a button for a folder"""
        btn = ctk.CTkButton(
            self.folder_listbox,
            text=f"📁 {folder.name}",
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            command=lambda f=folder: self._enter_folder(f)
        )
        btn.pack(fill="x", pady=2)

    def _enter_folder(self, folder: Path):
        """Enter a subfolder"""
        self.current_folder = folder
        self._update_folder_list()

    def _go_back(self):
        """Go to parent folder"""
        if self.current_folder != self.destination_root:
            self.current_folder = self.current_folder.parent
            self._update_folder_list()

    def _create_new_folder(self):
        """Show dialog to create new folder"""
        dialog = ctk.CTkInputDialog(
            text="新しいフォルダ名を入力:",
            title="新規フォルダ作成"
        )
        folder_name = dialog.get_input()

        if folder_name:
            # Sanitize folder name
            folder_name = "".join(
                c for c in folder_name
                if c not in '<>:"/\\|?*'
            ).strip()

            if folder_name:
                new_folder = self.current_folder / folder_name
                try:
                    new_folder.mkdir(exist_ok=True)
                    self._update_folder_list()
                except OSError as e:
                    self._show_error(f"フォルダ作成失敗: {e}")

    def _on_move_here(self):
        """Move file to current folder"""
        dest_path = self.current_folder / self.filename

        # Check if file already exists
        if dest_path.exists():
            # Add number suffix
            base, ext = os.path.splitext(self.filename)
            counter = 1
            while dest_path.exists():
                dest_path = self.current_folder / f"{base}_{counter}{ext}"
                counter += 1

        try:
            shutil.move(self.filepath, dest_path)
            self.result = str(dest_path)
        except OSError as e:
            self._show_error(f"移動失敗: {e}")
            return

        if self.on_complete:
            self.on_complete(self.filepath, self.result)

        self.destroy()

    def _on_skip(self):
        """Skip this file"""
        self.result = None
        if self.on_complete:
            self.on_complete(self.filepath, None)
        self.destroy()

    def _show_error(self, message: str):
        """Show error message"""
        error_dialog = ctk.CTkToplevel(self)
        error_dialog.title("エラー")
        error_dialog.geometry("300x100")
        error_dialog.transient(self)
        error_dialog.grab_set()

        ctk.CTkLabel(error_dialog, text=message, wraplength=280).pack(pady=20)
        ctk.CTkButton(
            error_dialog,
            text="OK",
            command=error_dialog.destroy
        ).pack(pady=10)


class FolderSelector:
    """Manager for folder selection dialogs"""

    def __init__(self, destination_root: str):
        self.destination_root = destination_root
        self._pending_files: list[str] = []
        self._dialog_open = False

    def set_destination_root(self, path: str):
        """Set the destination root folder"""
        self.destination_root = path

    def show_dialog(
        self,
        parent,
        filepath: str,
        on_complete: Optional[Callable[[str, Optional[str]], None]] = None
    ):
        """Show folder selection dialog for a file"""
        if not self.destination_root:
            return

        dialog = FolderSelectorDialog(
            parent,
            filepath,
            self.destination_root,
            on_complete
        )
        return dialog

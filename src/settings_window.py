"""Settings Window - Configuration UI"""

import json
from pathlib import Path
from typing import Optional, Callable
import customtkinter as ctk
from tkinter import filedialog


class Config:
    """Application configuration"""

    DEFAULT_CONFIG = {
        "api": {
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "key": "",
            "model": "openai/gpt-4o"
        },
        "folders": {
            "watch": "",
            "destination": ""
        },
        "startup": False
    }

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self._config = self.DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        """Load configuration from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Merge with defaults
                    self._deep_merge(self._config, loaded)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        """Save configuration to file"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    def _deep_merge(self, base: dict, update: dict):
        """Deep merge update into base"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    # API settings
    @property
    def api_url(self) -> str:
        return self._config["api"]["url"]

    @api_url.setter
    def api_url(self, value: str):
        self._config["api"]["url"] = value

    @property
    def api_key(self) -> str:
        return self._config["api"]["key"]

    @api_key.setter
    def api_key(self, value: str):
        self._config["api"]["key"] = value

    @property
    def api_model(self) -> str:
        return self._config["api"]["model"]

    @api_model.setter
    def api_model(self, value: str):
        self._config["api"]["model"] = value

    # Folder settings
    @property
    def watch_folder(self) -> str:
        return self._config["folders"]["watch"]

    @watch_folder.setter
    def watch_folder(self, value: str):
        self._config["folders"]["watch"] = value

    @property
    def destination_folder(self) -> str:
        return self._config["folders"]["destination"]

    @destination_folder.setter
    def destination_folder(self, value: str):
        self._config["folders"]["destination"] = value

    @property
    def startup(self) -> bool:
        return self._config["startup"]

    @startup.setter
    def startup(self, value: bool):
        self._config["startup"] = value


class SettingsWindow(ctk.CTkToplevel):
    """Settings configuration window"""

    def __init__(self, parent, config: Config, on_save: Optional[Callable] = None):
        super().__init__(parent)

        self.config = config
        self.on_save = on_save

        self._setup_window()
        self._create_widgets()
        self._load_values()

        self.transient(parent)
        self.grab_set()
        self.focus_force()

    def _setup_window(self):
        """Configure window"""
        self.title("設定")
        self.geometry("600x500")
        self.minsize(500, 400)

    def _create_widgets(self):
        """Create UI widgets"""
        # Create tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # API tab
        self.tabview.add("API設定")
        self._create_api_tab()

        # Folder tab
        self.tabview.add("フォルダ設定")
        self._create_folder_tab()

        # General tab
        self.tabview.add("一般")
        self._create_general_tab()

        # Buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            btn_frame,
            text="キャンセル",
            fg_color="gray",
            command=self.destroy
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="保存",
            fg_color="green",
            command=self._save
        ).pack(side="right", padx=5)

    def _create_api_tab(self):
        """Create API settings tab"""
        tab = self.tabview.tab("API設定")

        # API URL
        ctk.CTkLabel(tab, text="API URL:").pack(anchor="w", padx=10, pady=(10, 0))
        self.api_url_entry = ctk.CTkEntry(tab, width=500)
        self.api_url_entry.pack(padx=10, pady=5)

        # API Key
        ctk.CTkLabel(tab, text="API Key:").pack(anchor="w", padx=10, pady=(10, 0))
        self.api_key_entry = ctk.CTkEntry(tab, width=500, show="*")
        self.api_key_entry.pack(padx=10, pady=5)

        # Show/Hide key
        self.show_key_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            tab,
            text="APIキーを表示",
            variable=self.show_key_var,
            command=self._toggle_key_visibility
        ).pack(anchor="w", padx=10)

        # Model
        ctk.CTkLabel(tab, text="モデル:").pack(anchor="w", padx=10, pady=(10, 0))
        self.model_entry = ctk.CTkEntry(tab, width=500)
        self.model_entry.pack(padx=10, pady=5)

        # Model suggestions
        ctk.CTkLabel(
            tab,
            text="例: openai/gpt-4o, anthropic/claude-3-opus, google/gemini-pro",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=10)

    def _create_folder_tab(self):
        """Create folder settings tab"""
        tab = self.tabview.tab("フォルダ設定")

        # Watch folder
        ctk.CTkLabel(tab, text="監視フォルダ:").pack(anchor="w", padx=10, pady=(10, 0))
        watch_frame = ctk.CTkFrame(tab)
        watch_frame.pack(fill="x", padx=10, pady=5)

        self.watch_entry = ctk.CTkEntry(watch_frame, width=400)
        self.watch_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkButton(
            watch_frame,
            text="参照",
            width=80,
            command=lambda: self._browse_folder(self.watch_entry)
        ).pack(side="right")

        ctk.CTkLabel(
            tab,
            text="新しいファイルが作成されると通知されるフォルダ",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=10)

        # Destination folder
        ctk.CTkLabel(tab, text="移動先フォルダ:").pack(anchor="w", padx=10, pady=(20, 0))
        dest_frame = ctk.CTkFrame(tab)
        dest_frame.pack(fill="x", padx=10, pady=5)

        self.dest_entry = ctk.CTkEntry(dest_frame, width=400)
        self.dest_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkButton(
            dest_frame,
            text="参照",
            width=80,
            command=lambda: self._browse_folder(self.dest_entry)
        ).pack(side="right")

        ctk.CTkLabel(
            tab,
            text="ファイルの移動先として選択できるルートフォルダ",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=10)

    def _create_general_tab(self):
        """Create general settings tab"""
        tab = self.tabview.tab("一般")

        # Startup
        self.startup_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            tab,
            text="Windows起動時に自動起動",
            variable=self.startup_var
        ).pack(anchor="w", padx=10, pady=20)

        ctk.CTkLabel(
            tab,
            text="※この機能は現在未実装です",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=30)

    def _toggle_key_visibility(self):
        """Toggle API key visibility"""
        show = "" if self.show_key_var.get() else "*"
        self.api_key_entry.configure(show=show)

    def _browse_folder(self, entry: ctk.CTkEntry):
        """Open folder browser dialog"""
        folder = filedialog.askdirectory()
        if folder:
            entry.delete(0, "end")
            entry.insert(0, folder)

    def _load_values(self):
        """Load current config values into fields"""
        self.api_url_entry.insert(0, self.config.api_url)
        self.api_key_entry.insert(0, self.config.api_key)
        self.model_entry.insert(0, self.config.api_model)
        self.watch_entry.insert(0, self.config.watch_folder)
        self.dest_entry.insert(0, self.config.destination_folder)
        self.startup_var.set(self.config.startup)

    def _save(self):
        """Save settings"""
        self.config.api_url = self.api_url_entry.get().strip()
        self.config.api_key = self.api_key_entry.get().strip()
        self.config.api_model = self.model_entry.get().strip()
        self.config.watch_folder = self.watch_entry.get().strip()
        self.config.destination_folder = self.dest_entry.get().strip()
        self.config.startup = self.startup_var.get()

        self.config.save()

        if self.on_save:
            self.on_save()

        self.destroy()

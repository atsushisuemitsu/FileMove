"""Prompt Manager - Create, edit, and manage prompts"""

import json
import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional
import customtkinter as ctk


class Prompt:
    """Represents a saved prompt"""

    def __init__(self, name: str, content: str, prompt_id: Optional[str] = None):
        self.name = name
        self.content = content
        self.id = prompt_id or self._generate_id()
        self.created_at = datetime.now().isoformat()
        self.last_used: Optional[str] = None

    def _generate_id(self) -> str:
        """Generate unique ID from content hash"""
        content_hash = hashlib.md5(
            f"{self.name}{self.content}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        return content_hash

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "content": self.content,
            "created_at": self.created_at,
            "last_used": self.last_used
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Prompt":
        """Create from dictionary"""
        prompt = cls(
            name=data["name"],
            content=data["content"],
            prompt_id=data.get("id")
        )
        prompt.created_at = data.get("created_at", datetime.now().isoformat())
        prompt.last_used = data.get("last_used")
        return prompt


class PromptStorage:
    """Storage manager for prompts"""

    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._prompts: dict[str, Prompt] = {}
        self._load_all()

    def _load_all(self):
        """Load all prompts from storage"""
        for file in self.storage_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    prompt = Prompt.from_dict(data)
                    self._prompts[prompt.id] = prompt
            except (json.JSONDecodeError, KeyError):
                continue

    def save(self, prompt: Prompt):
        """Save a prompt"""
        self._prompts[prompt.id] = prompt
        filepath = self.storage_dir / f"{prompt.id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(prompt.to_dict(), f, ensure_ascii=False, indent=2)

    def delete(self, prompt_id: str) -> bool:
        """Delete a prompt"""
        if prompt_id not in self._prompts:
            return False

        filepath = self.storage_dir / f"{prompt_id}.json"
        if filepath.exists():
            filepath.unlink()

        del self._prompts[prompt_id]
        return True

    def get(self, prompt_id: str) -> Optional[Prompt]:
        """Get a prompt by ID"""
        return self._prompts.get(prompt_id)

    def get_all(self) -> list[Prompt]:
        """Get all prompts"""
        return list(self._prompts.values())

    def mark_used(self, prompt_id: str):
        """Mark prompt as recently used"""
        if prompt_id in self._prompts:
            self._prompts[prompt_id].last_used = datetime.now().isoformat()
            self.save(self._prompts[prompt_id])


class PromptEditorDialog(ctk.CTkToplevel):
    """Dialog for creating/editing a prompt"""

    def __init__(self, parent, prompt: Optional[Prompt] = None, on_save=None):
        super().__init__(parent)

        self.prompt = prompt
        self.on_save = on_save
        self.result: Optional[Prompt] = None

        self._setup_window()
        self._create_widgets()

        # Pre-fill if editing
        if prompt:
            self.name_entry.insert(0, prompt.name)
            self.content_text.insert("1.0", prompt.content)

        # Make modal
        self.transient(parent)
        self.grab_set()
        self.focus_force()

    def _setup_window(self):
        """Configure window"""
        title = "プロンプト編集" if self.prompt else "新規プロンプト"
        self.title(title)
        self.geometry("600x450")
        self.minsize(400, 300)

    def _create_widgets(self):
        """Create UI widgets"""
        # Name field
        name_frame = ctk.CTkFrame(self)
        name_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(name_frame, text="名前:").pack(side="left", padx=5)
        self.name_entry = ctk.CTkEntry(name_frame, width=400)
        self.name_entry.pack(side="left", fill="x", expand=True, padx=5)

        # Content field
        ctk.CTkLabel(self, text="プロンプト内容:").pack(anchor="w", padx=15)
        self.content_text = ctk.CTkTextbox(self, wrap="word")
        self.content_text.pack(fill="both", expand=True, padx=10, pady=5)

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

    def _save(self):
        """Save the prompt"""
        name = self.name_entry.get().strip()
        content = self.content_text.get("1.0", "end-1c").strip()

        if not name:
            self._show_error("名前を入力してください")
            return

        if not content:
            self._show_error("プロンプト内容を入力してください")
            return

        if self.prompt:
            # Update existing
            self.prompt.name = name
            self.prompt.content = content
            self.result = self.prompt
        else:
            # Create new
            self.result = Prompt(name, content)

        if self.on_save:
            self.on_save(self.result)

        self.destroy()

    def _show_error(self, message: str):
        """Show error message"""
        error = ctk.CTkToplevel(self)
        error.title("エラー")
        error.geometry("250x100")
        error.transient(self)
        error.grab_set()

        ctk.CTkLabel(error, text=message).pack(pady=20)
        ctk.CTkButton(error, text="OK", command=error.destroy).pack()


class PromptManagerWindow(ctk.CTkToplevel):
    """Window for managing prompts"""

    def __init__(self, parent, storage: PromptStorage, on_select=None):
        super().__init__(parent)

        self.storage = storage
        self.on_select = on_select
        self.selected_prompt: Optional[Prompt] = None

        self._setup_window()
        self._create_widgets()
        self._refresh_list()

        self.transient(parent)
        self.grab_set()

    def _setup_window(self):
        """Configure window"""
        self.title("プロンプト管理")
        self.geometry("600x500")
        self.minsize(500, 400)

    def _create_widgets(self):
        """Create UI widgets"""
        # Toolbar
        toolbar = ctk.CTkFrame(self)
        toolbar.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            toolbar,
            text="+ 新規作成",
            width=100,
            command=self._new_prompt
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            toolbar,
            text="編集",
            width=80,
            command=self._edit_prompt
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            toolbar,
            text="削除",
            width=80,
            fg_color="red",
            command=self._delete_prompt
        ).pack(side="left", padx=5)

        # Prompt list
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.prompt_list = ctk.CTkScrollableFrame(list_frame)
        self.prompt_list.pack(fill="both", expand=True)

        # Preview
        ctk.CTkLabel(self, text="プレビュー:").pack(anchor="w", padx=15)
        self.preview_text = ctk.CTkTextbox(self, height=100, state="disabled")
        self.preview_text.pack(fill="x", padx=10, pady=5)

        # Action buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            btn_frame,
            text="閉じる",
            fg_color="gray",
            command=self.destroy
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="選択して実行",
            fg_color="green",
            command=self._select_and_run
        ).pack(side="right", padx=5)

    def _refresh_list(self):
        """Refresh the prompt list"""
        for widget in self.prompt_list.winfo_children():
            widget.destroy()

        prompts = self.storage.get_all()

        if not prompts:
            ctk.CTkLabel(
                self.prompt_list,
                text="プロンプトがありません",
                text_color="gray"
            ).pack(pady=20)
            return

        for prompt in sorted(prompts, key=lambda p: p.name.lower()):
            self._create_prompt_item(prompt)

    def _create_prompt_item(self, prompt: Prompt):
        """Create a list item for a prompt"""
        frame = ctk.CTkFrame(self.prompt_list)
        frame.pack(fill="x", pady=2)

        # Radio-like selection
        btn = ctk.CTkButton(
            frame,
            text=prompt.name,
            anchor="w",
            fg_color="transparent" if self.selected_prompt != prompt else ("gray70", "gray30"),
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            command=lambda p=prompt: self._select_prompt(p)
        )
        btn.pack(fill="x", padx=5, pady=2)

    def _select_prompt(self, prompt: Prompt):
        """Select a prompt"""
        self.selected_prompt = prompt
        self._refresh_list()

        # Update preview
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", prompt.content[:500])
        if len(prompt.content) > 500:
            self.preview_text.insert("end", "...")
        self.preview_text.configure(state="disabled")

    def _new_prompt(self):
        """Create new prompt"""
        PromptEditorDialog(self, on_save=self._save_prompt)

    def _edit_prompt(self):
        """Edit selected prompt"""
        if not self.selected_prompt:
            return
        PromptEditorDialog(self, self.selected_prompt, on_save=self._save_prompt)

    def _save_prompt(self, prompt: Prompt):
        """Save prompt callback"""
        self.storage.save(prompt)
        self._refresh_list()

    def _delete_prompt(self):
        """Delete selected prompt"""
        if not self.selected_prompt:
            return

        # Confirm
        confirm = ctk.CTkToplevel(self)
        confirm.title("確認")
        confirm.geometry("300x120")
        confirm.transient(self)
        confirm.grab_set()

        ctk.CTkLabel(
            confirm,
            text=f"「{self.selected_prompt.name}」を削除しますか?"
        ).pack(pady=20)

        btn_frame = ctk.CTkFrame(confirm)
        btn_frame.pack(fill="x", padx=20)

        ctk.CTkButton(
            btn_frame,
            text="キャンセル",
            fg_color="gray",
            command=confirm.destroy
        ).pack(side="left", padx=5)

        def do_delete():
            self.storage.delete(self.selected_prompt.id)
            self.selected_prompt = None
            confirm.destroy()
            self._refresh_list()

        ctk.CTkButton(
            btn_frame,
            text="削除",
            fg_color="red",
            command=do_delete
        ).pack(side="right", padx=5)

    def _select_and_run(self):
        """Select prompt and close"""
        if self.selected_prompt and self.on_select:
            self.on_select(self.selected_prompt)
        self.destroy()

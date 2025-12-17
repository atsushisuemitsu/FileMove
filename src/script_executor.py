"""Script Executor - Generate and run Python scripts"""

import os
import sys
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable
import customtkinter as ctk

from .api_client import OpenRouterClient
from .prompt_manager import Prompt, PromptStorage


class ScriptManager:
    """Manage generated scripts"""

    def __init__(self, scripts_dir: str):
        self.scripts_dir = Path(scripts_dir)
        self.scripts_dir.mkdir(parents=True, exist_ok=True)

    def get_script_path(self, prompt: Prompt) -> Path:
        """Get the script path for a prompt"""
        # Use prompt ID as filename
        return self.scripts_dir / f"{prompt.id}.py"

    def script_exists(self, prompt: Prompt) -> bool:
        """Check if script already exists for prompt"""
        return self.get_script_path(prompt).exists()

    def save_script(self, prompt: Prompt, code: str) -> Path:
        """Save generated script"""
        path = self.get_script_path(prompt)

        # Add header comment
        header = f'''"""
Auto-generated script from FileMove
Prompt: {prompt.name}
Generated: {datetime.now().isoformat()}
"""

'''
        with open(path, "w", encoding="utf-8") as f:
            f.write(header + code)

        return path

    def get_script(self, prompt: Prompt) -> Optional[str]:
        """Get script content if exists"""
        path = self.get_script_path(prompt)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def delete_script(self, prompt: Prompt) -> bool:
        """Delete script for prompt"""
        path = self.get_script_path(prompt)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_scripts(self) -> list[Path]:
        """List all generated scripts"""
        return list(self.scripts_dir.glob("*.py"))


class ScriptExecutor:
    """Execute Python scripts"""

    def __init__(self, scripts_dir: str, api_client: OpenRouterClient):
        self.script_manager = ScriptManager(scripts_dir)
        self.api_client = api_client
        self._current_process: Optional[subprocess.Popen] = None

    def generate_and_save(
        self,
        prompt: Prompt,
        force_regenerate: bool = False,
        on_progress: Optional[Callable[[str], None]] = None
    ) -> tuple[bool, str, Optional[Path]]:
        """
        Generate script from prompt and save.

        Returns:
            tuple: (success, message, script_path)
        """
        # Check if script already exists
        if not force_regenerate and self.script_manager.script_exists(prompt):
            path = self.script_manager.get_script_path(prompt)
            return True, "既存のスクリプトを使用", path

        if on_progress:
            on_progress("APIにリクエスト中...")

        success, result = self.api_client.generate_script(prompt.content)

        if not success:
            return False, result, None

        if on_progress:
            on_progress("スクリプトを保存中...")

        path = self.script_manager.save_script(prompt, result)
        return True, "スクリプト生成完了", path

    def run_script(
        self,
        script_path: Path,
        on_output: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[int], None]] = None
    ) -> subprocess.Popen:
        """Run a Python script"""
        python_exe = sys.executable

        process = subprocess.Popen(
            [python_exe, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(script_path.parent)
        )

        self._current_process = process

        # Read output in real-time
        def read_output():
            for line in process.stdout:
                if on_output:
                    on_output(line)

            process.wait()
            self._current_process = None

            if on_complete:
                on_complete(process.returncode)

        import threading
        threading.Thread(target=read_output, daemon=True).start()

        return process

    def stop_current(self):
        """Stop currently running script"""
        if self._current_process:
            self._current_process.terminate()
            self._current_process = None


class ScriptExecutorWindow(ctk.CTkToplevel):
    """Window for script generation and execution"""

    def __init__(
        self,
        parent,
        executor: ScriptExecutor,
        storage: PromptStorage
    ):
        super().__init__(parent)

        self.executor = executor
        self.storage = storage
        self.selected_prompt: Optional[Prompt] = None
        self.script_path: Optional[Path] = None

        self._setup_window()
        self._create_widgets()
        self._refresh_prompt_list()

        self.transient(parent)

    def _setup_window(self):
        """Configure window"""
        self.title("スクリプト生成・実行")
        self.geometry("700x600")
        self.minsize(600, 500)

    def _create_widgets(self):
        """Create UI widgets"""
        # Left panel - Prompt selection
        left_frame = ctk.CTkFrame(self)
        left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(left_frame, text="プロンプト選択:").pack(anchor="w", padx=5)
        self.prompt_list = ctk.CTkScrollableFrame(left_frame, width=200)
        self.prompt_list.pack(fill="both", expand=True, pady=5)

        # Right panel - Execution
        right_frame = ctk.CTkFrame(self)
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Status
        self.status_label = ctk.CTkLabel(
            right_frame,
            text="プロンプトを選択してください",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(anchor="w", pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(right_frame)
        btn_frame.pack(fill="x", pady=10)

        self.generate_btn = ctk.CTkButton(
            btn_frame,
            text="生成",
            command=self._generate_script,
            state="disabled"
        )
        self.generate_btn.pack(side="left", padx=5)

        self.regenerate_btn = ctk.CTkButton(
            btn_frame,
            text="再生成",
            fg_color="orange",
            command=self._regenerate_script,
            state="disabled"
        )
        self.regenerate_btn.pack(side="left", padx=5)

        self.run_btn = ctk.CTkButton(
            btn_frame,
            text="実行",
            fg_color="green",
            command=self._run_script,
            state="disabled"
        )
        self.run_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="停止",
            fg_color="red",
            command=self._stop_script,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)

        # Output
        ctk.CTkLabel(right_frame, text="出力:").pack(anchor="w")
        self.output_text = ctk.CTkTextbox(right_frame, wrap="word")
        self.output_text.pack(fill="both", expand=True, pady=5)

        # Clear button
        ctk.CTkButton(
            right_frame,
            text="出力をクリア",
            width=100,
            command=self._clear_output
        ).pack(anchor="e", pady=5)

    def _refresh_prompt_list(self):
        """Refresh prompt list"""
        for widget in self.prompt_list.winfo_children():
            widget.destroy()

        prompts = self.storage.get_all()

        if not prompts:
            ctk.CTkLabel(
                self.prompt_list,
                text="プロンプトがありません\nプロンプト管理から作成してください",
                text_color="gray"
            ).pack(pady=20)
            return

        for prompt in sorted(prompts, key=lambda p: p.name.lower()):
            has_script = self.executor.script_manager.script_exists(prompt)
            indicator = "✓ " if has_script else "  "

            btn = ctk.CTkButton(
                self.prompt_list,
                text=f"{indicator}{prompt.name}",
                anchor="w",
                fg_color="transparent" if self.selected_prompt != prompt else ("gray70", "gray30"),
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                command=lambda p=prompt: self._select_prompt(p)
            )
            btn.pack(fill="x", pady=2)

    def _select_prompt(self, prompt: Prompt):
        """Select a prompt"""
        self.selected_prompt = prompt
        self._refresh_prompt_list()

        # Check if script exists
        has_script = self.executor.script_manager.script_exists(prompt)

        if has_script:
            self.script_path = self.executor.script_manager.get_script_path(prompt)
            self.status_label.configure(text=f"スクリプト: {self.script_path.name}")
            self.run_btn.configure(state="normal")
            self.regenerate_btn.configure(state="normal")
            self.generate_btn.configure(state="disabled")
        else:
            self.script_path = None
            self.status_label.configure(text="スクリプト未生成")
            self.run_btn.configure(state="disabled")
            self.regenerate_btn.configure(state="disabled")
            self.generate_btn.configure(state="normal")

    def _generate_script(self):
        """Generate script from prompt"""
        if not self.selected_prompt:
            return

        self._set_generating(True)
        self._append_output("スクリプト生成開始...\n")

        def do_generate():
            success, message, path = self.executor.generate_and_save(
                self.selected_prompt,
                force_regenerate=False,
                on_progress=lambda m: self.after(0, lambda: self._append_output(f"{m}\n"))
            )

            def update_ui():
                self._set_generating(False)
                self._append_output(f"{message}\n")

                if success and path:
                    self.script_path = path
                    self.status_label.configure(text=f"スクリプト: {path.name}")
                    self.run_btn.configure(state="normal")
                    self.regenerate_btn.configure(state="normal")
                    self.generate_btn.configure(state="disabled")
                    self._refresh_prompt_list()

            self.after(0, update_ui)

        import threading
        threading.Thread(target=do_generate, daemon=True).start()

    def _regenerate_script(self):
        """Force regenerate script"""
        if not self.selected_prompt:
            return

        self._set_generating(True)
        self._append_output("スクリプト再生成開始...\n")

        def do_regenerate():
            success, message, path = self.executor.generate_and_save(
                self.selected_prompt,
                force_regenerate=True,
                on_progress=lambda m: self.after(0, lambda: self._append_output(f"{m}\n"))
            )

            def update_ui():
                self._set_generating(False)
                self._append_output(f"{message}\n")

                if success and path:
                    self.script_path = path
                    self._refresh_prompt_list()

            self.after(0, update_ui)

        import threading
        threading.Thread(target=do_regenerate, daemon=True).start()

    def _run_script(self):
        """Run the generated script"""
        if not self.script_path or not self.script_path.exists():
            return

        self._append_output(f"\n{'='*40}\n実行開始: {self.script_path.name}\n{'='*40}\n")
        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        self.executor.run_script(
            self.script_path,
            on_output=lambda line: self.after(0, lambda l=line: self._append_output(l)),
            on_complete=lambda code: self.after(0, lambda c=code: self._on_script_complete(c))
        )

    def _stop_script(self):
        """Stop running script"""
        self.executor.stop_current()
        self._append_output("\n実行を停止しました\n")
        self.run_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def _on_script_complete(self, return_code: int):
        """Handle script completion"""
        status = "正常終了" if return_code == 0 else f"エラー終了 (コード: {return_code})"
        self._append_output(f"\n{'='*40}\n{status}\n{'='*40}\n")
        self.run_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def _set_generating(self, generating: bool):
        """Update UI for generating state"""
        state = "disabled" if generating else "normal"
        self.generate_btn.configure(state=state if not generating and not self.script_path else "disabled")
        self.regenerate_btn.configure(state=state if self.script_path else "disabled")

    def _append_output(self, text: str):
        """Append text to output"""
        self.output_text.insert("end", text)
        self.output_text.see("end")

    def _clear_output(self):
        """Clear output"""
        self.output_text.delete("1.0", "end")

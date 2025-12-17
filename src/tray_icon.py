"""System Tray Icon - pystray integration for Windows"""

import threading
from typing import Callable, Optional
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item


def create_icon_image(size: int = 64, color: str = "#4A90D9") -> Image.Image:
    """Create a simple folder icon image"""
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Parse color
    if color.startswith('#'):
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        fill_color = (r, g, b, 255)
    else:
        fill_color = (74, 144, 217, 255)

    # Draw folder shape
    margin = size // 8
    tab_height = size // 4
    tab_width = size // 3

    # Folder body
    points = [
        (margin, margin + tab_height),
        (margin + tab_width, margin + tab_height),
        (margin + tab_width + margin, margin),
        (size - margin, margin),
        (size - margin, size - margin),
        (margin, size - margin),
    ]
    draw.polygon(points, fill=fill_color)

    # Lighter shade for depth
    lighter = tuple(min(c + 40, 255) for c in fill_color[:3]) + (255,)
    draw.rectangle(
        [margin, margin + tab_height + margin, size - margin, size - margin - margin],
        fill=lighter
    )

    return image


class TrayIcon:
    """System tray icon manager"""

    def __init__(
        self,
        on_settings: Optional[Callable] = None,
        on_prompts: Optional[Callable] = None,
        on_scripts: Optional[Callable] = None,
        on_quit: Optional[Callable] = None,
        on_toggle_watch: Optional[Callable] = None
    ):
        self.on_settings = on_settings
        self.on_prompts = on_prompts
        self.on_scripts = on_scripts
        self.on_quit = on_quit
        self.on_toggle_watch = on_toggle_watch

        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None
        self._watching = False

    def _create_menu(self) -> pystray.Menu:
        """Create the tray icon menu"""
        watch_text = "監視停止" if self._watching else "監視開始"

        return pystray.Menu(
            item(watch_text, self._on_toggle_watch),
            item("─────────", None, enabled=False),
            item("設定", self._on_settings),
            item("プロンプト管理", self._on_prompts),
            item("スクリプト実行", self._on_scripts),
            item("─────────", None, enabled=False),
            item("終了", self._on_quit)
        )

    def _on_settings(self, icon, item):
        """Handle settings menu click"""
        if self.on_settings:
            self.on_settings()

    def _on_prompts(self, icon, item):
        """Handle prompts menu click"""
        if self.on_prompts:
            self.on_prompts()

    def _on_scripts(self, icon, item):
        """Handle scripts menu click"""
        if self.on_scripts:
            self.on_scripts()

    def _on_quit(self, icon, item):
        """Handle quit menu click"""
        if self.on_quit:
            self.on_quit()
        self.stop()

    def _on_toggle_watch(self, icon, item):
        """Handle toggle watch menu click"""
        if self.on_toggle_watch:
            self.on_toggle_watch()

    def set_watching(self, watching: bool):
        """Update watching state and refresh menu"""
        self._watching = watching
        if self._icon:
            self._icon.menu = self._create_menu()

    def start(self):
        """Start the tray icon"""
        if self._icon is not None:
            return

        image = create_icon_image()
        self._icon = pystray.Icon(
            "FileMove",
            image,
            "FileMove",
            menu=self._create_menu()
        )

        # Run in separate thread
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the tray icon"""
        if self._icon:
            self._icon.stop()
            self._icon = None

        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def update_tooltip(self, text: str):
        """Update the tray icon tooltip"""
        if self._icon:
            self._icon.title = text

    def notify(self, title: str, message: str):
        """Show a notification"""
        if self._icon:
            self._icon.notify(message, title)

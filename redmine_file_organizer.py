# -*- coding: utf-8 -*-
"""
Redmine ダウンロードファイル整理ツール（常駐版）
===============================================
Redmineからダウンロードしたファイルを、チケットタイトルに基づいて
自動的にフォルダ分類するツール

機能:
- システムトレイ常駐
- ダウンロードフォルダ常時監視
- 新規Redmineファイル自動検出・通知
- ワンクリック自動整理

フォルダ構造例:
[Nanya錦興][G2128][AJ005422]装置により検査時間が遅い時があります。
=> D:\\@USER\\Nanya錦興\\G2128\\[AJ005422]装置により検査時間が遅い時があります。\\
"""

import os
import re
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime
import webbrowser
import threading
import time
import sys
import json
import base64

# requestsがない場合
try:
    import requests
    from requests.auth import HTTPBasicAuth
except ImportError:
    requests = None

# システムトレイ用ライブラリ
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

# ファイル監視用ライブラリ
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


class RedmineClient:
    """Redmine API/Webクライアント"""

    def __init__(self, host):
        self.host = host
        self.base_url = f"https://{host}"
        self.session = requests.Session() if requests else None
        self.logged_in = False
        self.username = None

    def login(self, username, password):
        """Redmineにログイン"""
        if not self.session:
            return False, "requestsライブラリがインストールされていません"

        try:
            # ログインページを取得してCSRFトークンを取得
            login_url = f"{self.base_url}/login"
            response = self.session.get(login_url, timeout=10)

            if response.status_code != 200:
                return False, f"ログインページの取得に失敗: {response.status_code}"

            # CSRFトークンを抽出
            csrf_token = None
            csrf_match = re.search(r'name="authenticity_token"\s+value="([^"]+)"', response.text)
            if csrf_match:
                csrf_token = csrf_match.group(1)

            # ログインPOST
            login_data = {
                'username': username,
                'password': password,
                'login': 'ログイン',
                'back_url': self.base_url
            }
            if csrf_token:
                login_data['authenticity_token'] = csrf_token

            response = self.session.post(login_url, data=login_data, timeout=10)

            # ログイン成功判定（リダイレクトされるか、ログアウトリンクがあるか）
            if 'logout' in response.text.lower() or response.url != login_url:
                self.logged_in = True
                self.username = username
                return True, "ログイン成功"
            else:
                return False, "ユーザー名またはパスワードが正しくありません"

        except requests.exceptions.Timeout:
            return False, "接続タイムアウト"
        except requests.exceptions.ConnectionError:
            return False, "接続エラー: サーバーに接続できません"
        except Exception as e:
            return False, f"エラー: {str(e)}"

    def get_issue_title(self, issue_number):
        """チケットタイトルを取得"""
        if not self.session:
            return None, "requestsライブラリがインストールされていません"

        if not self.logged_in:
            return None, "ログインが必要です"

        try:
            # まずAPIを試す
            api_url = f"{self.base_url}/issues/{issue_number}.json"
            response = self.session.get(api_url, timeout=10)

            if response.status_code == 200:
                try:
                    data = response.json()
                    title = data.get('issue', {}).get('subject', '')
                    if title:
                        return title, None
                except:
                    pass

            # APIが使えない場合はHTMLから抽出
            html_url = f"{self.base_url}/issues/{issue_number}"
            response = self.session.get(html_url, timeout=10)

            if response.status_code == 200:
                # タイトルを抽出 (h2.subject または title タグ)
                # パターン1: <h2><div class="subject">...</div></h2>
                subject_match = re.search(r'<div class="subject"[^>]*>\s*<h2>([^<]+)</h2>', response.text)
                if subject_match:
                    return subject_match.group(1).strip(), None

                # パターン2: <h2 class="subject">...</h2>
                subject_match = re.search(r'<h2[^>]*class="[^"]*subject[^"]*"[^>]*>([^<]+)</h2>', response.text)
                if subject_match:
                    return subject_match.group(1).strip(), None

                # パターン3: titleタグから
                title_match = re.search(r'<title>([^<]+)</title>', response.text)
                if title_match:
                    title = title_match.group(1).strip()
                    # "Bug #12345: タイトル - Redmine" のような形式から抽出
                    clean_match = re.search(r'#\d+[:\s]+(.+?)\s*[-–]\s*\w+$', title)
                    if clean_match:
                        return clean_match.group(1).strip(), None
                    # そのまま返す
                    return title, None

                return None, "チケットタイトルを抽出できませんでした"
            elif response.status_code == 404:
                return None, f"チケット #{issue_number} が見つかりません"
            elif response.status_code == 403:
                return None, "アクセス権限がありません"
            else:
                return None, f"取得エラー: {response.status_code}"

        except requests.exceptions.Timeout:
            return None, "接続タイムアウト"
        except requests.exceptions.ConnectionError:
            return None, "接続エラー"
        except Exception as e:
            return None, f"エラー: {str(e)}"


class LoginDialog(tk.Toplevel):
    """ログインダイアログ"""

    def __init__(self, parent, title="Redmine ログイン", initial_username="", initial_password=""):
        super().__init__(parent)
        self.title(title)
        self.result = None
        self.initial_username = initial_username
        self.initial_password = initial_password

        # モーダルダイアログとして設定
        self.transient(parent)
        self.grab_set()

        # ウィンドウサイズと位置
        self.geometry("350x180")
        self.resizable(False, False)

        # 中央配置
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 350) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 180) // 2
        self.geometry(f"+{x}+{y}")

        self.create_widgets()

        # Enterキーでログイン
        self.bind('<Return>', lambda e: self.on_login())
        self.bind('<Escape>', lambda e: self.on_cancel())

    def create_widgets(self):
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # ユーザー名
        ttk.Label(frame, text="ユーザー名:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.username_entry = ttk.Entry(frame, width=30)
        self.username_entry.grid(row=0, column=1, pady=5, padx=(10, 0))
        if self.initial_username:
            self.username_entry.insert(0, self.initial_username)

        # パスワード
        ttk.Label(frame, text="パスワード:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.password_entry = ttk.Entry(frame, width=30, show="*")
        self.password_entry.grid(row=1, column=1, pady=5, padx=(10, 0))
        if self.initial_password:
            self.password_entry.insert(0, self.initial_password)

        # フォーカス設定（パスワードが空なら、そこにフォーカス）
        if self.initial_username and not self.initial_password:
            self.password_entry.focus_set()
        else:
            self.username_entry.focus_set()

        # ボタン
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="ログイン", command=self.on_login, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="キャンセル", command=self.on_cancel, width=12).pack(side=tk.LEFT, padx=5)

    def on_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username:
            messagebox.showwarning("入力エラー", "ユーザー名を入力してください", parent=self)
            return

        if not password:
            messagebox.showwarning("入力エラー", "パスワードを入力してください", parent=self)
            return

        self.result = (username, password)
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()


class DownloadsMonitor:
    """ダウンロードフォルダ監視クラス"""

    def __init__(self, folder_path, callback, log_func=None):
        """
        Args:
            folder_path: 監視するフォルダパス
            callback: 新規ファイル検出時のコールバック関数(file_path)
            log_func: ログ出力関数（オプション）
        """
        self.folder_path = folder_path
        self.callback = callback
        self.log_func = log_func
        self.observer = None
        self.running = False
        self.processed_files = set()  # 既に処理したファイルを追跡

    def start(self):
        """監視を開始"""
        if not WATCHDOG_AVAILABLE:
            return False

        if self.running:
            return True

        # 現在のファイルを記録（起動時のファイルは無視）
        if os.path.exists(self.folder_path):
            for f in os.listdir(self.folder_path):
                self.processed_files.add(os.path.join(self.folder_path, f))

        class Handler(FileSystemEventHandler):
            def __init__(handler_self, monitor):
                handler_self.monitor = monitor
                handler_self.log_func = None  # ログ関数を後で設定

            def _should_process(handler_self, file_path):
                """処理すべきファイルかチェック"""
                if not file_path:
                    return False
                filename = os.path.basename(file_path)
                # 一時ファイルやシステムファイルをスキップ
                if filename.startswith('.'):
                    return False
                if filename.endswith(('.tmp', '.crdownload', '.partial', '.download')):
                    return False
                return True

            def on_any_event(handler_self, event):
                """全イベントをログ（デバッグ用）"""
                if handler_self.log_func and not event.is_directory:
                    handler_self.log_func(f"[DEBUG] watchdog event: {event.event_type} - {event.src_path}")

            def on_created(handler_self, event):
                """ファイル作成イベント"""
                if not event.is_directory:
                    file_path = event.src_path
                    if handler_self.log_func:
                        handler_self.log_func(f"on_created: {file_path}")
                    if handler_self._should_process(file_path):
                        # 少し待ってからコールバック（ダウンロード完了を待つ）
                        threading.Timer(2.0, lambda: handler_self.monitor._on_file_created(file_path)).start()

            def on_moved(handler_self, event):
                """ファイル移動/リネームイベント（ダウンロード完了時に発生することが多い）"""
                if not event.is_directory:
                    # dest_path が新しいファイル名
                    file_path = event.dest_path
                    if handler_self.log_func:
                        handler_self.log_func(f"on_moved: {event.src_path} -> {file_path}")
                    if handler_self._should_process(file_path):
                        # リネーム完了後すぐに処理
                        threading.Timer(1.0, lambda: handler_self.monitor._on_file_created(file_path)).start()

            def on_modified(handler_self, event):
                """ファイル変更イベント（ダウンロード完了時に発生することがある）"""
                if not event.is_directory:
                    file_path = event.src_path
                    if handler_self._should_process(file_path):
                        if handler_self.log_func:
                            handler_self.log_func(f"on_modified: {file_path}")
                        # 変更イベントは頻繁に発生するため、少し長めに待つ
                        threading.Timer(3.0, lambda: handler_self.monitor._on_file_created(file_path)).start()

        handler = Handler(self)
        handler.log_func = self.log_func  # ログ関数を設定
        self.observer = Observer()
        self.observer.schedule(handler, self.folder_path, recursive=False)
        self.observer.start()
        self.running = True
        return True

    def stop(self):
        """監視を停止"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
        self.running = False

    def _on_file_created(self, file_path):
        """ファイル作成時の内部処理"""
        if file_path in self.processed_files:
            return
        if not os.path.exists(file_path):
            return
        self.processed_files.add(file_path)
        # コールバック呼び出し
        if self.callback:
            self.callback(file_path)


class RedmineFileOrganizer:
    """Redmineダウンロードファイル整理クラス"""

    # 設定
    DOWNLOADS_FOLDER = os.path.expanduser(r"~\Downloads")
    BASE_OUTPUT_FOLDER = r"D:\@USER"
    REDMINE_HOST = "read-sln.cloud.redmine.jp"
    LOG_FILE = os.path.join(os.path.expanduser("~"), "RedmineFileOrganizer_log.txt")
    CONFIG_FILE = os.path.join(os.path.expanduser("~"), "RedmineFileOrganizer_config.json")

    def __init__(self):
        self.root = None
        self.files_listbox = None
        self.title_entry = None
        self.preview_label = None
        self.selected_file = None
        self.detected_files = []
        self.redmine_client = RedmineClient(self.REDMINE_HOST)
        self.status_label = None
        self.progress_label = None
        self.auto_processing = False
        self.last_target_folder = None  # 最後に移動したファイルのフォルダ
        # 常駐機能用
        self.tray_icon = None
        self.monitor = None
        self.auto_organize_enabled = None  # GUIで初期化
        self.monitoring_enabled = None  # GUIで初期化
        self.pending_files = []  # 検出待ちファイル
        self.monitor_status_label = None
        self.notification_label = None  # 通知ラベル
        self.notification_frame = None  # 通知フレーム
        # ログ初期化
        self.write_log("=== アプリケーション起動 ===")

    def save_credentials(self, username, password):
        """ログイン情報を保存（パスワードは難読化）"""
        try:
            # パスワードを難読化（Base64エンコード）
            encoded_password = base64.b64encode(password.encode('utf-8')).decode('utf-8')
            config = {
                'username': username,
                'password': encoded_password,
                'saved_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            self.write_log(f"ログイン情報を保存: {username}")
        except Exception as e:
            self.write_log(f"ログイン情報の保存に失敗: {e}")

    def load_credentials(self):
        """保存されたログイン情報を読み込む"""
        try:
            if not os.path.exists(self.CONFIG_FILE):
                return None, None
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            username = config.get('username')
            encoded_password = config.get('password')
            if username and encoded_password:
                password = base64.b64decode(encoded_password.encode('utf-8')).decode('utf-8')
                self.write_log(f"保存されたログイン情報を読み込み: {username}")
                return username, password
        except Exception as e:
            self.write_log(f"ログイン情報の読み込みに失敗: {e}")
        return None, None

    def auto_login(self):
        """保存された情報で自動ログイン"""
        username, password = self.load_credentials()
        if username and password:
            self.write_log(f"自動ログイン試行: {username}")

            def do_login():
                success, message = self.redmine_client.login(username, password)
                if self.root:
                    self.root.after(0, lambda: self._on_auto_login_complete(success, message, username))

            thread = threading.Thread(target=do_login, daemon=True)
            thread.start()
            return True
        return False

    def _on_auto_login_complete(self, success, message, username):
        """自動ログイン完了時のコールバック"""
        if success:
            self.write_log(f"自動ログイン成功: {username}")
            if self.status_label:
                self.status_label.config(
                    text=f"ログイン中: {username}",
                    foreground='green'
                )
            self.update_auto_buttons()
            self.show_notification("自動ログイン", f"Redmineにログインしました: {username}")
        else:
            self.write_log(f"自動ログイン失敗: {message}")
            if self.status_label:
                self.status_label.config(text="未ログイン", foreground='gray')

    def write_log(self, message):
        """ログをファイルに書き込む"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_line = f"[{timestamp}] {message}\n"
            with open(self.LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception as e:
            # ログ書き込み失敗時はデスクトップにフォールバック
            try:
                fallback_log = os.path.join(os.path.expanduser("~"), "Desktop", "RedmineFileOrganizer_log.txt")
                with open(fallback_log, "a", encoding="utf-8") as f:
                    f.write(f"[LOG ERROR: {e}]\n")
                    f.write(log_line)
            except:
                pass

    def get_zone_identifier(self, file_path):
        """ファイルのZone.Identifierを取得"""
        try:
            # CREATE_NO_WINDOW でコンソールウィンドウを表示しない
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            result = subprocess.run(
                ["powershell", "-WindowStyle", "Hidden", "-Command",
                 f"Get-Content -Path '{file_path}' -Stream Zone.Identifier"],
                capture_output=True,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5
            )
            # Try multiple encodings
            output = None
            for encoding in ['utf-8', 'cp932', 'shift-jis', 'latin-1']:
                try:
                    output = result.stdout.decode(encoding)
                    break
                except (UnicodeDecodeError, AttributeError):
                    continue
            return output
        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            return None

    def parse_zone_identifier(self, zone_info):
        """Zone.Identifierをパースしてダウンロード情報を取得"""
        if not zone_info:
            return None

        info = {}
        for line in zone_info.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                info[key.strip()] = value.strip()
        return info

    def is_redmine_file(self, file_path):
        """Redmineからダウンロードされたファイルか判定"""
        zone_info = self.get_zone_identifier(file_path)
        if not zone_info:
            return False, None

        parsed = self.parse_zone_identifier(zone_info)
        if not parsed:
            return False, None

        referrer = parsed.get('ReferrerUrl', '')
        host_url = parsed.get('HostUrl', '')

        if self.REDMINE_HOST in referrer or self.REDMINE_HOST in host_url:
            # 添付ファイルIDを抽出
            attachment_match = re.search(r'/attachments/(\d+)', referrer)
            attachment_id = attachment_match.group(1) if attachment_match else None

            # チケット番号をReferrerUrlから抽出（信頼性が高い）
            issue_number = None
            issue_match = re.search(r'/issues/(\d+)', referrer)
            if issue_match:
                issue_number = issue_match.group(1)

            return True, {
                'referrer': referrer,
                'host_url': host_url,
                'attachment_id': attachment_id,
                'issue_number': issue_number,
                'zone_id': parsed.get('ZoneId', '')
            }

        return False, None

    def scan_downloads_folder(self):
        """ダウンロードフォルダをスキャンしてRedmineファイルを検出"""
        redmine_files = []

        if not os.path.exists(self.DOWNLOADS_FOLDER):
            return redmine_files

        for filename in os.listdir(self.DOWNLOADS_FOLDER):
            file_path = os.path.join(self.DOWNLOADS_FOLDER, filename)

            if not os.path.isfile(file_path):
                continue

            is_redmine, info = self.is_redmine_file(file_path)
            if is_redmine:
                redmine_files.append({
                    'path': file_path,
                    'filename': filename,
                    'info': info
                })

        # 更新日時の新しい順にソート
        redmine_files.sort(key=lambda x: os.path.getmtime(x['path']), reverse=True)
        return redmine_files

    def parse_ticket_title(self, title):
        """
        チケットタイトルをパースしてフォルダ構造を取得

        形式: [フォルダ1][フォルダ2][フォルダ3]タイトル
        例: [Nanya錦興][G2128][AJ005422]装置により検査時間が遅い時があります。
        """
        # パターン: [xxx][xxx][xxx]残り または [xxx][xxx]残り
        pattern3 = r'^\[([^\]]+)\]\[([^\]]+)\](.+)$'
        pattern2 = r'^\[([^\]]+)\](.+)$'

        match3 = re.match(pattern3, title.strip())
        if match3:
            return {
                'folder1': match3.group(1),
                'folder2': match3.group(2),
                'folder3': match3.group(3).strip(),
                'levels': 3
            }

        match2 = re.match(pattern2, title.strip())
        if match2:
            return {
                'folder1': match2.group(1),
                'folder2': match2.group(2).strip(),
                'folder3': None,
                'levels': 2
            }

        return None

    def build_target_path(self, parsed_title, file_path=None):
        """パースしたタイトルから移動先パスを構築（日付フォルダ付き）"""
        if not parsed_title:
            return None

        # ダウンロード日を取得（ファイルの更新日時から）
        if file_path and os.path.exists(file_path):
            mtime = os.path.getmtime(file_path)
            date_folder = datetime.fromtimestamp(mtime).strftime("%Y%m%d")
        else:
            date_folder = datetime.now().strftime("%Y%m%d")

        if parsed_title['levels'] == 3:
            return os.path.join(
                self.BASE_OUTPUT_FOLDER,
                parsed_title['folder1'],
                parsed_title['folder2'],
                parsed_title['folder3'],
                date_folder
            )
        elif parsed_title['levels'] == 2:
            return os.path.join(
                self.BASE_OUTPUT_FOLDER,
                parsed_title['folder1'],
                parsed_title['folder2'],
                date_folder
            )

        return None

    def move_file(self, source_path, target_folder):
        """ファイルを移動"""
        if not os.path.exists(source_path):
            return False, "元ファイルが見つかりません"

        # フォルダ作成
        os.makedirs(target_folder, exist_ok=True)

        filename = os.path.basename(source_path)
        target_path = os.path.join(target_folder, filename)

        # 同名ファイルが存在する場合
        if os.path.exists(target_path):
            base, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{base}_{timestamp}{ext}"
            target_path = os.path.join(target_folder, new_filename)

        try:
            shutil.move(source_path, target_path)
            return True, target_path
        except Exception as e:
            return False, str(e)

    def open_folder_safe(self, path):
        """フォルダを安全に開く（フリーズ防止）"""
        if not path:
            self.write_log("フォルダオープン失敗: パスが空")
            return

        self.write_log(f"フォルダオープン試行: {path}")

        def do_open():
            try:
                # パスを正規化
                normalized_path = os.path.normpath(path)

                # ファイルパスの場合は親ディレクトリを取得
                if os.path.isfile(normalized_path):
                    self.write_log(f"ファイルパスが渡されました。親フォルダを開きます: {normalized_path}")
                    normalized_path = os.path.dirname(normalized_path)

                # フォルダが存在しない場合は作成
                if not os.path.exists(normalized_path):
                    os.makedirs(normalized_path, exist_ok=True)
                    self.write_log(f"フォルダ作成: {normalized_path}")

                # Windows専用: explorer.exe を使用
                if sys.platform == 'win32':
                    self.write_log(f"正規化パス: {normalized_path}")

                    # explorer.exe を直接呼び出す（フォルダとして確実に開く）
                    subprocess.run(['explorer.exe', normalized_path], check=False)
                    self.write_log(f"フォルダオープン成功: {normalized_path}")
                else:
                    subprocess.Popen(['xdg-open', normalized_path])
            except Exception as e:
                self.write_log(f"フォルダオープン失敗: {path} - {type(e).__name__}: {e}")
                # フォールバック: os.startfile を試す
                try:
                    folder_path = os.path.dirname(path) if os.path.isfile(path) else path
                    os.startfile(os.path.normpath(folder_path))
                    self.write_log(f"フォールバック成功: os.startfile {folder_path}")
                except Exception as e2:
                    self.write_log(f"フォールバックも失敗: {e2}")

        # daemon=True でメインスレッド終了時に自動終了
        thread = threading.Thread(target=do_open, daemon=True)
        thread.start()

    def show_move_notification(self, success, filename, target_folder):
        """移動結果を通知し、3秒後にフォルダを開く"""
        if not self.root or not self.notification_frame:
            # GUIがない場合は直接フォルダを開く
            if success:
                self.open_folder_safe(target_folder)
            return

        def do_show():
            try:
                if success:
                    message = f"✅ 移動成功: {filename}\n📁 {target_folder}"
                    self.notification_frame.config(bg='#4CAF50')
                    self.notification_label.config(bg='#4CAF50', fg='white', text=message)
                else:
                    message = f"❌ 移動失敗: {filename}"
                    self.notification_frame.config(bg='#f44336')
                    self.notification_label.config(bg='#f44336', fg='white', text=message)

                # 通知フレームを表示（一番上に）
                self.notification_frame.pack(fill=tk.X, pady=(0, 10), before=self.notification_frame.master.winfo_children()[1])

                self.write_log(f"通知表示: {message}")

                # 3秒後に通知を非表示にしてフォルダを開く
                def hide_and_open():
                    try:
                        self.notification_frame.pack_forget()
                        if success:
                            self.write_log(f"3秒経過、フォルダを開く: {target_folder}")
                            self.open_folder_safe(target_folder)
                    except Exception as e:
                        self.write_log(f"通知非表示/フォルダオープン失敗: {e}")

                self.root.after(3000, hide_and_open)
            except Exception as e:
                self.write_log(f"通知表示失敗: {e}")
                if success:
                    self.open_folder_safe(target_folder)

        # GUIスレッドで実行
        if self.root:
            self.root.after(0, do_show)

    def open_preview_folder(self):
        """プレビューに表示されている移動先フォルダを開く"""
        if not self.preview_label:
            return

        # プレビューラベルから移動先パスを取得
        preview_text = self.preview_label.cget("text")
        if preview_text.startswith("移動先: "):
            folder_path = preview_text.replace("移動先: ", "").strip()
            if folder_path and os.path.exists(folder_path):
                self.open_folder_safe(folder_path)
            elif folder_path:
                # フォルダが存在しない場合は作成して開く
                try:
                    os.makedirs(folder_path, exist_ok=True)
                    self.open_folder_safe(folder_path)
                except Exception as e:
                    messagebox.showerror("エラー", f"フォルダを作成できません: {e}")
        else:
            # プレビューがない場合はベースフォルダを開く
            self.open_folder_safe(self.BASE_OUTPUT_FOLDER)

    # ========== 常駐機能 ==========

    def create_tray_icon(self):
        """システムトレイアイコンを作成"""
        if not TRAY_AVAILABLE:
            return None

        # シンプルなアイコンを作成（赤い丸）
        def create_image():
            size = 64
            image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            # 背景円
            draw.ellipse([4, 4, size-4, size-4], fill=(70, 130, 180))
            # Rの文字（簡略化）
            draw.text((20, 15), "R", fill='white')
            return image

        menu = pystray.Menu(
            pystray.MenuItem("ウィンドウを表示", self.show_window),
            pystray.MenuItem("監視中" if self.monitoring_enabled.get() else "監視停止中",
                           lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("監視を開始/停止", self.toggle_monitoring),
            pystray.MenuItem("自動整理 ON/OFF", self.toggle_auto_organize),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("終了", self.quit_app)
        )

        icon = pystray.Icon(
            "RedmineOrganizer",
            create_image(),
            "Redmine ファイル整理ツール",
            menu
        )
        return icon

    def show_window(self, icon=None, item=None):
        """ウィンドウを表示"""
        if self.root:
            self.root.after(0, self._do_show_window)

    def _do_show_window(self):
        """メインスレッドでウィンドウを表示"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide_to_tray(self):
        """トレイに最小化"""
        if self.tray_icon:
            self.root.withdraw()

    def toggle_monitoring(self, icon=None, item=None):
        """監視のON/OFF切り替え"""
        if self.monitoring_enabled.get():
            self.stop_monitoring()
            if hasattr(self, 'monitor_btn') and self.monitor_btn:
                self.monitor_btn.config(text="監視開始")
        else:
            # start_monitoring は非同期で、完了時に _on_monitoring_started でボタン更新
            self.start_monitoring()

    def toggle_auto_organize(self, icon=None, item=None):
        """自動整理のON/OFF切り替え"""
        current = self.auto_organize_enabled.get()
        self.auto_organize_enabled.set(not current)
        status = "ON" if not current else "OFF"
        self.show_notification("設定変更", f"自動整理: {status}")

    def start_monitoring(self):
        """ファイル監視を開始（非ブロッキング）"""
        if not WATCHDOG_AVAILABLE:
            messagebox.showwarning("警告", "watchdogライブラリがインストールされていません")
            return

        # 別スレッドで監視を開始（UIをブロックしないため）
        def do_start():
            try:
                if self.monitor is None:
                    self.monitor = DownloadsMonitor(self.DOWNLOADS_FOLDER, self.on_new_file_detected, self.write_log)

                if self.monitor.start():
                    # UIの更新はメインスレッドで
                    self.root.after(0, self._on_monitoring_started)
            except Exception as e:
                self.root.after(0, lambda err=e: messagebox.showerror("エラー", f"監視開始に失敗: {err}"))

        thread = threading.Thread(target=do_start, daemon=True)
        thread.start()

    def _on_monitoring_started(self):
        """監視開始完了時のUI更新"""
        self.monitoring_enabled.set(True)
        self.update_monitoring_status()
        if hasattr(self, 'monitor_btn') and self.monitor_btn:
            self.monitor_btn.config(text="監視停止")
        self.write_log(f"監視開始: {self.DOWNLOADS_FOLDER}")
        # 通知も非ブロッキングで
        threading.Thread(target=lambda: self.show_notification("監視開始", "ダウンロードフォルダの監視を開始しました"), daemon=True).start()

    def stop_monitoring(self):
        """ファイル監視を停止"""
        if self.monitor:
            self.monitor.stop()
        self.monitoring_enabled.set(False)
        self.update_monitoring_status()
        self.write_log("監視停止")

    def update_monitoring_status(self):
        """監視状態の表示を更新"""
        if hasattr(self, 'monitor_status_label') and self.monitor_status_label:
            if self.monitoring_enabled.get():
                self.monitor_status_label.config(text="監視中 🟢", foreground='green')
            else:
                self.monitor_status_label.config(text="監視停止 🔴", foreground='red')

    def on_new_file_detected(self, file_path):
        """新規ファイル検出時のコールバック"""
        # Redmineからのファイルかチェック
        is_redmine, info = self.is_redmine_file(file_path)
        if not is_redmine:
            return

        filename = os.path.basename(file_path)
        issue_number = info.get('issue_number') if info else None

        # ログ記録
        self.write_log(f"Redmineファイル検出: {filename} (チケット: #{issue_number if issue_number else '不明'})")

        # 通知
        self.show_notification(
            "Redmineファイル検出",
            f"{filename[:40]}...\nチケット: #{issue_number if issue_number else '不明'}"
        )

        # GUIを更新（ウィンドウが存在する場合のみ）
        if self.root:
            try:
                self.root.after(0, self.scan_and_display)
            except Exception:
                pass

        # 自動整理が有効で、ログイン済みで、チケット番号がある場合は自動処理
        # ウィンドウが閉じていても動作するようにthreading.Timerを使用
        if (self.auto_organize_enabled and self.auto_organize_enabled.get() and
            self.redmine_client.logged_in and
            issue_number):
            self.write_log(f"自動整理開始: {filename}")
            threading.Timer(1.0, lambda: self.auto_process_file(file_path, info)).start()

    def auto_process_file(self, file_path, info):
        """ファイルを自動処理（ウィンドウが閉じていても動作）"""
        if not os.path.exists(file_path):
            self.write_log(f"自動整理失敗: ファイルが存在しません - {file_path}")
            return

        issue_number = info.get('issue_number')
        if not issue_number:
            self.write_log(f"自動整理失敗: チケット番号なし - {file_path}")
            return

        filename = os.path.basename(file_path)

        def do_process():
            # タイトル取得
            title, error = self.redmine_client.get_issue_title(issue_number)
            if not title:
                self.write_log(f"自動整理失敗: タイトル取得失敗 - #{issue_number}: {error}")
                self.show_notification("自動整理失敗", f"タイトル取得失敗: {error}")
                return

            self.write_log(f"チケットタイトル取得: #{issue_number} - {title}")

            # パース
            parsed = self.parse_ticket_title(title)
            if not parsed:
                self.write_log(f"自動整理失敗: タイトル形式不正 - {title}")
                self.show_notification("自動整理失敗", f"タイトル形式が認識できません")
                return

            # 移動先パス構築（日付フォルダ付き）
            target_folder = self.build_target_path(parsed, file_path)
            if not target_folder:
                self.write_log(f"自動整理失敗: パス構築失敗")
                return

            # ファイル移動
            success, result = self.move_file(file_path, target_folder)
            if success:
                self.write_log(f"ファイル移動成功: {filename} → {target_folder}")
                self._on_auto_process_complete(result, target_folder)
            else:
                self.write_log(f"自動整理失敗: ファイル移動失敗 - {result}")
                self.show_notification("自動整理失敗", f"ファイル移動失敗")

        thread = threading.Thread(target=do_process, daemon=True)
        thread.start()

    def _on_auto_process_complete(self, result, target_folder):
        """自動処理完了時（ウィンドウが閉じていても動作）"""
        filename = os.path.basename(result)
        self.show_notification("自動整理完了", f"{filename[:30]}...")
        self.last_target_folder = target_folder

        # GUIを更新（ウィンドウが存在する場合のみ）
        if self.root:
            try:
                self.root.after(0, self.scan_and_display)
            except Exception:
                pass

        # 通知表示して3秒後にフォルダを開く
        self.show_move_notification(True, filename, target_folder)

    def show_notification(self, title, message):
        """デスクトップ通知を表示（pystrayのnotify使用）"""
        try:
            if self.tray_icon:
                self.tray_icon.notify(message, title)
        except Exception:
            pass  # 通知に失敗しても無視

    def quit_app(self, icon=None, item=None):
        """アプリケーションを終了"""
        # 監視停止
        if self.monitor:
            self.monitor.stop()
        # トレイアイコン停止
        if self.tray_icon:
            self.tray_icon.stop()
        # GUI終了
        if self.root:
            self.root.after(0, self.root.destroy)

    def on_closing(self):
        """ウィンドウを閉じる時の処理（トレイに最小化）"""
        if TRAY_AVAILABLE and self.tray_icon:
            self.hide_to_tray()
        else:
            self.quit_app()

    # ========== GUI部分 ==========

    def create_gui(self):
        """GUIを作成"""
        self.root = tk.Tk()
        self.root.title("Redmine ファイル整理ツール（常駐版）")
        self.root.geometry("800x750")
        self.root.configure(bg='#f0f0f0')

        # BooleanVarをここで初期化
        self.auto_organize_enabled = tk.BooleanVar(value=True)
        self.monitoring_enabled = tk.BooleanVar(value=False)

        # ウィンドウを閉じる時の処理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # スタイル設定
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Meiryo UI', 14, 'bold'))
        style.configure('Info.TLabel', font=('Meiryo UI', 10))
        style.configure('Status.TLabel', font=('Meiryo UI', 9))
        style.configure('Big.TButton', font=('Meiryo UI', 11), padding=10)
        style.configure('Auto.TButton', font=('Meiryo UI', 12, 'bold'), padding=15)
        style.configure('Monitor.TLabel', font=('Meiryo UI', 10, 'bold'))

        # メインフレーム
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 通知フレーム（画面上部に表示、初期状態では非表示）
        self.notification_frame = tk.Frame(main_frame, bg='#4CAF50', pady=10)
        self.notification_label = tk.Label(self.notification_frame, text="",
                                           font=('Meiryo UI', 11, 'bold'),
                                           bg='#4CAF50', fg='white',
                                           wraplength=700, justify=tk.LEFT)
        self.notification_label.pack(padx=10)
        # 初期状態では非表示
        # self.notification_frame.pack() は show_move_notification で呼ぶ

        # タイトルとステータス
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = ttk.Label(header_frame, text="Redmine ダウンロードファイル整理ツール",
                                style='Title.TLabel')
        title_label.pack(side=tk.LEFT)

        # 監視状態表示
        self.monitor_status_label = ttk.Label(header_frame, text="監視停止 🔴",
                                               style='Monitor.TLabel', foreground='red')
        self.monitor_status_label.pack(side=tk.RIGHT, padx=(10, 0))

        self.status_label = ttk.Label(header_frame, text="未ログイン",
                                       style='Status.TLabel', foreground='gray')
        self.status_label.pack(side=tk.RIGHT)

        # ========== 監視設定セクション ==========
        monitor_frame = ttk.LabelFrame(main_frame, text="常駐監視設定", padding=10)
        monitor_frame.pack(fill=tk.X, pady=(0, 10))

        monitor_row = ttk.Frame(monitor_frame)
        monitor_row.pack(fill=tk.X)

        self.monitor_btn = ttk.Button(monitor_row, text="監視開始",
                                       command=self.toggle_monitoring, style='Big.TButton')
        self.monitor_btn.pack(side=tk.LEFT, padx=(0, 10))

        auto_check = ttk.Checkbutton(monitor_row, text="自動整理（ログイン時のみ有効）",
                                      variable=self.auto_organize_enabled)
        auto_check.pack(side=tk.LEFT, padx=(10, 0))

        ttk.Label(monitor_row, text="※ウィンドウを閉じてもトレイに常駐します",
                  style='Info.TLabel', foreground='gray').pack(side=tk.RIGHT)

        # ========== 自動整理セクション ==========
        auto_frame = ttk.LabelFrame(main_frame, text="ワンクリック自動整理", padding=10)
        auto_frame.pack(fill=tk.X, pady=(0, 10))

        auto_btn_frame = ttk.Frame(auto_frame)
        auto_btn_frame.pack(fill=tk.X)

        self.auto_btn = ttk.Button(auto_btn_frame, text="選択ファイルを自動整理",
                                    command=self.auto_organize_selected, style='Auto.TButton',
                                    state=tk.DISABLED)
        self.auto_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.auto_all_btn = ttk.Button(auto_btn_frame, text="全ファイル一括整理",
                                        command=self.auto_organize_all, style='Big.TButton',
                                        state=tk.DISABLED)
        self.auto_all_btn.pack(side=tk.LEFT)

        self.progress_label = ttk.Label(auto_frame, text="", style='Info.TLabel')
        self.progress_label.pack(anchor=tk.W, pady=(10, 0))

        # ファイルリストセクション
        list_frame = ttk.LabelFrame(main_frame, text="検出されたRedmineファイル", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # スキャンボタン
        btn_row = ttk.Frame(list_frame)
        btn_row.pack(fill=tk.X, pady=(0, 10))

        scan_btn = ttk.Button(btn_row, text="再スキャン",
                              command=self.scan_and_display)
        scan_btn.pack(side=tk.LEFT)

        login_btn = ttk.Button(btn_row, text="Redmineにログイン",
                               command=self.show_login_dialog)
        login_btn.pack(side=tk.RIGHT)

        # ファイルリスト
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.files_listbox = tk.Listbox(list_container, font=('Meiryo UI', 10),
                                         yscrollcommand=scrollbar.set, height=8)
        self.files_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.files_listbox.yview)

        self.files_listbox.bind('<<ListboxSelect>>', self.on_file_select)
        self.files_listbox.bind('<Double-Button-1>', lambda e: self.auto_organize_selected())

        # ファイル情報表示
        self.file_info_label = ttk.Label(list_frame, text="", style='Info.TLabel')
        self.file_info_label.pack(pady=(10, 0))

        # チケットタイトル入力セクション（手動用）
        title_frame = ttk.LabelFrame(main_frame, text="手動入力（自動取得できない場合）", padding=10)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        # 自動取得ボタンと手動入力の説明
        auto_frame2 = ttk.Frame(title_frame)
        auto_frame2.pack(fill=tk.X, pady=(0, 5))

        self.auto_fetch_btn = ttk.Button(auto_frame2, text="タイトル取得",
                                          command=self.fetch_title_async, state=tk.DISABLED)
        self.auto_fetch_btn.pack(side=tk.LEFT)

        self.open_redmine_btn = ttk.Button(auto_frame2, text="ブラウザで開く",
                                           command=self.open_redmine_ticket, state=tk.DISABLED)
        self.open_redmine_btn.pack(side=tk.LEFT, padx=(10, 0))

        # タイトル入力欄
        self.title_entry = ttk.Entry(title_frame, font=('Meiryo UI', 11))
        self.title_entry.pack(fill=tk.X, pady=(5, 0))
        self.title_entry.bind('<KeyRelease>', self.update_preview)

        # プレビューセクション
        preview_frame = ttk.LabelFrame(main_frame, text="移動先プレビュー", padding=10)
        preview_frame.pack(fill=tk.X, pady=(0, 10))

        self.preview_label = ttk.Label(preview_frame, text="ファイルを選択してください",
                                        style='Info.TLabel', wraplength=750)
        self.preview_label.pack(anchor=tk.W)

        # 実行ボタン
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        self.execute_btn = ttk.Button(btn_frame, text="手動で移動",
                                       command=self.execute_move,
                                       state=tk.DISABLED)
        self.execute_btn.pack(side=tk.LEFT, padx=(0, 10))

        open_folder_btn = ttk.Button(btn_frame, text="出力フォルダを開く",
                                     command=self.open_preview_folder)
        open_folder_btn.pack(side=tk.LEFT)

        # 初回スキャン
        self.root.after(500, self.scan_and_display)

    def show_login_dialog(self):
        """ログインダイアログを表示"""
        if not requests:
            messagebox.showerror("エラー",
                "requestsライブラリがインストールされていません。\n"
                "pip install requests を実行してください。")
            return

        # 保存済みのログイン情報を読み込んでダイアログにセット
        saved_username, saved_password = self.load_credentials()
        dialog = LoginDialog(self.root,
                            initial_username=saved_username or "",
                            initial_password=saved_password or "")
        self.root.wait_window(dialog)

        if dialog.result:
            username, password = dialog.result
            self.status_label.config(text="ログイン中...", foreground='orange')
            self.root.update()

            # ログイン実行（別スレッドで）
            def do_login():
                success, message = self.redmine_client.login(username, password)
                # ログイン成功時にユーザー名とパスワードを渡す
                self.root.after(0, lambda: self.on_login_complete(success, message, username, password))

            thread = threading.Thread(target=do_login)
            thread.start()

    def on_login_complete(self, success, message, username=None, password=None):
        """ログイン完了時のコールバック"""
        if success:
            self.status_label.config(
                text=f"ログイン中: {self.redmine_client.username}",
                foreground='green'
            )
            # ログイン情報を保存（常に最新の認証情報で更新）
            if username and password:
                self.save_credentials(username, password)
                self.write_log(f"ログイン情報を更新しました: {username}")
            messagebox.showinfo("ログイン成功", "Redmineにログインしました。\n自動整理機能が使えます。\n\n※ログイン情報を保存しました。次回から自動ログインします。")
            # 自動整理ボタンを有効化
            self.update_auto_buttons()
        else:
            self.status_label.config(text="未ログイン", foreground='gray')
            messagebox.showerror("ログイン失敗", message)

    def update_auto_buttons(self):
        """自動整理ボタンの有効/無効を更新"""
        if self.redmine_client.logged_in:
            # 選択ファイルがあってチケット番号がある場合
            if self.selected_file and self.selected_file['info'].get('issue_number'):
                self.auto_btn.config(state=tk.NORMAL)
                self.auto_fetch_btn.config(state=tk.NORMAL)
            else:
                self.auto_btn.config(state=tk.DISABLED)
                self.auto_fetch_btn.config(state=tk.DISABLED)

            # チケット番号があるファイルが1つ以上あれば全ファイル整理を有効化
            has_valid_files = any(f['info'].get('issue_number') for f in self.detected_files)
            if has_valid_files:
                self.auto_all_btn.config(state=tk.NORMAL)
            else:
                self.auto_all_btn.config(state=tk.DISABLED)
        else:
            self.auto_btn.config(state=tk.DISABLED)
            self.auto_all_btn.config(state=tk.DISABLED)
            self.auto_fetch_btn.config(state=tk.DISABLED)

    def auto_organize_selected(self):
        """選択ファイルを自動整理"""
        if not self.selected_file:
            messagebox.showwarning("エラー", "ファイルを選択してください")
            return

        if not self.redmine_client.logged_in:
            messagebox.showwarning("ログイン必要", "先にRedmineにログインしてください")
            self.show_login_dialog()
            return

        issue_number = self.selected_file['info'].get('issue_number')
        if not issue_number:
            messagebox.showwarning("エラー", "このファイルはチケット番号が不明です。\n手動でタイトルを入力してください。")
            return

        # 処理開始
        self.progress_label.config(text=f"処理中: {self.selected_file['filename'][:50]}...")
        self.auto_btn.config(state=tk.DISABLED)
        self.root.update()

        def do_organize():
            # タイトル取得
            title, error = self.redmine_client.get_issue_title(issue_number)
            if not title:
                self.root.after(0, lambda: self.on_auto_organize_error(error or "タイトル取得失敗"))
                return

            # パース
            parsed = self.parse_ticket_title(title)
            if not parsed:
                self.root.after(0, lambda: self.on_auto_organize_error(
                    f"タイトル形式が認識できません:\n{title}"))
                return

            # 移動先パス構築（日付フォルダ付き）
            target_folder = self.build_target_path(parsed, self.selected_file['path'])
            if not target_folder:
                self.root.after(0, lambda: self.on_auto_organize_error("移動先パス構築失敗"))
                return

            # ファイル移動
            success, result = self.move_file(self.selected_file['path'], target_folder)
            self.root.after(0, lambda: self.on_auto_organize_complete(success, result, title))

        thread = threading.Thread(target=do_organize)
        thread.start()

    def on_auto_organize_error(self, error):
        """自動整理エラー時のコールバック"""
        self.progress_label.config(text="")
        self.update_auto_buttons()
        messagebox.showerror("自動整理エラー", error)

    def on_auto_organize_complete(self, success, result, title):
        """自動整理完了時のコールバック"""
        if success:
            filename = os.path.basename(result)
            self.progress_label.config(text=f"完了: {filename}")
            # 移動先フォルダを保存（「出力フォルダを開く」ボタン用）
            self.last_target_folder = os.path.dirname(result)
            # リストを更新（移動したファイルが消える）
            self.scan_and_display()
            self.title_entry.delete(0, tk.END)
            self.selected_file = None
            self.file_info_label.config(text="")
            self.preview_label.config(text="ファイルを選択してください")
            self.update_auto_buttons()
            # 通知表示して3秒後にフォルダを開く
            self.show_move_notification(True, filename, self.last_target_folder)
        else:
            self.progress_label.config(text="")
            self.update_auto_buttons()
            self.show_move_notification(False, result, "")
            messagebox.showerror("移動エラー", f"ファイル移動に失敗:\n{result}")

    def auto_organize_all(self):
        """全ファイル一括整理"""
        if not self.redmine_client.logged_in:
            messagebox.showwarning("ログイン必要", "先にRedmineにログインしてください")
            self.show_login_dialog()
            return

        # チケット番号があるファイルのみ対象
        valid_files = [f for f in self.detected_files if f['info'].get('issue_number')]

        if not valid_files:
            messagebox.showinfo("情報", "整理可能なファイルがありません")
            return

        confirm = messagebox.askyesno(
            "一括整理確認",
            f"{len(valid_files)}件のファイルを自動整理します。\n\n"
            "チケット番号が不明なファイルはスキップされます。\n\n"
            "続行しますか？"
        )

        if not confirm:
            return

        # 処理開始
        self.auto_processing = True
        self.auto_btn.config(state=tk.DISABLED)
        self.auto_all_btn.config(state=tk.DISABLED)

        def do_organize_all():
            success_count = 0
            error_count = 0
            skip_count = 0
            last_folder = None  # 最後に成功したフォルダを追跡

            for i, file_info in enumerate(valid_files):
                if not self.auto_processing:
                    break

                filename = file_info['filename']
                issue_number = file_info['info'].get('issue_number')

                self.root.after(0, lambda fn=filename, idx=i:
                    self.progress_label.config(text=f"処理中 ({idx+1}/{len(valid_files)}): {fn[:40]}..."))

                # タイトル取得
                title, error = self.redmine_client.get_issue_title(issue_number)
                if not title:
                    error_count += 1
                    continue

                # パース
                parsed = self.parse_ticket_title(title)
                if not parsed:
                    skip_count += 1
                    continue

                # 移動先パス構築（日付フォルダ付き）
                target_folder = self.build_target_path(parsed, file_info['path'])
                if not target_folder:
                    error_count += 1
                    continue

                # ファイル移動
                success, result = self.move_file(file_info['path'], target_folder)
                if success:
                    success_count += 1
                    last_folder = target_folder  # 最後に成功したフォルダを記録
                else:
                    error_count += 1

                # 少し待機（サーバー負荷軽減）
                time.sleep(0.5)

            self.root.after(0, lambda: self.on_auto_organize_all_complete(
                success_count, error_count, skip_count, last_folder))

        thread = threading.Thread(target=do_organize_all)
        thread.start()

    def on_auto_organize_all_complete(self, success_count, error_count, skip_count, last_folder=None):
        """全ファイル整理完了時のコールバック"""
        self.auto_processing = False
        self.progress_label.config(text=f"完了: 成功 {success_count}件, エラー {error_count}件, スキップ {skip_count}件")
        # 最後に成功したフォルダを保存（「出力フォルダを開く」ボタン用）
        if last_folder:
            self.last_target_folder = last_folder

        # リスト更新
        self.scan_and_display()
        self.update_auto_buttons()

        # 移動先フォルダを自動で開く（成功した場合のみ）
        if last_folder and success_count > 0:
            self.open_folder_safe(last_folder)

        messagebox.showinfo("一括整理完了",
            f"処理が完了しました。\n\n"
            f"成功: {success_count}件\n"
            f"エラー: {error_count}件\n"
            f"スキップ: {skip_count}件")

    def fetch_title_async(self):
        """チケットタイトルを非同期で取得"""
        if not self.selected_file:
            return

        issue_number = self.selected_file['info'].get('issue_number')
        if not issue_number:
            messagebox.showwarning("エラー", "チケット番号が不明です")
            return

        if not self.redmine_client.logged_in:
            messagebox.showwarning("ログイン必要", "先にRedmineにログインしてください")
            self.show_login_dialog()
            return

        # 取得中の表示
        self.auto_fetch_btn.config(state=tk.DISABLED)
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, "取得中...")
        self.root.update()

        def do_fetch():
            title, error = self.redmine_client.get_issue_title(issue_number)
            self.root.after(0, lambda: self.on_fetch_complete(title, error))

        thread = threading.Thread(target=do_fetch)
        thread.start()

    def on_fetch_complete(self, title, error):
        """タイトル取得完了時のコールバック"""
        self.auto_fetch_btn.config(state=tk.NORMAL)
        self.title_entry.delete(0, tk.END)

        if title:
            self.title_entry.insert(0, title)
            self.update_preview()
        else:
            messagebox.showerror("取得エラー", error or "タイトルを取得できませんでした")

    def scan_and_display(self):
        """スキャンして結果を表示（非ブロッキング）"""
        self.files_listbox.delete(0, tk.END)
        self.files_listbox.insert(tk.END, "(スキャン中...)")

        def do_scan():
            files = self.scan_downloads_folder()
            self.root.after(0, lambda: self._update_file_list(files))

        thread = threading.Thread(target=do_scan, daemon=True)
        thread.start()

    def _update_file_list(self, files):
        """ファイルリストを更新（メインスレッド）"""
        self.files_listbox.delete(0, tk.END)
        self.detected_files = files

        if not self.detected_files:
            self.files_listbox.insert(tk.END, "(Redmineからのファイルは見つかりませんでした)")
            self.update_auto_buttons()
            return

        for file_info in self.detected_files:
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(file_info['path']))
                issue_num = file_info['info'].get('issue_number')
                prefix = f"[#{issue_num}] " if issue_num else "[?] "
                display = f"{prefix}{file_info['filename']} ({mtime.strftime('%m/%d %H:%M')})"
                self.files_listbox.insert(tk.END, display)
            except:
                pass

        self.update_auto_buttons()

    def on_file_select(self, event):
        """ファイル選択時の処理"""
        selection = self.files_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        if index >= len(self.detected_files):
            return

        self.selected_file = self.detected_files[index]
        info = self.selected_file['info']

        # ファイル情報を表示
        issue_num = info.get('issue_number')
        attach_id = info.get('attachment_id')
        info_text = f"チケット番号: #{issue_num if issue_num else '不明'} | "
        info_text += f"添付ID: {attach_id if attach_id else '不明'}"
        self.file_info_label.config(text=info_text)

        # ボタンの有効/無効を設定
        if issue_num:
            self.open_redmine_btn.config(state=tk.NORMAL)
        else:
            self.open_redmine_btn.config(state=tk.DISABLED)

        self.update_auto_buttons()
        self.update_preview()

    def open_redmine_ticket(self):
        """Redmineチケットをブラウザで開く"""
        if not self.selected_file:
            return

        issue_number = self.selected_file['info'].get('issue_number')
        if issue_number:
            url = f"https://{self.REDMINE_HOST}/issues/{issue_number}"
            webbrowser.open(url)

    def update_preview(self, event=None):
        """プレビューを更新"""
        title = self.title_entry.get().strip()

        if not title or title == "取得中...":
            self.preview_label.config(text="チケットタイトルを入力または自動取得してください")
            self.execute_btn.config(state=tk.DISABLED)
            return

        parsed = self.parse_ticket_title(title)
        if not parsed:
            self.preview_label.config(text="タイトル形式が認識できません。[xxx][xxx]形式で入力してください。")
            self.execute_btn.config(state=tk.DISABLED)
            return

        # 選択ファイルのパスを渡して日付フォルダを含める
        file_path = self.selected_file['path'] if self.selected_file else None
        target_path = self.build_target_path(parsed, file_path)
        if not target_path:
            self.preview_label.config(text="パスの構築に失敗しました")
            self.execute_btn.config(state=tk.DISABLED)
            return

        preview_text = f"移動先: {target_path}"
        self.preview_label.config(text=preview_text)

        if self.selected_file:
            self.execute_btn.config(state=tk.NORMAL)

    def execute_move(self):
        """ファイル移動を実行（手動）"""
        if not self.selected_file:
            messagebox.showerror("エラー", "ファイルを選択してください")
            return

        title = self.title_entry.get().strip()
        parsed = self.parse_ticket_title(title)
        target_folder = self.build_target_path(parsed, self.selected_file['path'])

        if not target_folder:
            messagebox.showerror("エラー", "移動先の構築に失敗しました")
            return

        # 確認ダイアログ
        confirm = messagebox.askyesno(
            "確認",
            f"以下のファイルを移動しますか？\n\n"
            f"元: {self.selected_file['filename']}\n\n"
            f"先: {target_folder}"
        )

        if not confirm:
            return

        success, result = self.move_file(self.selected_file['path'], target_folder)

        if success:
            messagebox.showinfo("完了", f"ファイルを移動しました")
            # 移動先フォルダを保存（「出力フォルダを開く」ボタン用）
            self.last_target_folder = target_folder
            # リストを更新
            self.scan_and_display()
            self.title_entry.delete(0, tk.END)
            self.selected_file = None
            self.file_info_label.config(text="")
            self.preview_label.config(text="ファイルを選択してください")
            self.execute_btn.config(state=tk.DISABLED)
            self.update_auto_buttons()
            # 移動先フォルダを自動で開く
            self.open_folder_safe(self.last_target_folder)
        else:
            messagebox.showerror("エラー", f"移動に失敗しました:\n{result}")


def main(start_minimized=True):
    """メイン関数

    Args:
        start_minimized: True の場合、トレイに最小化して起動
    """
    try:
        organizer = RedmineFileOrganizer()

        # GUIを作成
        organizer.create_gui()

        # システムトレイアイコンを作成・起動
        if TRAY_AVAILABLE:
            organizer.tray_icon = organizer.create_tray_icon()
            if organizer.tray_icon:
                # トレイアイコンを別スレッドで実行
                tray_thread = threading.Thread(target=organizer.tray_icon.run, daemon=True)
                tray_thread.start()

                # 最小化して起動（トレイに常駐）
                if start_minimized:
                    organizer.root.withdraw()  # ウィンドウを非表示
                    # 起動通知（少し遅延させる）
                    organizer.root.after(2000, lambda: organizer.show_notification("Redmine ファイル整理", "トレイに常駐しています"))

        # 自動で監視を開始
        if WATCHDOG_AVAILABLE:
            organizer.root.after(1000, organizer.start_monitoring)

        # 保存されたログイン情報で自動ログイン
        organizer.root.after(1500, organizer.auto_login)

        # メインループ
        organizer.root.mainloop()

    except Exception as e:
        # エラーが発生した場合はメッセージボックスを表示して終了
        try:
            messagebox.showerror("起動エラー", f"アプリケーションの起動に失敗しました:\n{e}")
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    # コマンドライン引数で --show を指定するとウィンドウ表示で起動
    show_window = "--show" in sys.argv
    main(start_minimized=not show_window)

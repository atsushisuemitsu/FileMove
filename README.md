# FileMove

Windows 11 用のファイル監視・整理アプリケーション

## 機能

### 機能A: ファイル監視 + フォルダ移動
- 指定フォルダを監視し、新しいファイル（コピー、ダウンロード、作成）を検出
- フォルダ選択UIで移動先を選択
- サブフォルダのナビゲーション、新規フォルダ作成に対応

### 機能B: スクリプト生成
- OpenRouter API を使用してプロンプトから Python スクリプトを生成
- プロンプトの作成・編集・管理
- 生成したスクリプトの手動実行

## インストール

```bash
git clone https://github.com/yourusername/FileMove.git
cd FileMove
pip install -r requirements.txt
```

## 使い方

### 起動
```bash
python main.py
```

### 初期設定
1. システムトレイアイコンを右クリック → 「設定」
2. **API設定**: OpenRouter API Key とモデル名を設定
3. **フォルダ設定**: 監視フォルダと移動先フォルダを設定

### トレイメニュー
- **監視開始/停止**: ファイル監視のON/OFF
- **設定**: 設定画面を開く
- **プロンプト管理**: プロンプトの作成・編集
- **スクリプト実行**: スクリプトの生成・実行
- **終了**: アプリを終了

## 技術スタック

- **UI**: CustomTkinter
- **ファイル監視**: watchdog
- **システムトレイ**: pystray + Pillow
- **API**: httpx (OpenRouter)

## ファイル構成

```
FileMove/
├── main.py                 # エントリーポイント
├── config.json             # 設定ファイル
├── requirements.txt        # 依存関係
├── prompts/                # プロンプト保存
├── generated_scripts/      # 生成されたスクリプト
└── src/
    ├── __init__.py
    ├── app.py              # メインアプリケーション
    ├── file_watcher.py     # ファイル監視
    ├── api_client.py       # OpenRouter API
    ├── folder_selector.py  # フォルダ選択UI
    ├── prompt_manager.py   # プロンプト管理
    ├── script_executor.py  # スクリプト生成・実行
    ├── settings_window.py  # 設定画面
    └── tray_icon.py        # システムトレイ
```

## 依存関係

- customtkinter >= 5.2.0
- watchdog >= 3.0.0
- pystray >= 0.19.0
- Pillow >= 10.0.0
- httpx >= 0.25.0

---

## Redmine ファイル整理ツール

Redmine チケット情報に基づいてダウンロードファイルを自動整理するツール

### 機能
- ダウンロードフォルダの監視
- Redmine API でチケット情報を取得
- チケット番号に基づくフォルダ整理
- システムトレイ常駐

### EXE ビルド
```bash
build.bat
# または
python build_exe.py
```

### 変更履歴

#### 2024-12-17 (v5)
- **機能追加**: 移動先に日付フォルダを追加
  - 移動先パスに `YYYYMMDD` 形式の日付フォルダを追加
  - 例: `D:\@USER\Folder1\Folder2\Folder3\20241217`
  - ダウンロード日（ファイル更新日時）を使用

#### 2024-12-17 (v4)
- **機能追加**: ログ機能と自動移動の改善
  - ファイル移動ログを `~/RedmineFileOrganizer_log.txt` に出力
  - ウィンドウを閉じても自動移動が動作するように改善
  - 移動完了後に移動先フォルダを自動で開く
  - threading.Timerを使用してGUI非依存の処理に改善

#### 2024-12-17 (v3)
- **修正**: ウィンドウ表示時のフリーズ問題を解決
  - subprocess.runにタイムアウト（5秒）を追加
  - scan_and_displayを非ブロッキング化（バックグラウンドスレッドで実行）
  - TimeoutExpired例外ハンドリングを追加

#### 2024-12-17 (v2)
- **修正**: EXE実行時のコンソールウィンドウ問題を完全解決
  - subprocess呼び出しにCREATE_NO_WINDOWフラグを追加
  - PowerShell実行時のコンソールウィンドウを非表示化
  - 残りのprint文を全て削除

#### 2024-12-17 (v1)
- **修正**: EXE実行時の無限ループ問題を解決
  - plyer通知ライブラリを削除（EXE環境で不安定）
  - pystray.notify() による通知に変更
  - print文を削除（コンソールウィンドウ問題を防止）
  - 例外ハンドリングを追加

## ライセンス

MIT

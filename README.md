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

## ライセンス

MIT

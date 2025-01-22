# AI Desktop Agent

デスクトップとブラウザの操作を自動化するAIエージェントです。

## 機能

- デスクトップ操作の自動化
  - マウス・キーボード制御
  - ウィンドウ管理
  - スクリーンショット
  - システムメトリクス取得

- ブラウザ操作の自動化
  - Edge/Chromeブラウザの制御
  - ドキュメント検索
  - コードスニペット抽出
  - APIリファレンス検索
  - 検索履歴管理

- タスク管理
  - タスクの作成・更新・削除
  - 優先度・ステータス管理
  - タスク実行結果の追跡

## 必要要件

- Python 3.8以上
- Edge WebDriver または Chrome WebDriver
- 必要なPythonパッケージ:
  ```
  selenium
  webdriver-manager
  pyautogui
  keyboard
  mouse
  psutil
  pywin32
  PyQt6
  ```

## インストール

1. リポジトリをクローン:
```bash
git clone https://github.com/yourusername/ai-desktop-agent.git
cd ai-desktop-agent
```

2. 仮想環境を作成して有効化:
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. 依存パッケージをインストール:
```bash
pip install -r requirements.txt
```

4. 環境変数の設定:
```bash
cp .env.example .env
# .envファイルを編集してAPIキーなどを設定
```

## ブラウザの設定

使用するブラウザは環境変数で指定できます：

```bash
# .envファイル
BROWSER_TYPE=edge  # または "chrome"
BROWSER_HEADLESS=true  # ヘッドレスモードの有効/無効
BROWSER_TIMEOUT=10  # タイムアウト時間（秒）
```

## 使用方法

1. アプリケーションを起動:
```bash
python -m ai_orchestration
```

2. GUIが起動し、以下の操作が可能になります:
   - タスクの作成・管理
   - デスクトップ操作の自動化
   - ブラウザ操作の自動化

## テスト実行

1. 単体テストの実行:
```bash
pytest
```

2. カバレッジレポートの生成:
```bash
pytest --cov=ai_orchestration --cov-report=html
```

3. 特定のブラウザのテストのみ実行:
```bash
pytest ai_orchestration/tests/test_browser_controller.py -k "chrome"
pytest ai_orchestration/tests/test_browser_controller.py -k "edge"
```

## プロジェクト構成

```
ai_orchestration/
├── __init__.py
├── __main__.py
├── config/
│   ├── __init__.py
│   └── config.py
├── core/
│   ├── __init__.py
│   ├── desktop_controller.py
│   ├── browser_controller.py
│   └── task_manager.py
├── gui/
│   ├── __init__.py
│   └── main_window.py
├── models/
│   ├── __init__.py
│   └── task.py
├── tests/
│   ├── __init__.py
│   ├── test_browser_controller.py
│   ├── test_desktop_controller.py
│   └── test_task_manager.py
└── utils/
    ├── __init__.py
    └── error_handler.py
```

## エラーハンドリング

アプリケーションは以下のエラーハンドリング機能を提供します：

- カスタムエラークラス
- エラーログの自動記録
- リトライメカニズム
- 入力バリデーション
- 安全な操作のためのデコレータ

## ライセンス

MITライセンス

## 作者

Your Name 
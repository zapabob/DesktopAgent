# デスクトップエージェント

デスクトップエージェントは、自然言語でコンピュータを操作できるPythonアプリケーションです。コマンドの実行、システムモニタリング、ポモドーロタイマーなどの機能を提供します。

## 主な機能

- 自然言語によるコマンド実行
- システムリソースのモニタリング（CPU、GPU、メモリ使用率）
- ポモドーロタイマー
- タスク管理
- システムトレイ常駐
- コマンド履歴の記録

## 必要条件

- Python 3.8以上
- Windows 10/11
- Google AI (Gemini Pro) APIキー

## インストール方法

1. リポジトリをクローン：
```bash
git clone https://github.com/yourusername/DesktopAgent.git
cd DesktopAgent
```

2. 仮想環境を作成して有効化：
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
```

3. 必要なパッケージをインストール：
```bash
pip install -r requirements.txt
```

4. 環境変数の設定：
`.env`ファイルを作成し、以下の内容を設定：
```
GOOGLE_API_KEY=your_api_key_here
```

## 使用方法

1. アプリケーションを起動：
```bash
python DesktopAgent/src/main.py
```

2. コマンド入力欄に自然言語でコマンドを入力（例：「ブラウザでGoogleを開いて」）

3. システムトレイアイコンから各種機能にアクセス可能

## 利用可能なコマンド

- ブラウザ操作（Edge, Chrome, デフォルトブラウザ）
- ファイル操作（作成、移動、削除）
- ウィンドウ操作（最小化）
- アプリケーション起動
- マウス・キーボード操作
- 画面分析

## 開発者向け情報

プロジェクト構造：
```
DesktopAgent/
├── src/
│   ├── agent/
│   │   ├── autonomous_agent.py
│   │   ├── command_interpreter.py
│   │   └── keyboard_monitor.py
│   ├── db/
│   │   └── models.py
│   ├── gui/
│   │   └── main_window.py
│   └── main.py
├── requirements.txt
└── README.md
```

## ライセンス

MITライセンス

## 注意事項

- システム操作を行うため、管理者権限が必要な場合があります
- APIキーは適切に管理してください
- キーボード・マウス操作の自動化は慎重に行ってください

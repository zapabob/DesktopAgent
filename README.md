# デスクトップエージェント

<<<<<<< HEAD
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
=======
マルチモーダルな自律型AIエージェントシステム。複数のAIエージェントが協調して動作し、デスクトップ操作の自動化と支援を行います。

## Features
- Autonomous Agent Management
- Real-time System Monitoring
- Cross-platform GUI Interface

## 主な機能

### マルチエージェントシステム
- 複数の子エージェントによる並行処理
- エージェント間の自律的な通信と協調
- リソース使用の最適化と負荷分散

### 学習機能
- Transformerベースの行動学習
- マウス操作とボタン入力の予測
- RAGによるコンテキスト理解

### AIモデル統合
- Google AI Studio（デフォルト）
- OpenAI（オプション）
- Anthropic（オプション）
- 自動フォールバックとロードバランシング

### データ管理
- SQLiteによる永続化
- セキュアなデータ保存
- 構造化されたログ管理

## 必要要件

- Python 3.10以上
- CUDA対応GPU（推奨）
- 必要なPythonパッケージ:
  - PyQt6
  - torch
  - numpy
  - langchain
  - その他（requirements.txtを参照）

## インストール & クイックスタート

1. リポジトリのクローンと依存関係インストール:
```bash
git clone https://github.com/zapabob/DesktopAgent.git
cd DesktopAgent
python -m pip install -r requirements.txt
```

2. 設定ファイルの作成:
```bash
cp config.example.yaml config.yaml
# 使用するAIプロバイダーのAPIキーを設定
```

3. アプリケーションの実行:
```bash
python src/main.py
```

## 設定

### AIプロバイダーの設定
`config.yaml`で使用するAIプロバイダーを設定できます：

```yaml
ai_providers:
  use_vertexai: true  # Google AI Studio
  use_openai: false   # OpenAI (オプション)
  use_anthropic: false # Anthropic (オプション)
```

### システム設定
```yaml
system_settings:
  cpu_threshold: 80   # CPU使用率の閾値
  memory_threshold: 85 # メモリ使用率の閾値
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
```

## 使用方法

<<<<<<< HEAD
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
=======
1. アプリケーションの起動:
   - `start.bat`をダブルクリック
   - または、コマンドラインで`start.bat`を実行

2. メインウィンドウの操作:
   - エージェントの状態監視
   - タスクの割り当て
   - メトリクスの確認

3. エージェントの管理:
   - 新規エージェントの追加
   - 既存エージェントの一時停止/再開
   - タスクの優先順位付け

## 開発者ガイド

### プロジェクト構造
```
src/
├── DesktopAgent/
│   ├── agent/         # エージェント関連
│   ├── ai/            # AIモデル管理
│   ├── database/      # データベース
│   ├── gui/           # GUI
│   ├── models/        # 機械学習モデル
│   ├── monitoring/    # システム監視
│   └── rag/           # RAG実装
├── main.py            # エントリーポイント
└── config.yaml        # 設定ファイル
```

### 拡張方法
1. 新しいエージェントの追加:
   - `agent/`ディレクトリに新しいエージェントクラスを作成
   - `ChildAgent`クラスを継承

2. 新しいAIモデルの追加:
   - `ai/model_manager.py`にプロバイダーを追加
   - 必要なインターフェースを実装

## ライセンス

Apache2.0 License

## 貢献

1. Forkを作成
2. 機能ブランチを作成
3. 変更をコミット
4. ブランチをPush
5. Pull Requestを作成

## サポート

問題が発生した場合は、以下を確認してください：
1. ログファイル（`logs/`ディレクトリ）
2. システムリソースの使用状況
3. AIプロバイダーの設定

詳細なトラブルシューティングは[Wiki](https://github.com/zapabob/DesktopAgent/wiki)を参照してください。
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809

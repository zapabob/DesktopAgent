# デスクトップエージェント

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
git clone https://github.com/yourusername/desktop-agent.git
cd desktop-agent
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
```

## 使用方法

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

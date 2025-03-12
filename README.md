# デスクトップエージェント

マルチモーダルな自律型AIエージェントシステム。複数のAIエージェントが協調して動作し、デスクトップ操作の自動化と支援を行います。
音声認識とAI駆動のブラウザ制御により、自然な対話を通じてブラウザ操作や様々なタスクの自動化を実現します。

## 主な機能

### 高度なブラウザ操作
- browser-useパッケージによるインテリジェントなウェブ自動化
- 自然言語指示によるウェブサイト操作（「YouTubeで猫の動画を再生して」など）
- 要素の探索とクリック、フォーム入力、スクリーンショット撮影機能
- Playwrightを活用した高レベルなブラウザ制御

### 音声認識と音声コマンド
- 音声コマンドによるブラウザ操作とシステム制御
- Whisperモデルによるローカルでのオフライン音声認識
- GPU加速による高速かつ正確な認識
- 複数言語対応（日本語・英語）

### マルチエージェントシステム
- 複数の子エージェントによる並行処理
- エージェント間の自律的な通信と協調
- リソース使用の最適化と負荷分散

### AIモデル統合
- Google AI Studio（デフォルト）
- OpenAI（オプション）
- Anthropic（オプション）
- 自動フォールバックとロードバランシング

### システム監視と制御
- CPUやGPUの使用率、温度監視
- メモリ使用状況のリアルタイムモニタリング
- システム操作の自動化（音量調整など）
- OpenHardwareMonitorによる詳細な温度監視（オプション）
- リソース使用率の時系列データ収集と分析機能
- 異常値検出と自動アラート通知

### データ管理とUI
- PyQt6ベースのモダンなインターフェース
- タスク管理とポモドーロタイマー
- SQLiteによるデータの永続化
- 構造化されたログ管理

## 必要要件

- Python 3.10以上
- CUDA対応GPU（音声認識と高度な機能に推奨）
- Windows 10/11
- 必要なPythonパッケージ:
  - PyQt6とPyQt6-WebEngine
  - browser-use
  - Playwright
  - Torch (CUDA対応)
  - Transformers
  - その他（requirements.txtを参照）

## インストール & クイックスタート

1. リポジトリのクローンと依存関係インストール:
```bash
git clone https://github.com/zapabob/DesktopAgent.git
cd DesktopAgent
python -m pip install -r requirements.txt
```

2. Playwrightブラウザドライバーのインストール:
```bash
python -m playwright install
```

3. 設定ファイルの作成:
```bash
cp config.example.yaml config.yaml
# 使用するAIプロバイダーのAPIキーを設定
```

4. アプリケーションの実行:
```bash
# Windowsの場合
start.bat

# または
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

### ブラウザ設定
```yaml
browser_paths:
  chrome: "C:/Program Files/Google/Chrome/Application/chrome.exe"
  edge: "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
  firefox: "C:/Program Files/Mozilla Firefox/firefox.exe"
```

### システム設定
```yaml
system_settings:
  cpu_threshold: 80   # CPU使用率の閾値
  memory_threshold: 85 # メモリ使用率の閾値
  voice_recognition:
    enabled: true
    model: "tiny"     # tiny, base, small, medium
    device: "cuda"    # cuda, cpu
```

## 使用方法

### GUI操作
1. アプリケーションの起動:
   - `start.bat`をダブルクリック
   - または、コマンドラインで`start.bat`を実行

2. メインウィンドウの操作:
   - ブラウザ操作タブでウェブ自動化
   - 音声認識ボタンで音声コマンドの開始/停止
   - システムモニタリングとタスク管理

### 音声コマンド例
- 「YouTubeで猫の動画を再生して」
- 「ブラウザでGoogleを開いて」
- 「Gmailを開いて」
- 「音量を上げて」

### ブラウザ操作コマンド例
- 「ブラウザでYahooを開いて」
- 「ブラウザで要素ログインボタンをクリック」
- 「ブラウザでスクリーンショットを撮る」
- 「Googleでデスクトップエージェントを検索」

## 開発者ガイド

### プロジェクト構造
```
src/
├── agent/             # エージェント関連
│   ├── command_interpreter.py  # コマンド解釈
│   ├── voice_recognizer.py     # 音声認識
│   └── keyboard_monitor.py     # キーボード監視
├── desktop/           # デスクトップ制御
│   ├── browser_controller.py       # 基本ブラウザ制御
│   └── advanced_browser_controller.py  # 高度ブラウザ制御
├── db/                # データベース
│   └── models.py      # データモデル
├── gui/               # GUI
│   └── main_window.py # メインウィンドウ
├── models/            # 機械学習モデル
├── main.py            # エントリーポイント
└── config.yaml        # 設定ファイル
```

### 拡張方法
1. 新しいコマンドの追加:
   - `command_interpreter.py`にコマンドパターンとハンドラを追加

2. ブラウザ機能の拡張:
   - `advanced_browser_controller.py`に新しいブラウザ操作メソッドを追加

3. 音声認識の調整:
   - `voice_recognizer.py`でモデルサイズや設定をカスタマイズ

## ライセンス

MIT License

## 貢献

1. Forkを作成
2. 機能ブランチを作成
3. 変更をコミット
4. ブランチをPush
5. Pull Requestを作成

## サポート

問題が発生した場合は、以下を確認してください：
1. ログファイル（`logs/`ディレクトリ）
2. GPUドライバが最新かどうか確認
3. AIプロバイダーの設定とAPIキーの有効性

詳細なトラブルシューティングは[Wiki](https://github.com/zapabob/DesktopAgent/wiki)を参照してください。

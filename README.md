# 自律型AIデスクトップエージェント

自己強化学習と自己修復機能を備えた自律型デスクトップ操作AIエージェント

## 主な機能

### 1. キーボード操作
- テキスト入力
- キー押下
- ホットキー実行

### 2. マウス操作
- クリック（左/右/ダブル）
- カーソル移動
- ドラッグ＆ドロップ
- スクロール

### 3. ブラウザ操作
- URL操作
- 要素クリック
- フォーム入力
- スクロール
- ヘッドレスモード対応

### 4. ファイル操作
- ファイル作成/削除
- コピー/移動
- 読み込み/書き込み
- ディレクトリ管理

### 5. 自己学習・進化機能
- タスク実行の学習
- スキル獲得
- エラー検知と自己修復

## インストール

```bash
# 仮想環境の作成と有効化
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージのインストール
pip install -r requirements.txt
```

## 使用方法

### コマンドライン実行
```bash
# 基本実行
python main.py

# オプション付き実行
python main.py --config config.json --headless true
```

### プログラムからの利用
```python
from agent.core import AutoAgent

# エージェントの初期化
agent = AutoAgent()

# タスク例
agent.execute_task("type 'こんにちは、世界！'")
agent.execute_task("click button#submit")
agent.execute_task("browse https://example.com")
agent.execute_task("create test.txt")
```

### メインスクリプト (main.py)
```python
import argparse
import json
import os
from agent.core import AutoAgent

def main():
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='自律型AIデスクトップエージェント')
    parser.add_argument('--config', type=str, help='設定ファイルのパス')
    parser.add_argument('--headless', type=str, help='ブラウザのヘッドレスモード (true/false)')
    args = parser.parse_args()

    # 環境変数の設定
    if args.headless:
        os.environ['BROWSER_HEADLESS'] = args.headless

    # エージェントの初期化
    agent = AutoAgent(config_path=args.config)

    try:
        # ここにメインのタスク実行ロジックを記述
        while True:
            task = input("実行するタスクを入力してください（終了は 'exit'）: ")
            if task.lower() == 'exit':
                break
            
            result = agent.execute_task(task)
            print(f"実行結果: {'成功' if result else '失敗'}")

    except KeyboardInterrupt:
        print("\nプログラムを終了します")
    finally:
        # ブラウザなどのリソースをクリーンアップ
        if 'browser' in agent.controllers:
            agent.controllers['browser'].close()

if __name__ == '__main__':
    main()
```

## 設定

- `config.json`: エージェントの基本設定
- 環境変数:
  - `BROWSER_HEADLESS`: ブラウザのヘッドレスモード（true/false）

## 開発環境

- Python 3.8以上
- Windows/Mac/Linux対応
- 必要なパッケージ:
  - keyboard
  - pyautogui
  - selenium
  - python-dotenv

## ライセンス

Apache2.0ライセンス

作者
Ryo Minegishi

# MCP (Model Context Protocol) サーバー

MCPサーバーは、複数のAIモデルとブラウザ自動化を一元管理するためのプロトコルを提供します。このサーバーを使用することで、異なるLLMプロバイダー（OpenAI、Anthropic、Google AI）を統一的なインターフェースで利用でき、ブラウザの操作も同時に行うことができます。

## 主な機能

- **複数のAIモデルの一元管理**: OpenAI、Anthropic、Google AIなどの異なるプロバイダーのモデルを統一的に扱えます
- **ブラウザ自動化の統合**: LLMとブラウザ操作を組み合わせて高度な自動化が可能です
- **RESTful API**: 標準的なHTTP APIでどこからでもアクセス可能です
- **セッション管理**: 複数のブラウザセッションを同時に管理できます
- **非同期処理**: すべての操作は非同期で効率的に実行されます

## インストール

```bash
# リポジトリをクローン
git clone https://github.com/yourusername/mcp-server.git
cd mcp-server

# 依存関係のインストール
pip install -r requirements.txt

# browser-useが必要な場合（オプション）
pip install browser-use playwright
playwright install
```

## 環境変数の設定

`.env`ファイルを作成して、以下の環境変数を設定します：

```
# サーバー設定
MCP_HOST=127.0.0.1
MCP_PORT=8000

# API キー
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
GOOGLE_API_KEY=your_google_api_key
```

## 使用方法

### サーバーの起動

```bash
# サーバーを起動
cd src
python server.py
```

サーバーは`http://localhost:8000`でアクセス可能になります。

### クライアントからの使用

Pythonクライアントを使用する例：

```python
import asyncio
from client import MCPClient

async def main():
    async with MCPClient() as client:
        # サーバーステータスの確認
        status = await client.get_status()
        print(f"サーバーステータス: {status}")
        
        # テキスト生成の実行
        messages = [
            {"role": "system", "content": "あなたは役立つAIアシスタントです。"},
            {"role": "user", "content": "こんにちは、今日の天気を教えてください。"}
        ]
        
        response = await client.generate(messages)
        print(f"生成レスポンス: {response}")
        
        # ブラウザ操作の例
        result = await client.navigate("https://www.google.com")
        print(f"ナビゲーション結果: {result}")
        
        result = await client.search_google("MCPサーバー")
        print(f"Google検索結果: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## API エンドポイント

| エンドポイント | メソッド | 説明 |
|--------------|--------|------|
| `/health` | GET | サーバーのヘルスチェック |
| `/status` | GET | サーバーの詳細なステータス情報 |
| `/generate` | POST | テキスト生成リクエスト |
| `/browser` | POST | ブラウザ操作リクエスト |

## ブラウザアクション

以下のブラウザアクションがサポートされています：

- `navigate`: 指定したURLに移動
- `click`: 要素をクリック
- `type`: テキストを入力
- `screenshot`: スクリーンショットを撮影
- `get_text`: 要素のテキストを取得
- `evaluate`: JavaScriptを実行
- `search_youtube`: YouTubeで検索
- `search_google`: Googleで検索

## 注意事項

- 本番環境では適切なセキュリティ対策を講じてください
- APIキーは厳重に管理し、.envファイルをgitにコミットしないようにしてください
- ブラウザ自動化機能を使用するには、browser-useとPlaywrightのインストールが必要です

## ライセンス

MIT License 
import os
import sys
import asyncio
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("mcp_integration")

# クライアントのインポート
try:
    from client import MCPClient
except ImportError:
    logger.error("client.pyをインポートできませんでした。パスを確認してください。")
    sys.exit(1)

class MCPIntegration:
    """
    デスクトップエージェントとMCPサーバーを統合するためのクラス
    """
    
    def __init__(self, server_url: Optional[str] = None):
        """
        統合クラスを初期化します
        
        Args:
            server_url: MCPサーバーのURL（指定しない場合は環境変数または既定値を使用）
        """
        self.server_url = server_url
        self.client = None
        self.connected = False
        
        # 設定ファイルのロード
        self.load_config()
    
    def load_config(self):
        """設定を環境変数からロードします"""
        # 環境変数から設定を読み込む
        if not self.server_url:
            self.server_url = os.environ.get("MCP_SERVER_URL", "http://localhost:8000")
    
    async def connect(self) -> bool:
        """
        MCPサーバーに接続します
        
        Returns:
            bool: 接続が成功したかどうか
        """
        try:
            self.client = MCPClient(base_url=self.server_url)
            await self.client.__aenter__()
            
            # 接続テスト
            await self.client.health_check()
            self.connected = True
            logger.info(f"MCPサーバー ({self.server_url}) に接続しました")
            return True
        except Exception as e:
            logger.error(f"MCPサーバーへの接続に失敗しました: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """MCPサーバーから切断します"""
        if self.client:
            try:
                await self.client.__aexit__(None, None, None)
                logger.info("MCPサーバーから切断しました")
            except Exception as e:
                logger.error(f"MCPサーバーからの切断中にエラーが発生しました: {e}")
            finally:
                self.client = None
                self.connected = False
    
    async def generate_text(self, user_input: str, system_prompt: Optional[str] = None) -> str:
        """
        ユーザー入力に基づいてテキストを生成します
        
        Args:
            user_input: ユーザーからの入力
            system_prompt: システムプロンプト（指定しない場合はデフォルト値が使用されます）
            
        Returns:
            str: 生成されたテキスト
        """
        if not self.connected or not self.client:
            success = await self.connect()
            if not success:
                return "MCPサーバーに接続できません。テキスト生成を実行できません。"
        
        try:
            # メッセージの作成
            messages = []
            
            # システムプロンプトがある場合は追加
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                messages.append({"role": "system", "content": "あなたは役立つAIアシスタントです。"})
            
            # ユーザー入力を追加
            messages.append({"role": "user", "content": user_input})
            
            # テキスト生成を実行
            response = await self.client.generate(messages)
            
            # レスポンスからテキストを抽出
            if isinstance(response, dict) and "choices" in response:
                # OpenAI形式のレスポンス
                return response["choices"][0]["message"]["content"]
            elif isinstance(response, dict) and "text" in response:
                # シンプルな形式のレスポンス
                return response["text"]
            elif isinstance(response, str):
                # 文字列が直接返された場合
                return response
            else:
                # その他の形式
                return str(response)
        except Exception as e:
            logger.error(f"テキスト生成中にエラーが発生しました: {e}")
            return f"エラー: {str(e)}"
    
    async def process_browser_command(self, command: str) -> Dict[str, Any]:
        """
        ブラウザ操作コマンドを処理します
        
        Args:
            command: ブラウザコマンド文字列
            
        Returns:
            Dict[str, Any]: 実行結果
        """
        if not self.connected or not self.client:
            success = await self.connect()
            if not success:
                return {"status": "error", "message": "MCPサーバーに接続できません。ブラウザ操作を実行できません。"}
        
        try:
            # コマンドの解析
            parts = command.strip().split(' ', 1)
            action = parts[0].lower()
            
            # パラメータの抽出
            params = {}
            if len(parts) > 1:
                args = parts[1]
                
                if action == "navigate" or action == "goto" or action == "open":
                    params["url"] = args
                elif action == "click":
                    params["selector"] = args
                elif action == "type":
                    selector, text = args.split(' ', 1)
                    params["selector"] = selector
                    params["text"] = text
                elif action == "screenshot":
                    if args:
                        params["path"] = args
                elif action == "get_text":
                    params["selector"] = args
                elif action == "evaluate":
                    params["code"] = args
                elif action in ["search_youtube", "youtube"]:
                    params["query"] = args
                elif action in ["search_google", "google"]:
                    params["query"] = args
            
            # 適切なアクションの実行
            if action in ["navigate", "goto", "open"]:
                return await self.client.navigate(**params)
            elif action == "click":
                return await self.client.click(**params)
            elif action == "type":
                return await self.client.type_text(**params)
            elif action == "screenshot":
                return await self.client.screenshot(**params)
            elif action == "get_text":
                return await self.client.get_text(**params)
            elif action == "evaluate":
                return await self.client.evaluate_js(**params)
            elif action in ["search_youtube", "youtube"]:
                return await self.client.search_youtube(**params)
            elif action in ["search_google", "google"]:
                return await self.client.search_google(**params)
            else:
                return {"status": "error", "message": f"不明なブラウザアクション: {action}"}
        except Exception as e:
            logger.error(f"ブラウザコマンド処理中にエラーが発生しました: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_server_status(self) -> Dict[str, Any]:
        """
        サーバーのステータスを取得します
        
        Returns:
            Dict[str, Any]: サーバーステータス情報
        """
        if not self.connected or not self.client:
            success = await self.connect()
            if not success:
                return {"status": "error", "message": "MCPサーバーに接続できません。"}
        
        try:
            return await self.client.get_status()
        except Exception as e:
            logger.error(f"サーバーステータス取得中にエラーが発生しました: {e}")
            return {"status": "error", "message": str(e)}

# コマンドライン実行用の関数
async def main():
    parser = argparse.ArgumentParser(description="MCP統合スクリプト")
    parser.add_argument("--server", help="MCPサーバーのURL", default=None)
    parser.add_argument("--command", help="実行するコマンド (generate, browser, status)", required=True)
    parser.add_argument("--input", help="コマンドの入力", default=None)
    
    args = parser.parse_args()
    
    integration = MCPIntegration(server_url=args.server)
    await integration.connect()
    
    try:
        if args.command == "generate":
            if not args.input:
                print("Error: --input パラメータが必要です")
                return
            
            result = await integration.generate_text(args.input)
            print(result)
        
        elif args.command == "browser":
            if not args.input:
                print("Error: --input パラメータが必要です")
                return
                
            result = await integration.process_browser_command(args.input)
            print(result)
            
        elif args.command == "status":
            result = await integration.get_server_status()
            print(result)
            
        else:
            print(f"Error: 不明なコマンド: {args.command}")
    
    finally:
        await integration.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 
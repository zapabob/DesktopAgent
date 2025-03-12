import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional, Union, Callable, AsyncGenerator
import aiohttp
from pydantic import BaseModel, Field

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("mcp_client")

# データモデル
class MessageContent(BaseModel):
    type: str = "text"  # text, image, tool_call, tool_result
    text: Optional[str] = None
    image_url: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Any] = None

class Message(BaseModel):
    role: str  # user, assistant, system, tool
    content: Union[str, List[MessageContent], None] = None
    name: Optional[str] = None

class MCPClient:
    """
    MCPサーバーと通信するためのクライアント
    """
    
    def __init__(self, base_url: Optional[str] = None, session: Optional[aiohttp.ClientSession] = None):
        """
        MCPクライアントを初期化します
        
        Args:
            base_url: MCPサーバーのベースURL。指定されない場合は環境変数から読み込みます。
            session: 既存のaiohttp.ClientSessionインスタンス
        """
        # ベースURLの設定
        self.base_url = base_url or os.environ.get("MCP_SERVER_URL", "http://localhost:8000")
        
        # セッションの設定
        self.session = session
        self.session_owner = session is None
        
        # キャッシュと状態管理
        self.server_status = None
        self.server_status_timestamp = 0
        self.connected = False
    
    async def __aenter__(self):
        """非同期コンテキストマネージャーのエントリーポイント"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
            self.session_owner = True
        
        # 接続テスト
        try:
            await self.health_check()
            self.connected = True
        except Exception as e:
            logger.error(f"MCPサーバーに接続できません: {e}")
            self.connected = False
            
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーの終了ポイント"""
        if self.session_owner and self.session is not None:
            await self.session.close()
            self.session = None
    
    def _ensure_session(self):
        """セッションが存在することを確認します"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
            self.session_owner = True
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        HTTPリクエストを実行します
        
        Args:
            method: HTTPメソッド (GET, POST, etc.)
            endpoint: APIエンドポイント
            **kwargs: aiohttp.ClientSessionリクエストの追加引数
            
        Returns:
            レスポンスのJSONデータ
        """
        self._ensure_session()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    raise Exception(f"APIエラー ({response.status}): {error_text}")
                
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"HTTPリクエストエラー: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        サーバーのヘルスチェックを実行します
        
        Returns:
            ヘルスチェックレスポンス
        """
        return await self._request("GET", "/health")
    
    async def get_status(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        サーバーのステータス情報を取得します
        
        Args:
            force_refresh: キャッシュを無視して最新情報を取得するかどうか
            
        Returns:
            サーバーステータス情報
        """
        import time
        now = time.time()
        
        # キャッシュされたステータスを使用するかどうかを判断
        if not force_refresh and self.server_status is not None and now - self.server_status_timestamp < 60:
            return self.server_status
        
        # 新しいステータスを取得
        status = await self._request("GET", "/status")
        self.server_status = status
        self.server_status_timestamp = now
        
        return status
    
    async def generate(
        self,
        messages: List[Union[Message, Dict]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        テキスト生成リクエストを送信します
        
        Args:
            messages: メッセージの配列
            model: 使用するモデル
            max_tokens: 生成する最大トークン数
            temperature: 温度パラメータ
            top_p: top-pサンプリングパラメータ
            stream: ストリーミングモードを使用するかどうか
            tools: 利用可能なツールのリスト
            tool_choice: ツール選択オプション
            
        Returns:
            生成テキストの結果
        """
        # メッセージの変換
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                formatted_messages.append(msg)
            else:
                formatted_messages.append(msg.model_dump())
        
        # リクエストボディの作成
        request_body = {
            "messages": formatted_messages,
            "stream": stream
        }
        
        # オプションパラメータの追加
        if model is not None:
            request_body["model"] = model
        if max_tokens is not None:
            request_body["max_tokens"] = max_tokens
        if temperature is not None:
            request_body["temperature"] = temperature
        if top_p is not None:
            request_body["top_p"] = top_p
        if tools is not None:
            request_body["tools"] = tools
        if tool_choice is not None:
            request_body["tool_choice"] = tool_choice
        
        # ストリーミングモードの処理
        if stream:
            return self._stream_generate(request_body)
        
        # 通常の生成処理
        return await self._request("POST", "/generate", json=request_body)
    
    async def _stream_generate(self, request_body: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        ストリーミングモードでテキスト生成を行います
        
        Args:
            request_body: リクエスト本文
            
        Yields:
            ストリーミングレスポンスの各チャンク
        """
        self._ensure_session()
        url = f"{self.base_url}/generate"
        
        try:
            async with self.session.post(url, json=request_body) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    raise Exception(f"APIエラー ({response.status}): {error_text}")
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if not line:
                        continue
                    
                    if line.startswith('data: '):
                        line = line[6:]  # 'data: ' プレフィックスを削除
                        
                    if line == "[DONE]":
                        break
                        
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        logger.error(f"JSONデコードエラー: {line}")
        except aiohttp.ClientError as e:
            logger.error(f"ストリーミングエラー: {e}")
            raise
    
    async def execute_browser_action(self, action: str, **params) -> Dict[str, Any]:
        """
        ブラウザアクションを実行します
        
        Args:
            action: 実行するアクション
            **params: アクションに必要なパラメータ
            
        Returns:
            アクション実行の結果
        """
        request_body = {
            "action": action,
            "params": params
        }
        
        return await self._request("POST", "/browser", json=request_body)
    
    # ブラウザアクションのショートカットメソッド
    async def navigate(self, url: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        指定したURLに移動します
        
        Args:
            url: 移動先のURL
            session_id: 使用するブラウザセッションID
            
        Returns:
            アクション実行の結果
        """
        params = {"url": url}
        if session_id is not None:
            params["session_id"] = session_id
            
        return await self.execute_browser_action("navigate", **params)
    
    async def click(self, selector: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        要素をクリックします
        
        Args:
            selector: クリックする要素のセレクタ
            session_id: 使用するブラウザセッションID
            
        Returns:
            アクション実行の結果
        """
        params = {"selector": selector}
        if session_id is not None:
            params["session_id"] = session_id
            
        return await self.execute_browser_action("click", **params)
    
    async def type_text(self, selector: str, text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        要素にテキストを入力します
        
        Args:
            selector: 入力対象の要素のセレクタ
            text: 入力するテキスト
            session_id: 使用するブラウザセッションID
            
        Returns:
            アクション実行の結果
        """
        params = {"selector": selector, "text": text}
        if session_id is not None:
            params["session_id"] = session_id
            
        return await self.execute_browser_action("type", **params)
    
    async def screenshot(self, path: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        スクリーンショットを撮影します
        
        Args:
            path: スクリーンショットの保存先パス
            session_id: 使用するブラウザセッションID
            
        Returns:
            アクション実行の結果
        """
        params = {}
        if path is not None:
            params["path"] = path
        if session_id is not None:
            params["session_id"] = session_id
            
        return await self.execute_browser_action("screenshot", **params)
    
    async def get_text(self, selector: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        要素のテキストを取得します
        
        Args:
            selector: テキストを取得する要素のセレクタ
            session_id: 使用するブラウザセッションID
            
        Returns:
            アクション実行の結果
        """
        params = {"selector": selector}
        if session_id is not None:
            params["session_id"] = session_id
            
        return await self.execute_browser_action("get_text", **params)
    
    async def evaluate_js(self, code: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        JavaScriptコードを実行します
        
        Args:
            code: 実行するJavaScriptコード
            session_id: 使用するブラウザセッションID
            
        Returns:
            アクション実行の結果
        """
        params = {"code": code}
        if session_id is not None:
            params["session_id"] = session_id
            
        return await self.execute_browser_action("evaluate", **params)
    
    async def search_youtube(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        YouTubeで検索を実行します
        
        Args:
            query: 検索クエリ
            session_id: 使用するブラウザセッションID
            
        Returns:
            アクション実行の結果
        """
        params = {"query": query}
        if session_id is not None:
            params["session_id"] = session_id
            
        return await self.execute_browser_action("search_youtube", **params)
    
    async def search_google(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Googleで検索を実行します
        
        Args:
            query: 検索クエリ
            session_id: 使用するブラウザセッションID
            
        Returns:
            アクション実行の結果
        """
        params = {"query": query}
        if session_id is not None:
            params["session_id"] = session_id
            
        return await self.execute_browser_action("search_google", **params)

# 使用例
async def main():
    # クライアントの作成
    async with MCPClient() as client:
        # サーバーステータスの取得
        status = await client.get_status()
        print(f"サーバーステータス: {status}")
        
        # テキスト生成の例
        messages = [
            {"role": "system", "content": "あなたは役立つAIアシスタントです。"},
            {"role": "user", "content": "こんにちは、今日の天気を教えてください。"}
        ]
        
        response = await client.generate(messages)
        print(f"生成レスポンス: {response}")
        
        # ブラウザ操作の例
        try:
            result = await client.navigate("https://www.google.com")
            print(f"ナビゲーション結果: {result}")
            
            result = await client.search_google("Pythonプログラミング")
            print(f"Google検索結果: {result}")
            
            screenshot_result = await client.screenshot()
            print(f"スクリーンショット結果: {screenshot_result}")
        except Exception as e:
            print(f"ブラウザ操作エラー: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 
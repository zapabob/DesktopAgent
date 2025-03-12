import os
import sys
import asyncio
import logging
import subprocess
import threading
import time
from typing import Dict, Any, Optional, List, Tuple

# プロジェクトルートをパスに追加
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
mcp_path = os.path.join(project_root, "MCP", "src")
sys.path.append(mcp_path)

# MCPクライアントのインポート
try:
    from client import MCPClient
except ImportError:
    pass

# ロギングの設定
logger = logging.getLogger("mcp_adapter")

class MCPAdapter:
    """
    デスクトップエージェントとMCPサーバーを連携するためのアダプタクラス
    """
    
    def __init__(self, server_url: Optional[str] = None):
        """
        MCPアダプタを初期化
        
        Args:
            server_url: MCPサーバーのURL
        """
        self.server_url = server_url or os.environ.get("MCP_SERVER_URL", "http://localhost:8000")
        self.client = None
        self.connected = False
        self.server_process = None
        self.keep_alive_thread = None
        self.stop_flag = False
    
    async def connect(self) -> bool:
        """
        MCPサーバーに接続
        
        Returns:
            bool: 接続の成否
        """
        try:
            if 'MCPClient' not in globals():
                logger.error("MCPClientがインポートできません")
                return False
                
            self.client = MCPClient(base_url=self.server_url)
            await self.client.__aenter__()
            
            # 接続テスト
            await self.client.health_check()
            self.connected = True
            logger.info(f"MCPサーバーに接続しました: {self.server_url}")
            return True
        except Exception as e:
            logger.error(f"MCPサーバー接続エラー: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> None:
        """MCPサーバーから切断"""
        if self.client:
            try:
                await self.client.__aexit__(None, None, None)
                logger.info("MCPサーバーから切断しました")
            except Exception as e:
                logger.error(f"MCPサーバー切断エラー: {e}")
            finally:
                self.client = None
                self.connected = False
    
    def start_server(self) -> bool:
        """
        MCPサーバーを起動
        
        Returns:
            bool: 起動の成否
        """
        if self.server_process:
            logger.info("MCPサーバーは既に起動しています")
            return True
            
        try:
            # サーバー実行ファイルのパス
            server_script = os.path.join(mcp_path, "server.py")
            
            # 実行コマンドの構築
            cmd = [sys.executable, server_script]
            
            # サーバーをバックグラウンドで起動
            logger.info(f"MCPサーバーを起動: {' '.join(cmd)}")
            
            # Windows環境ではcreationflags=subprocess.CREATE_NO_WINDOWを追加
            if os.name == 'nt':
                self.server_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                self.server_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            # サーバー起動の待機
            max_retries = 10
            retry_interval = 1.0
            
            for i in range(max_retries):
                try:
                    # 非同期ループを作成して接続テスト
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    success = loop.run_until_complete(self._check_server_running())
                    loop.close()
                    
                    if success:
                        # Keep-Aliveスレッドの開始
                        self.stop_flag = False
                        self.keep_alive_thread = threading.Thread(target=self._keep_alive_worker)
                        self.keep_alive_thread.daemon = True
                        self.keep_alive_thread.start()
                        
                        logger.info("MCPサーバーが正常に起動しました")
                        return True
                except Exception as e:
                    pass
                    
                time.sleep(retry_interval)
            
            # 起動に失敗した場合
            logger.error("MCPサーバーの起動に失敗しました")
            self.stop_server()
            return False
            
        except Exception as e:
            logger.error(f"MCPサーバー起動エラー: {e}")
            return False
    
    async def _check_server_running(self) -> bool:
        """
        サーバーが起動しているか確認
        
        Returns:
            bool: サーバーが起動している場合はTrue
        """
        try:
            client = MCPClient(base_url=self.server_url)
            await client.__aenter__()
            await client.health_check()
            await client.__aexit__(None, None, None)
            return True
        except Exception:
            return False
    
    def _keep_alive_worker(self) -> None:
        """
        定期的にサーバーの状態を確認するワーカー
        """
        while not self.stop_flag:
            try:
                # 非同期ループを作成してヘルスチェック
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self._check_server_running())
                loop.close()
                
                if not result and self.server_process:
                    logger.warning("MCPサーバーが応答していません")
            except Exception as e:
                logger.error(f"Keep-Aliveエラー: {e}")
                
            # 10秒間隔でチェック
            time.sleep(10)
    
    def stop_server(self) -> bool:
        """
        MCPサーバーを停止
        
        Returns:
            bool: 停止の成否
        """
        if not self.server_process:
            logger.info("MCPサーバーは実行されていません")
            return True
            
        try:
            # Keep-Aliveスレッドの停止
            self.stop_flag = True
            if self.keep_alive_thread:
                self.keep_alive_thread.join(timeout=1.0)
                self.keep_alive_thread = None
            
            # サーバープロセスの終了
            self.server_process.terminate()
            
            # 終了を待機
            try:
                self.server_process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                logger.warning("MCPサーバーの終了がタイムアウトしました。強制終了します。")
                self.server_process.kill()
            
            self.server_process = None
            logger.info("MCPサーバーを停止しました")
            return True
        except Exception as e:
            logger.error(f"MCPサーバー停止エラー: {e}")
            return False
    
    async def generate_text(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """
        テキスト生成を実行
        
        Args:
            prompt: ユーザーからの入力
            system_prompt: システムプロンプト
            model: 使用するモデル名
            
        Returns:
            str: 生成されたテキスト
        """
        if not self.connected or not self.client:
            success = await self.connect()
            if not success:
                return "MCPサーバーに接続できません"
        
        try:
            # メッセージの構築
            messages = []
            
            # システムプロンプト
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                messages.append({"role": "system", "content": "あなたは役立つAIアシスタントです。"})
            
            # ユーザープロンプト
            messages.append({"role": "user", "content": prompt})
            
            # 生成パラメータ
            params = {}
            if model:
                params["model"] = model
            
            # テキスト生成の実行
            response = await self.client.generate(messages, **params)
            
            # レスポンスの解析
            if isinstance(response, dict):
                if "choices" in response and len(response["choices"]) > 0:
                    # OpenAI形式
                    return response["choices"][0]["message"]["content"]
                elif "response" in response:
                    # カスタム形式
                    return response["response"]
                elif "text" in response:
                    # シンプル形式
                    return response["text"]
            
            # その他の形式
            return str(response)
        except Exception as e:
            logger.error(f"テキスト生成エラー: {e}")
            return f"エラー: {str(e)}"
    
    async def execute_browser_action(self, action: str, **params) -> Dict[str, Any]:
        """
        ブラウザアクションを実行
        
        Args:
            action: 実行するアクション
            **params: アクションのパラメータ
            
        Returns:
            Dict[str, Any]: 実行結果
        """
        if not self.connected or not self.client:
            success = await self.connect()
            if not success:
                return {"status": "error", "message": "MCPサーバーに接続できません"}
        
        try:
            # ブラウザアクションの実行
            result = await self.client.execute_browser_action(action, **params)
            return result
        except Exception as e:
            logger.error(f"ブラウザアクションエラー ({action}): {e}")
            return {"status": "error", "message": str(e)}
    
    async def navigate(self, url: str) -> Dict[str, Any]:
        """
        指定URLに移動
        
        Args:
            url: 移動先URL
            
        Returns:
            Dict[str, Any]: 実行結果
        """
        return await self.execute_browser_action("navigate", url=url)
    
    async def click(self, selector: str) -> Dict[str, Any]:
        """
        要素をクリック
        
        Args:
            selector: クリックする要素のセレクタ
            
        Returns:
            Dict[str, Any]: 実行結果
        """
        return await self.execute_browser_action("click", selector=selector)
    
    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """
        テキストを入力
        
        Args:
            selector: 入力対象要素のセレクタ
            text: 入力するテキスト
            
        Returns:
            Dict[str, Any]: 実行結果
        """
        return await self.execute_browser_action("type", selector=selector, text=text)
    
    async def screenshot(self, path: Optional[str] = None) -> Dict[str, Any]:
        """
        スクリーンショットを撮影
        
        Args:
            path: 保存先パス
            
        Returns:
            Dict[str, Any]: 実行結果
        """
        params = {}
        if path:
            params["path"] = path
        return await self.execute_browser_action("screenshot", **params)
    
    async def get_text(self, selector: str) -> Dict[str, Any]:
        """
        要素のテキストを取得
        
        Args:
            selector: テキストを取得する要素のセレクタ
            
        Returns:
            Dict[str, Any]: 実行結果
        """
        return await self.execute_browser_action("get_text", selector=selector)
    
    async def search_google(self, query: str) -> Dict[str, Any]:
        """
        Google検索を実行
        
        Args:
            query: 検索クエリ
            
        Returns:
            Dict[str, Any]: 実行結果
        """
        return await self.execute_browser_action("search_google", query=query)
    
    async def search_youtube(self, query: str) -> Dict[str, Any]:
        """
        YouTube検索を実行
        
        Args:
            query: 検索クエリ
            
        Returns:
            Dict[str, Any]: 実行結果
        """
        return await self.execute_browser_action("search_youtube", query=query)
    
    async def get_server_status(self) -> Dict[str, Any]:
        """
        サーバーステータスを取得
        
        Returns:
            Dict[str, Any]: サーバーステータス
        """
        if not self.connected or not self.client:
            success = await self.connect()
            if not success:
                return {"status": "error", "message": "MCPサーバーに接続できません"}
        
        try:
            return await self.client.get_status()
        except Exception as e:
            logger.error(f"ステータス取得エラー: {e}")
            return {"status": "error", "message": str(e)}
    
    def run_async(self, coro):
        """
        非同期関数を同期的に実行
        
        Args:
            coro: 実行する非同期コルーチン
            
        Returns:
            Any: コルーチンの実行結果
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # イベントループがない場合は新規作成
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(coro) 
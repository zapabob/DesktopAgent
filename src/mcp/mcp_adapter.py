import os
import sys
import time
import logging
import socket
import asyncio
import json
import subprocess
import threading
import requests
from typing import Any, Dict, Optional, List, Union, Tuple


# ロギングの設定
logger = logging.getLogger(__name__)

class MCPAdapter:
    """
    MCPサーバーとデスクトップエージェント間の通信を管理するアダプタークラス
    """
    
    def __init__(self, host: str = None, port: int = None):
        """
        MCPアダプタを初期化します。
        
        Args:
            host (str, optional): MCPサーバーのホスト。デフォルトはNone（環境変数から読み込み）
            port (int, optional): MCPサーバーのポート。デフォルトはNone（環境変数から読み込み）
        """
        # 設定の読み込み
        self.host = host or os.environ.get("MCP_HOST", "localhost")
        self.port = port or int(os.environ.get("MCP_PORT", 8765))
        self.base_url = f"http://{self.host}:{self.port}"
        
        # APIエンドポイントを修正（サーバーのエンドポイント構造に合わせる）
        # self.api_url = f"{self.base_url}/api"
        
        # サーバー情報
        self.server_process = None
        self.keep_alive_thread = None
        self.running = False
        
        # 接続情報
        self.connected = False
        
        logger.info(f"MCPアダプタを初期化しました: {self.base_url}")
    
    async def connect(self) -> bool:
        """
        MCPサーバーに接続します。
        
        Returns:
            bool: 接続に成功したかどうか
        """
        try:
            # サーバーの稼働状態を確認
            status = await self.get_status()
            if status.get("status") == "healthy":
                self.connected = True
                logger.info("MCPサーバーに接続しました")
                return True
            else:
                logger.error(f"MCPサーバーの状態が正常ではありません: {status}")
                return False
        except Exception as e:
            logger.error(f"MCPサーバーへの接続に失敗しました: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> bool:
        """
        MCPサーバーから切断します。
        
        Returns:
            bool: 切断に成功したかどうか
        """
        self.connected = False
        logger.info("MCPサーバーから切断しました")
        return True
    
    def start_server(self) -> bool:
        """
        MCPサーバーを起動します。
        
        Returns:
            bool: サーバーの起動に成功したかどうか
        """
        # サーバーが既に実行中かどうか確認
        if self.is_server_running():
            logger.info("MCPサーバーは既に実行中です")
            return True
        
        try:
            # サーバーディレクトリの取得
            base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            server_dir = os.path.join(base_dir, "MCP")
            
            if not os.path.exists(server_dir):
                logger.error(f"サーバーディレクトリが見つかりません: {server_dir}")
                return False
            
            # 環境変数とコマンド設定
            env = os.environ.copy()
            env["PYTHONPATH"] = server_dir
            
            # サーバー起動コマンド
            if sys.platform == "win32":
                cmd = ["python", os.path.join(server_dir, "src", "server.py")]
            else:
                cmd = ["python3", os.path.join(server_dir, "src", "server.py")]
            
            # サーバープロセスの起動
            logger.info(f"MCPサーバーを起動します: {' '.join(cmd)}")
            self.server_process = subprocess.Popen(
                cmd,
                cwd=server_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            # サーバーの起動を待機
            self.running = True
            max_retries = 10
            for i in range(max_retries):
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=1)
                    if response.status_code == 200:
                        logger.info("MCPサーバーが起動しました")
                        # キープアライブスレッドの開始
                        self._start_keep_alive_thread()
                        return True
                    else:
                        logger.error(f"MCPサーバーが応答しません: {response.status_code}")
                except Exception as e:
                    logger.error(f"MCPサーバーの起動中にエラーが発生しました: {e}")
                time.sleep(1)  # 1秒待機
            
            logger.error(f"MCPサーバーの起動に失敗しました: {max_retries}回のリトライ後にサーバーが応答しません")
            self.stop_server()
            return False
            
        except Exception as e:
            logger.error(f"MCPサーバーの起動中にエラーが発生しました: {e}")
            self.running = False
            return False
    
    def stop_server(self) -> bool:
        """
        MCPサーバーを停止します。
        
        Returns:
            bool: サーバーの停止に成功したかどうか
        """
        # キープアライブスレッドの停止
        if self.keep_alive_thread and self.keep_alive_thread.is_alive():
            self.running = False
            self.keep_alive_thread.join(timeout=2)
            self.keep_alive_thread = None
        
        # サーバープロセスの停止
        if self.server_process:
            try:
                # まずはAPIで停止を試みる
                try:
                    requests.post(f"{self.base_url}/shutdown", timeout=2)
                    # 少し待機して自然に終了するか確認
                    time.sleep(2)
                
                except Exception as e:
                    logger.error(f"MCPサーバーの停止中にエラーが発生しました: {e}")
                
                # プロセスが終了したか確認
                if self.server_process.poll() is None:
                    # まだ実行中の場合、強制終了
                    self.server_process.terminate()
                    self.server_process.wait(timeout=5)
                
                logger.info("MCPサーバーを停止しました")
                self.server_process = None
                return True
            except Exception as e:
                logger.error(f"MCPサーバーの停止中にエラーが発生しました: {e}")
                return False
        
        return True  # サーバーが実行されていない場合も成功として扱う
    
    def is_server_running(self) -> bool:
        """
        MCPサーバーが実行中かどうかを確認します。
        
        Returns:
            bool: サーバーが実行中であればTrue
        """
        # プロセスの状態確認
        if self.server_process and self.server_process.poll() is None:
            # APIで動作確認
            try:
                response = requests.get(f"{self.base_url}/health", timeout=1)
                return response.status_code == 200
            except Exception as e:
                logger.error(f"MCPサーバーの実行状態確認中にエラーが発生しました: {e}")
                return False
        
        # サーバーがすでに起動しているか確認（外部で起動されているケース）
        try:
            response = requests.get(f"{self.base_url}/health", timeout=1)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"MCPサーバーの実行状態確認中にエラーが発生しました: {e}")
            return False
    
    def _start_keep_alive_thread(self):
        """
        サーバーの状態を監視し、必要に応じて再起動するスレッドを開始します。
        """
        if self.keep_alive_thread and self.keep_alive_thread.is_alive():
            return  # すでに実行中
        
        def keep_alive():
            """サーバーの状態を監視するスレッド関数"""
            check_interval = 30  # 30秒ごとに確認
            
            while self.running:
                time.sleep(check_interval)
                
                # サーバーの状態確認
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=2)
                    if response.status_code != 200:
                        logger.warning("MCPサーバーが応答しません。再起動を試みます。")
                        self.stop_server()
                        time.sleep(1)
                        self.start_server()
                except Exception as e:
                    logger.warning(f"MCPサーバーとの接続が失われました: {e}。再起動を試みます。")
                    self.stop_server()
                    time.sleep(1)
                    self.start_server()
        self.running = True
        self.keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
        self.keep_alive_thread.start()
    
    async def get_status(self) -> Dict[str, Any]:
        """
        サーバーの状態を取得します。
        
        Returns:
            Dict[str, Any]: サーバーの状態を表す辞書
        """
        try:
            async with asyncio.timeout(5):  # 5秒のタイムアウト
                session = requests.Session()
                response = session.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    return {"status": "healthy", "message": "サーバーは正常に動作しています"}
                else:
                    return {"status": "unhealthy", "message": f"ステータスコード: {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": f"サーバーとの通信エラー: {str(e)}"}
    
    async def generate_text(self, prompt: str, system_prompt: str = None, model: str = None) -> Dict[str, Any]:
        """
        テキスト生成リクエストを送信します。
        
        Args:
            prompt (str): ユーザープロンプト
            system_prompt (str, optional): システムプロンプト
            model (str, optional): 使用するモデル名
            
        Returns:
            Dict[str, Any]: 生成結果を含む辞書
        """
        if not self.connected:
            if not await self.connect():
                return {"status": "error", "message": "サーバーに接続されていません"}
        
        try:
            # URLを修正
            url = f"{self.base_url}/generate"
            payload = {
                "messages": [
                    {"role": "system", "content": system_prompt} if system_prompt else None,
                    {"role": "user", "content": prompt}
                ],
                "model": model,
                "stream": False
            }
            # Noneの項目を削除
            payload["messages"] = [msg for msg in payload["messages"] if msg]
            
            async with asyncio.timeout(60):  # 60秒のタイムアウト
                session = requests.Session()
                response = session.post(url, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    return {"status": "success", "result": result.get("text", ""), "model": result.get("model")}
                else:
                    return {"status": "error", "message": f"APIエラー: {response.status_code} - {response.text}"}
        except Exception as e:
            logger.error(f"テキスト生成中にエラーが発生しました: {e}")
            return {"status": "error", "message": f"エラー: {str(e)}"}
    
    async def navigate(self, url: str) -> Dict[str, Any]:
        """
        指定したURLにブラウザを移動させます。
        
        Args:
            url (str): 移動先のURL
            
        Returns:
            Dict[str, Any]: 操作結果を含む辞書
        """
        if not self.connected:
            if not await self.connect():
                return {"status": "error", "message": "サーバーに接続されていません"}
        
        try:
            # URLを修正
            api_url = f"{self.base_url}/browser"
            payload = {
                "action": "navigate",
                "params": {"url": url}
            }
            
            async with asyncio.timeout(30):  # 30秒のタイムアウト
                session = requests.Session()
                response = session.post(api_url, json=payload)
                
                if response.status_code == 200:
                    return {"status": "success", "result": response.json()}
                else:
                    return {"status": "error", "message": f"APIエラー: {response.status_code} - {response.text}"}
        except Exception as e:
            logger.error(f"ナビゲーション中にエラーが発生しました: {e}")
            return {"status": "error", "message": f"エラー: {str(e)}"}
    
    async def click(self, selector: str) -> Dict[str, Any]:
        """
        指定したセレクタの要素をクリックします。
        
        Args:
            selector (str): クリックする要素のセレクタ
            
        Returns:
            Dict[str, Any]: 操作結果を含む辞書
        """
        if not self.connected:
            if not await self.connect():
                return {"status": "error", "message": "サーバーに接続されていません"}
        
        try:
            # URLを修正
            api_url = f"{self.base_url}/browser"
            payload = {
                "action": "click",
                "params": {"selector": selector}
            }
            
            async with asyncio.timeout(30):  # 30秒のタイムアウト
                session = requests.Session()
                response = session.post(api_url, json=payload)
                
                if response.status_code == 200:
                    return {"status": "success", "result": response.json()}
                else:
                    return {"status": "error", "message": f"APIエラー: {response.status_code} - {response.text}"}
        except Exception as e:
            logger.error(f"クリック操作中にエラーが発生しました: {e}")
            return {"status": "error", "message": f"エラー: {str(e)}"}
    
    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """
        指定したセレクタの要素にテキストを入力します。
        
        Args:
            selector (str): テキストを入力する要素のセレクタ
            text (str): 入力するテキスト
            
        Returns:
            Dict[str, Any]: 操作結果を含む辞書
        """
        if not self.connected:
            if not await self.connect():
                return {"status": "error", "message": "サーバーに接続されていません"}
        
        try:
            # URLを修正
            api_url = f"{self.base_url}/browser"
            payload = {
                "action": "type",
                "params": {"selector": selector, "text": text}
            }
            
            async with asyncio.timeout(30):  # 30秒のタイムアウト
                session = requests.Session()
                response = session.post(api_url, json=payload)
                
                if response.status_code == 200:
                    return {"status": "success", "result": response.json()}
                else:
                    return {"status": "error", "message": f"APIエラー: {response.status_code} - {response.text}"}
        except Exception as e:
            logger.error(f"テキスト入力中にエラーが発生しました: {e}")
            return {"status": "error", "message": f"エラー: {str(e)}"}
    
    async def get_text(self, selector: str) -> Dict[str, Any]:
        """
        指定したセレクタの要素のテキストを取得します。
        
        Args:
            selector (str): テキストを取得する要素のセレクタ
            
        Returns:
            Dict[str, Any]: 取得したテキストを含む辞書
        """
        if not self.connected:
            if not await self.connect():
                return {"status": "error", "message": "サーバーに接続されていません"}
        
        try:
            # URLを修正
            api_url = f"{self.base_url}/browser"
            payload = {
                "action": "get_text",
                "params": {"selector": selector}
            }
            
            async with asyncio.timeout(30):  # 30秒のタイムアウト
                session = requests.Session()
                response = session.post(api_url, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    return {"status": "success", "result": result.get("result", {}).get("text", "")}
                else:
                    return {"status": "error", "message": f"APIエラー: {response.status_code} - {response.text}"}
        except Exception as e:
            logger.error(f"テキスト取得中にエラーが発生しました: {e}")
            return {"status": "error", "message": f"エラー: {str(e)}"}
    
    async def evaluate_js(self, code: str) -> Dict[str, Any]:
        """
        JavaScriptコードを実行します。
        
        Args:
            code (str): 実行するJavaScriptコード
            
        Returns:
            Dict[str, Any]: 実行結果を含む辞書
        """
        if not self.connected:
            if not await self.connect():
                return {"status": "error", "message": "サーバーに接続されていません"}
        
        try:
            # URLを修正
            api_url = f"{self.base_url}/browser"
            payload = {
                "action": "evaluate",
                "params": {"code": code}
            }
            
            async with asyncio.timeout(30):  # 30秒のタイムアウト
                session = requests.Session()
                response = session.post(api_url, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    return {"status": "success", "result": result.get("result", {}).get("result", "")}
                else:
                    return {"status": "error", "message": f"APIエラー: {response.status_code} - {response.text}"}
        except Exception as e:
            logger.error(f"JavaScript実行中にエラーが発生しました: {e}")
            return {"status": "error", "message": f"エラー: {str(e)}"}
    
    async def screenshot(self, path: str = None) -> Dict[str, Any]:
        """
        スクリーンショットを撮影します。
        
        Args:
            path (str, optional): スクリーンショットの保存先パス
            
        Returns:
            Dict[str, Any]: スクリーンショットのパスを含む辞書
        """
        if not self.connected:
            if not await self.connect():
                return {"status": "error", "message": "サーバーに接続されていません"}
        
        try:
            # URLを修正
            api_url = f"{self.base_url}/browser"
            payload = {
                "action": "screenshot",
                "params": {}
            }
            if path:
                payload["params"]["path"] = path
            
            async with asyncio.timeout(30):  # 30秒のタイムアウト
                session = requests.Session()
                response = session.post(api_url, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    result = result.get("result", {})
                    if "path" in result:
                        # ファイルとして保存されている場合
                        return {"status": "success", "result": {"path": result["path"]}}
                    elif "image" in result:
                        # Base64画像データが返された場合
                        if path:
                            # Base64データをファイルに保存
                            import base64
                            img_data = base64.b64decode(result["image"])
                            with open(path, "wb") as f:
                                f.write(img_data)
                            return {"status": "success", "result": {"path": path}}
                        else:
                            return {"status": "success", "result": {"image": result["image"]}}
                    else:
                        return {"status": "error", "message": "スクリーンショットデータが含まれていません"}
                else:
                    return {"status": "error", "message": f"APIエラー: {response.status_code} - {response.text}"}
        except Exception as e:
            logger.error(f"スクリーンショット撮影中にエラーが発生しました: {e}")
            return {"status": "error", "message": f"エラー: {str(e)}"}
    
    async def search_google(self, query: str) -> Dict[str, Any]:
        """
        Googleで検索を実行します。
        
        Args:
            query (str): 検索クエリ
            
        Returns:
            Dict[str, Any]: 検索結果を含む辞書
        """
        url = f"https://www.google.com/search?q={query}"
        return await self.navigate(url)
    
    async def search_youtube(self, query: str) -> Dict[str, Any]:
        """
        YouTubeで検索を実行します。
        
        Args:
            query (str): 検索クエリ
            
        Returns:
            Dict[str, Any]: 検索結果を含む辞書
        """
        url = f"https://www.youtube.com/results?search_query={query}"
        return await self.navigate(url)
    
    def run_async(self, coro):
        """
        非同期関数を同期的に実行します。
        
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
        
        try:
            return loop.run_until_complete(coro)
        except Exception as e:
            logger.error(f"非同期実行中にエラーが発生しました: {e}")
            return {"status": "error", "message": f"非同期実行エラー: {str(e)}"} 
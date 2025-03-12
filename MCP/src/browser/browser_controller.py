import os
import logging
import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import traceback
import browser_use

# ロギングの設定
logger = logging.getLogger(__name__)

# browser-useパッケージが利用可能かチェック
try:
    import browser_use as browser_use
    BROWSER_USE_AVAILABLE = True
    logger.info("browser-useパッケージが見つかりました")
except ImportError:
    BROWSER_USE_AVAILABLE = False
    logger.warning("browser-useパッケージが見つかりません。基本的なブラウザ機能のみが利用可能です。")

class BrowserSession:
    """
    単一のブラウザセッションを管理するクラス。
    browser-useを使用して単一のブラウザインスタンスとの対話を管理します。
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.browser = None
        self.loop = None
        self.last_activity = time.time()
        self.metadata = {
            "created_at": time.time(),
            "current_url": None,
            "title": None,
            "tabs": 1
        }
        self.methods = {}
        self.initialized = False
    
    async def initialize(self) -> bool:
        """ブラウザセッションを初期化します"""
        if not BROWSER_USE_AVAILABLE:
            logger.error(f"セッション {self.session_id}: browser-useパッケージが利用できません")
            return False
            
        try:
            # 新しいイベントループの作成
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Browserインスタンスを作成
            self.browser = browser_use.Browser()
            
            # APIメソッドの存在を確認
            # navigate/open/gotoメソッドのいずれかを使用
            if hasattr(self.browser, 'navigate'):
                self.methods['navigate'] = self.browser.navigate
            elif hasattr(self.browser, 'open'):
                self.methods['navigate'] = self.browser.open
            elif hasattr(self.browser, 'goto'):
                self.methods['navigate'] = self.browser.goto
            else:
                self.methods['navigate'] = lambda url: self.browser._page.goto(url)
                
            # YouTubeメソッド
            if hasattr(self.browser, 'youtube'):
                self.methods['youtube'] = self.browser.youtube
            elif hasattr(self.browser, 'search_youtube'):
                self.methods['youtube'] = self.browser.search_youtube
            
            # Googleメソッド
            if hasattr(self.browser, 'google'):
                self.methods['google'] = self.browser.google
            elif hasattr(self.browser, 'search_google'):
                self.methods['google'] = self.browser.search_google
                
            # その他のメソッド
            self.methods['click'] = getattr(self.browser, 'click', None)
            self.methods['type'] = getattr(self.browser, 'type', None)
            self.methods['screenshot'] = getattr(self.browser, 'screenshot', None)
            self.methods['get_text'] = getattr(self.browser, 'get_text', None)
            self.methods['evaluate'] = getattr(self.browser, 'evaluate', None)
            
            self.initialized = True
            logger.info(f"セッション {self.session_id}: ブラウザインスタンスを初期化しました")
            return True
        except Exception as e:
            logger.error(f"セッション {self.session_id}: ブラウザの初期化に失敗しました: {e}")
            traceback.print_exc()
            return False
    
    async def run_async(self, coro):
        """
        非同期関数を実行するヘルパーメソッド
        """
        if not self.initialized or self.browser is None:
            raise ValueError("ブラウザが初期化されていません")
            
        self.last_activity = time.time()
        
        try:
            return await coro
        except Exception as e:
            logger.error(f"セッション {self.session_id}: ブラウザ操作エラー: {e}")
            raise
    
    async def navigate(self, url: str) -> bool:
        """指定したURLに移動します"""
        if 'navigate' not in self.methods or self.methods['navigate'] is None:
            logger.error(f"セッション {self.session_id}: navigateメソッドが利用できません")
            return False
            
        try:
            # URLにスキームがない場合は追加
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
                
            result = await self.run_async(self.methods['navigate'](url))
            
            # メタデータの更新
            self.metadata["current_url"] = url
            # タイトル取得を試みる
            try:
                title = await self.run_async(self.browser.evaluate("document.title"))
                self.metadata["title"] = title
            except:
                pass
                
            return result is not False  # None の場合も成功とみなす
        except Exception as e:
            logger.error(f"セッション {self.session_id}: ナビゲーションエラー ({url}): {e}")
            return False
    
    async def click(self, selector: str) -> bool:
        """要素をクリックします"""
        if 'click' not in self.methods or self.methods['click'] is None:
            logger.error(f"セッション {self.session_id}: clickメソッドが利用できません")
            return False
            
        try:
            result = await self.run_async(self.methods['click'](selector))
            return result is not False
        except Exception as e:
            logger.error(f"セッション {self.session_id}: クリックエラー ({selector}): {e}")
            return False
    
    async def type(self, selector: str, text: str) -> bool:
        """要素にテキストを入力します"""
        if 'type' not in self.methods or self.methods['type'] is None:
            logger.error(f"セッション {self.session_id}: typeメソッドが利用できません")
            return False
            
        try:
            result = await self.run_async(self.methods['type'](selector, text))
            return result is not False
        except Exception as e:
            logger.error(f"セッション {self.session_id}: タイプエラー ({selector}): {e}")
            return False
    
    async def screenshot(self, path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """スクリーンショットを撮影します"""
        if 'screenshot' not in self.methods or self.methods['screenshot'] is None:
            logger.error(f"セッション {self.session_id}: screenshotメソッドが利用できません")
            return False, None
            
        try:
            # パスが指定されていない場合はデフォルトのパスを使用
            if path is None:
                now = time.strftime("%Y%m%d_%H%M%S")
                screenshots_dir = Path("screenshots")
                screenshots_dir.mkdir(exist_ok=True)
                path = str(screenshots_dir / f"screenshot_{self.session_id}_{now}.png")
            
            result = await self.run_async(self.methods['screenshot'](path))
            return result is not False, path
        except Exception as e:
            logger.error(f"セッション {self.session_id}: スクリーンショットエラー: {e}")
            return False, None
    
    async def get_text(self, selector: str) -> Optional[str]:
        """要素のテキストを取得します"""
        if 'get_text' not in self.methods or self.methods['get_text'] is None:
            logger.error(f"セッション {self.session_id}: get_textメソッドが利用できません")
            return None
            
        try:
            result = await self.run_async(self.methods['get_text'](selector))
            return result
        except Exception as e:
            logger.error(f"セッション {self.session_id}: テキスト取得エラー ({selector}): {e}")
            return None
    
    async def evaluate(self, code: str) -> Any:
        """JavaScriptコードを実行します"""
        if 'evaluate' not in self.methods or self.methods['evaluate'] is None:
            logger.error(f"セッション {self.session_id}: evaluateメソッドが利用できません")
            return None
            
        try:
            result = await self.run_async(self.methods['evaluate'](code))
            return result
        except Exception as e:
            logger.error(f"セッション {self.session_id}: JavaScript実行エラー: {e}")
            return None
            
    async def search_youtube(self, query: str) -> bool:
        """YouTubeで検索します"""
        if 'youtube' not in self.methods or self.methods['youtube'] is None:
            logger.error(f"セッション {self.session_id}: YouTubeメソッドが利用できません")
            # フォールバック: 直接URLに移動
            return await self.navigate(f"https://www.youtube.com/results?search_query={query}")
            
        try:
            result = await self.run_async(self.methods['youtube'](query))
            # メタデータの更新
            self.metadata["current_url"] = f"https://www.youtube.com/results?search_query={query}"
            return result is not False
        except Exception as e:
            logger.error(f"セッション {self.session_id}: YouTube検索エラー ({query}): {e}")
            return False
            
    async def search_google(self, query: str) -> bool:
        """Googleで検索します"""
        if 'google' not in self.methods or self.methods['google'] is None:
            logger.error(f"セッション {self.session_id}: Googleメソッドが利用できません")
            # フォールバック: 直接URLに移動
            return await self.navigate(f"https://www.google.com/search?q={query}")
            
        try:
            result = await self.run_async(self.methods['google'](query))
            # メタデータの更新
            self.metadata["current_url"] = f"https://www.google.com/search?q={query}"
            return result is not False
        except Exception as e:
            logger.error(f"セッション {self.session_id}: Google検索エラー ({query}): {e}")
            return False
    
    async def close(self) -> bool:
        """ブラウザセッションを閉じます"""
        if self.browser is None:
            return True
            
        try:
            # クローズメソッドを探す
            close_method = None
            if hasattr(self.browser, 'close'):
                close_method = self.browser.close
            elif hasattr(self.browser, 'shutdown'):
                close_method = self.browser.shutdown
                
            if close_method is not None:
                await self.run_async(close_method())
            
            self.browser = None
            self.methods = {}
            self.initialized = False
            logger.info(f"セッション {self.session_id}: ブラウザセッションを閉じました")
            return True
        except Exception as e:
            logger.error(f"セッション {self.session_id}: ブラウザクローズエラー: {e}")
            self.browser = None  # エラーでもリソースを解放
            self.methods = {}
            self.initialized = False
            return False

class BrowserController:
    """
    複数のブラウザセッションを管理するコントローラークラス。
    セッションの作成、削除、タイムアウト管理などを行います。
    """
    
    def __init__(self):
        self.sessions: Dict[str, BrowserSession] = {}
        self.default_session_id = None
        self.session_timeout = 1800  # 30分
        self.cleanup_interval = 300  # 5分ごとに掃除
        self.cleanup_task = None
        
    async def initialize(self) -> None:
        """コントローラーを初期化します"""
        logger.info("ブラウザコントローラーの初期化を開始...")
        
        if not BROWSER_USE_AVAILABLE:
            logger.warning("browser-useパッケージが利用できないため、機能が制限されます")
        
        # デフォルトのセッションを作成
        await self.create_session()
        
        # 定期的なクリーンアップタスクを開始
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
    async def create_session(self) -> str:
        """
        新しいブラウザセッションを作成します
        
        Returns:
            str: 作成されたセッションのID
        """
        session_id = str(uuid.uuid4())
        session = BrowserSession(session_id)
        
        success = await session.initialize()
        if not success:
            logger.error(f"セッション {session_id} の初期化に失敗しました")
            return None
            
        self.sessions[session_id] = session
        
        # 最初のセッションをデフォルトとして設定
        if self.default_session_id is None:
            self.default_session_id = session_id
            
        logger.info(f"セッション {session_id} を作成しました")
        return session_id
    
    async def execute_action(self, action: str, **kwargs) -> Any:
        """
        ブラウザアクションを実行します
        
        Args:
            action: 実行するアクション名
            **kwargs: アクションに必要なパラメータ
            
        Returns:
            アクションの結果
        """
        # セッションIDの取得（指定がなければデフォルトを使用）
        session_id = kwargs.pop("session_id", self.default_session_id)
        
        # セッションが存在しない場合はデフォルトセッションを作成
        if session_id is None or session_id not in self.sessions:
            if self.default_session_id is not None and self.default_session_id in self.sessions:
                session_id = self.default_session_id
            else:
                session_id = await self.create_session()
                if session_id is None:
                    raise ValueError("ブラウザセッションを作成できませんでした")
        
        session = self.sessions[session_id]
        
        # アクションに基づいてメソッドを呼び出す
        if action == "navigate":
            return await session.navigate(kwargs.get("url", ""))
        elif action == "click":
            return await session.click(kwargs.get("selector", ""))
        elif action == "type":
            return await session.type(kwargs.get("selector", ""), kwargs.get("text", ""))
        elif action == "screenshot":
            success, path = await session.screenshot(kwargs.get("path"))
            return {"success": success, "path": path}
        elif action == "get_text":
            return await session.get_text(kwargs.get("selector", ""))
        elif action == "evaluate":
            return await session.evaluate(kwargs.get("code", ""))
        elif action == "search_youtube":
            return await session.search_youtube(kwargs.get("query", ""))
        elif action == "search_google":
            return await session.search_google(kwargs.get("query", ""))
        elif action == "close":
            return await self.close_session(session_id)
        else:
            raise ValueError(f"不明なアクション: {action}")
    
    async def close_session(self, session_id: str) -> bool:
        """
        指定されたセッションを閉じます
        
        Args:
            session_id: 閉じるセッションのID
            
        Returns:
            bool: 成功したかどうか
        """
        if session_id not in self.sessions:
            logger.warning(f"セッション {session_id} が見つかりません")
            return False
            
        session = self.sessions[session_id]
        success = await session.close()
        
        # セッションをリストから削除
        del self.sessions[session_id]
        
        # このセッションがデフォルトだった場合、新しいデフォルトを設定
        if session_id == self.default_session_id:
            if self.sessions:
                self.default_session_id = next(iter(self.sessions.keys()))
            else:
                self.default_session_id = None
                
        logger.info(f"セッション {session_id} を閉じました")
        return success
    
    async def _cleanup_loop(self) -> None:
        """
        定期的に古いセッションをクリーンアップするループ
        """
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_inactive_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"セッションクリーンアップエラー: {e}")
    
    async def _cleanup_inactive_sessions(self) -> None:
        """
        非アクティブなセッションをクリーンアップします
        """
        now = time.time()
        
        # タイムアウトしたセッションのIDを収集
        timeout_sessions = [
            session_id for session_id, session in self.sessions.items()
            if now - session.last_activity > self.session_timeout
        ]
        
        # タイムアウトしたセッションを閉じる
        for session_id in timeout_sessions:
            logger.info(f"セッション {session_id} はタイムアウトしました。クローズします。")
            await self.close_session(session_id)
    
    def get_active_browsers(self) -> List[Dict[str, Any]]:
        """
        アクティブなブラウザセッションの一覧を返します
        
        Returns:
            List[Dict[str, Any]]: セッション情報のリスト
        """
        return [
            {
                "session_id": session_id,
                "last_activity": session.last_activity,
                "metadata": session.metadata,
                "is_default": session_id == self.default_session_id
            }
            for session_id, session in self.sessions.items()
        ]
    
    async def cleanup(self) -> None:
        """
        すべてのリソースをクリーンアップします
        """
        logger.info("ブラウザコントローラーのクリーンアップを実行...")
        
        # クリーンアップタスクを停止
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            
        # すべてのセッションを閉じる
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            await self.close_session(session_id)
            
        logger.info("すべてのブラウザセッションを閉じました") 
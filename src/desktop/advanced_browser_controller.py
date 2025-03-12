"""
高度なブラウザ操作を制御するモジュール。
Playwrightを使用して、AIエージェントがウェブサイトにアクセスするための機能を提供します。
browser-useライブラリの機能を統合しています。
"""

import os
import asyncio
import logging
import yaml
import urllib.parse
import time
from pathlib import Path
from typing import Dict, Optional, List, Union, Any, Tuple

# Playwrightのインポート
from playwright.async_api import async_playwright, Browser, Page, BrowserContext, Playwright

logger = logging.getLogger(__name__)

class AdvancedBrowserController:
    """Playwrightを使用した高度なブラウザ操作を提供するクラス"""
    
    def __init__(self, config_path: str = None, headless: bool = False):
        """
        高度なブラウザコントローラの初期化
        
        Args:
            config_path: 設定ファイルのパス。指定がない場合はデフォルトを使用
            headless: ヘッドレスモードで実行するかどうか
        """
        self.browsers = {}
        self.default_browser = None
        self.config_path = config_path or Path(__file__).resolve().parents[2] / 'config.yaml'
        self.headless = headless
        self.load_browser_config()
        
        # Playwrightの状態管理
        self.playwright = None
        self.browser_instance = None
        self.context = None
        self.page = None
        
        logger.info("高度なブラウザコントローラが初期化されました")
    
    def load_browser_config(self) -> None:
        """設定ファイルからブラウザ情報を読み込む"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if 'browser_paths' in config:
                self.browsers = config['browser_paths']
                # デフォルトブラウザを設定（最初のブラウザ）
                if self.browsers:
                    self.default_browser = list(self.browsers.keys())[0]
                    logger.info(f"デフォルトブラウザを設定しました: {self.default_browser}")
            else:
                logger.warning("設定ファイルにブラウザの設定がありません")
        except Exception as e:
            logger.error(f"ブラウザ設定の読み込みに失敗しました: {str(e)}")
    
    async def initialize(self) -> None:
        """Playwrightとブラウザを初期化する"""
        if self.playwright is None:
            self.playwright = await async_playwright().start()
            logger.info("Playwrightを初期化しました")
        
        if self.browser_instance is None:
            self.browser_instance = await self.playwright.chromium.launch(
                headless=self.headless
            )
            logger.info(f"ブラウザを起動しました（ヘッドレス: {self.headless}）")
        
        if self.context is None:
            self.context = await self.browser_instance.new_context()
            logger.info("新しいブラウザコンテキストを作成しました")
        
        if self.page is None:
            self.page = await self.context.new_page()
            logger.info("新しいページを作成しました")
    
    async def close(self) -> None:
        """ブラウザとPlaywrightを閉じる"""
        if self.page:
            await self.page.close()
            self.page = None
            logger.info("ページを閉じました")
        
        if self.context:
            await self.context.close()
            self.context = None
            logger.info("コンテキストを閉じました")
        
        if self.browser_instance:
            await self.browser_instance.close()
            self.browser_instance = None
            logger.info("ブラウザを閉じました")
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
            logger.info("Playwrightを停止しました")
    
    async def navigate(self, url: str) -> bool:
        """
        指定されたURLに移動する
        
        Args:
            url: 移動先のURL
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            await self.initialize()
            
            # URLにスキームがない場合は追加
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            await self.page.goto(url)
            logger.info(f"URLに移動しました: {url}")
            return True
        except Exception as e:
            logger.error(f"URL移動エラー: {str(e)}")
            return False
    
    async def search_on_youtube(self, query: str) -> bool:
        """
        YouTubeで検索を実行
        
        Args:
            query: 検索クエリ
            
        Returns:
            bool: 成功したかどうか
        """
        encoded_query = urllib.parse.quote(query)
        youtube_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        logger.info(f"YouTubeで検索します: '{query}'")
        return await self.navigate(youtube_url)
    
    async def search_on_google(self, query: str) -> bool:
        """
        Googleで検索を実行
        
        Args:
            query: 検索クエリ
            
        Returns:
            bool: 成功したかどうか
        """
        encoded_query = urllib.parse.quote(query)
        google_url = f"https://www.google.com/search?q={encoded_query}"
        logger.info(f"Googleで検索します: '{query}'")
        return await self.navigate(google_url)
    
    async def open_gmail(self) -> bool:
        """
        Gmailを開く
        
        Returns:
            bool: 成功したかどうか
        """
        return await self.navigate("https://mail.google.com")
    
    async def open_calendar(self) -> bool:
        """
        Googleカレンダーを開く
        
        Returns:
            bool: 成功したかどうか
        """
        return await self.navigate("https://calendar.google.com")
    
    async def click_element(self, selector: str) -> bool:
        """
        指定されたセレクタの要素をクリックする
        
        Args:
            selector: CSSセレクタ
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            await self.initialize()
            await self.page.click(selector)
            logger.info(f"要素をクリックしました: {selector}")
            return True
        except Exception as e:
            logger.error(f"要素クリックエラー: {str(e)}")
            return False
    
    async def fill_form(self, selector: str, text: str) -> bool:
        """
        指定されたセレクタのフォームに文字を入力する
        
        Args:
            selector: CSSセレクタ
            text: 入力するテキスト
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            await self.initialize()
            await self.page.fill(selector, text)
            logger.info(f"フォームに入力しました: {selector} -> {text}")
            return True
        except Exception as e:
            logger.error(f"フォーム入力エラー: {str(e)}")
            return False
    
    async def get_text(self, selector: str) -> Optional[str]:
        """
        指定されたセレクタの要素のテキストを取得する
        
        Args:
            selector: CSSセレクタ
            
        Returns:
            Optional[str]: 取得したテキスト、失敗した場合はNone
        """
        try:
            await self.initialize()
            text = await self.page.text_content(selector)
            logger.info(f"テキストを取得しました: {selector} -> {text[:50]}...")
            return text
        except Exception as e:
            logger.error(f"テキスト取得エラー: {str(e)}")
            return None
    
    async def take_screenshot(self, path: str) -> bool:
        """
        スクリーンショットを撮影する
        
        Args:
            path: 保存先のパス
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            await self.initialize()
            await self.page.screenshot(path=path)
            logger.info(f"スクリーンショットを撮影しました: {path}")
            return True
        except Exception as e:
            logger.error(f"スクリーンショット撮影エラー: {str(e)}")
            return False
    
    async def execute_javascript(self, script: str) -> Any:
        """
        JavaScriptを実行する
        
        Args:
            script: 実行するJavaScriptコード
            
        Returns:
            Any: JavaScriptの実行結果
        """
        try:
            await self.initialize()
            result = await self.page.evaluate(script)
            logger.info(f"JavaScriptを実行しました: {script[:50]}...")
            return result
        except Exception as e:
            logger.error(f"JavaScript実行エラー: {str(e)}")
            return None
    
    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> bool:
        """
        指定されたセレクタの要素が表示されるまで待機する
        
        Args:
            selector: CSSセレクタ
            timeout: タイムアウト（ミリ秒）
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            await self.initialize()
            await self.page.wait_for_selector(selector, timeout=timeout)
            logger.info(f"要素の表示を待機しました: {selector}")
            return True
        except Exception as e:
            logger.error(f"要素待機エラー: {str(e)}")
            return False
    
    async def get_page_content(self) -> Optional[str]:
        """
        現在のページのHTMLコンテンツを取得する
        
        Returns:
            Optional[str]: HTMLコンテンツ、失敗した場合はNone
        """
        try:
            await self.initialize()
            content = await self.page.content()
            logger.info(f"ページコンテンツを取得しました: {len(content)} バイト")
            return content
        except Exception as e:
            logger.error(f"ページコンテンツ取得エラー: {str(e)}")
            return None
    
    def get_available_browsers(self) -> List[str]:
        """
        利用可能なブラウザのリストを取得
        
        Returns:
            List[str]: ブラウザのリスト
        """
        return list(self.browsers.keys())
    
    def set_default_browser(self, browser_name: str) -> bool:
        """
        デフォルトブラウザを設定
        
        Args:
            browser_name: ブラウザ名
            
        Returns:
            bool: 成功したかどうか
        """
        if browser_name in self.browsers:
            self.default_browser = browser_name
            logger.info(f"デフォルトブラウザを設定しました: {browser_name}")
            return True
        else:
            logger.warning(f"指定されたブラウザ '{browser_name}' は設定されていません")
            return False
    
    # 従来のブラウザ操作メソッド（非同期ではない）
    def open_browser(self, url: str, browser_name: str = None) -> bool:
        """
        指定されたURLをブラウザで開く（従来のメソッド）
        
        Args:
            url: 開くURL
            browser_name: 使用するブラウザ名。指定がない場合はデフォルトブラウザを使用
            
        Returns:
            bool: 成功したかどうか
        """
        # ブラウザが指定されていない場合はデフォルトを使用
        browser_to_use = browser_name or self.default_browser
        
        if not browser_to_use or browser_to_use not in self.browsers:
            logger.warning(f"指定されたブラウザ '{browser_to_use}' は設定されていません。システムのデフォルトブラウザを使用します。")
            try:
                # 非同期関数を同期的に実行
                asyncio.run(self.navigate(url))
                logger.info(f"Playwrightでブラウザを開きました: {url}")
                return True
            except Exception as e:
                logger.error(f"ブラウザでURLを開けませんでした: {str(e)}")
                return False
        
        # 設定されたブラウザのパスを使用
        browser_path = self.browsers[browser_to_use]
        if not os.path.exists(browser_path):
            logger.error(f"ブラウザが見つかりません: {browser_path}")
            return False
        
        try:
            # 従来の方法でブラウザを起動
            import subprocess
            subprocess.Popen([browser_path, url])
            logger.info(f"ブラウザ '{browser_to_use}' でURLを開きました: {url}")
            return True
        except Exception as e:
            logger.error(f"ブラウザでURLを開けませんでした: {str(e)}")
            return False
    
    def play_youtube_video(self, video_query: str, browser_name: str = None) -> bool:
        """
        YouTubeで動画を検索して再生（従来のメソッド）
        
        Args:
            video_query: 動画のクエリ
            browser_name: 使用するブラウザ名
            
        Returns:
            bool: 成功したかどうか
        """
        encoded_query = urllib.parse.quote(video_query)
        youtube_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        logger.info(f"YouTubeで検索します: '{video_query}'")
        return self.open_browser(youtube_url, browser_name) 
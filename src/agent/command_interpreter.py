import re
from typing import Dict, Any, Tuple, Optional, List
import logging
import pyautogui
import keyboard
import time
import cv2
import subprocess
import threading
import os
import asyncio

from .keyboard_monitor import KeyboardMonitor
from ..desktop.browser_controller import BrowserController
from browser_use import Browser

class CommandInterpreter:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.keyboard_monitor = KeyboardMonitor()
        self.command_buffer = []
        self.is_recording = False
        
        # 従来のブラウザコントローラー（後方互換性用）
        self.browser_controller = BrowserController()
        
        # 新しいbrowser-useのブラウザインスタンス
        self.browser = None
        self.browser_loop = None
        
        # コマンドパターンを定義
        self.command_patterns = [
            # ブラウザ関連コマンド
            (r'(ブラウザ|browser)(\s*で|\s*を)?(.+)(を)?(開く|開いて|見る|表示)', self._open_browser),
            (r'(youtube|ユーチューブ)(\s*で|\s*を)?(.+)(を)?(検索|見る|開く|再生)', self._search_youtube),
            (r'(google|グーグル)(\s*で|\s*を)?(.+)(を)?(検索|調べる)', self._search_google),
            (r'(gmail|メール)(を)?(開く|開いて|見る|表示)', self._open_gmail),
            (r'(カレンダー|calendar)(を)?(開く|開いて|見る|表示)', self._open_calendar),
            
            # 高度なブラウザ操作コマンド
            (r'(ブラウザ|browser)(を|で)?要素(.+)(を)?(クリック|押す|タップ)', self._click_element),
            (r'(ブラウザ|browser)(を|で)?スクリーンショット(を)?(撮る|撮影|取る)', self._take_screenshot),
            
            # システム関連コマンド
            (r'(音量|ボリューム)(を)?(上げる|アップ|大きく)', self._volume_up),
            (r'(音量|ボリューム)(を)?(下げる|ダウン|小さく)', self._volume_down),
            (r'(音|サウンド)(を)?(ミュート|消す)', self._mute),
        ]

    def start_monitoring(self):
        """キーボードの監視を開始"""
        self.keyboard_monitor.start(self._on_key_press)

    def stop_monitoring(self):
        """キーボードの監視を停止"""
        self.keyboard_monitor.stop()

    def _on_key_press(self, key: str):
        """キー入力時のコールバック"""
        if self.is_recording:
            self.command_buffer.append(key)

    def start_recording(self):
        """コマンドの記録を開始"""
        self.is_recording = True
        self.command_buffer.clear()

    def stop_recording(self) -> str:
        """コマンドの記録を停止し、記録されたコマンドを返す"""
        self.is_recording = False
        command = ''.join(self.command_buffer)
        self.command_buffer.clear()
        return command
    
    def initialize_browser(self):
        """browser-useのブラウザを初期化"""
        if self.browser is None:
            self.browser_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.browser_loop)
            
            def init_browser():
                self.browser = Browser(headless=False)
                self.logger.info("browser-useブラウザインスタンスを初期化しました")
            
            # 非同期で初期化を実行
            if threading.current_thread() is threading.main_thread():
                self.browser_loop.run_until_complete(init_browser())
            else:
                # 別スレッドから呼ばれた場合
                threading.Thread(target=lambda: self.browser_loop.run_until_complete(init_browser())).start()

    def parse_command(self, command_text: str) -> Tuple[bool, str]:
        """
        テキストコマンドを解析して適切な関数を呼び出す
        
        Args:
            command_text: コマンドテキスト
            
        Returns:
            Tuple[bool, str]: (成功したかどうか, 結果または詳細メッセージ)
        """
        for pattern, handler in self.command_patterns:
            match = re.search(pattern, command_text, re.IGNORECASE)
            if match:
                self.logger.info(f"コマンドマッチ: '{command_text}' -> {pattern}")
                try:
                    result = handler(match, command_text)
                    return result
                except Exception as e:
                    self.logger.error(f"コマンド実行エラー: {e}")
                    return False, f"コマンド実行中にエラーが発生しました: {str(e)}"
        
        self.logger.warning(f"認識できないコマンド: '{command_text}'")
        return False, f"コマンド '{command_text}' を認識できませんでした"
    
    def execute_command(self, command: str) -> bool:
        """コマンドを実行"""
        success, message = self.parse_command(command)
        self.logger.info(f"コマンド実行結果: {success}, {message}")
        return success
    
    def _run_browser_async(self, coro):
        """browser-useの非同期関数を実行するヘルパーメソッド"""
        self.initialize_browser()
        
        # 実行するコルーチン
        async def run_and_return():
            try:
                return await coro
            except Exception as e:
                self.logger.error(f"ブラウザ操作エラー: {e}")
                return False
        
        # メインスレッドかどうかで実行方法を変える
        if threading.current_thread() is threading.main_thread():
            return self.browser_loop.run_until_complete(run_and_return())
        else:
            # 別スレッドの場合は結果を受け取るための仕組みを作る
            result = [None]
            def run_async():
                result[0] = self.browser_loop.run_until_complete(run_and_return())
            
            thread = threading.Thread(target=run_async)
            thread.start()
            thread.join()
            return result[0]
    
    # ブラウザ関連ハンドラ (browser-useを使用)
    def _open_browser(self, match, command_text: str) -> Tuple[bool, str]:
        """ブラウザを開くコマンドを処理 (browser-useを使用)"""
        url = match.group(3).strip()
        # URLにスキームがない場合は追加
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        try:
            # browser-useを使用
            success = self._run_browser_async(self.browser.navigate(url))
            if success:
                message = f"ブラウザで {url} を開きました"
                return True, message
            
            # browser-useが失敗した場合、従来のコントローラーを使用
            self.logger.info("browser-useによる操作が失敗しました。従来のコントローラーを使用します。")
            success = self.browser_controller.open_browser(url)
            message = f"ブラウザで {url} を開き" + ("ました" if success else "ませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"ブラウザ操作エラー: {e}")
            return False, f"ブラウザ操作中にエラーが発生しました: {str(e)}"
    
    def _search_youtube(self, match, command_text: str) -> Tuple[bool, str]:
        """YouTubeで検索するコマンドを処理 (browser-useを使用)"""
        query = match.group(3).strip()
        
        try:
            # browser-useを使用して検索
            search_function = self.browser.search_youtube if hasattr(self.browser, 'search_youtube') else self.browser.youtube
            success = self._run_browser_async(search_function(query))
            if success:
                message = f"YouTubeで '{query}' を検索しました"
                return True, message
                
            # 失敗した場合は従来のコントローラーを使用
            success = self.browser_controller.search_on_youtube(query)
            message = f"YouTubeで '{query}' を検索し" + ("ました" if success else "ませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"YouTube検索エラー: {e}")
            return False, f"YouTube検索中にエラーが発生しました: {str(e)}"
    
    def _search_google(self, match, command_text: str) -> Tuple[bool, str]:
        """Googleで検索するコマンドを処理 (browser-useを使用)"""
        query = match.group(3).strip()
        
        try:
            # browser-useを使用して検索
            search_function = self.browser.search_google if hasattr(self.browser, 'search_google') else self.browser.google
            success = self._run_browser_async(search_function(query))
            if success:
                message = f"Googleで '{query}' を検索しました"
                return True, message
                
            # 失敗した場合は従来のコントローラーを使用
            success = self.browser_controller.search_on_google(query)
            message = f"Googleで '{query}' を検索し" + ("ました" if success else "ませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"Google検索エラー: {e}")
            return False, f"Google検索中にエラーが発生しました: {str(e)}"
    
    def _open_gmail(self, match, command_text: str) -> Tuple[bool, str]:
        """Gmailを開くコマンドを処理 (browser-useを使用)"""
        try:
            # browser-useを使用
            success = self._run_browser_async(self.browser.navigate("https://mail.google.com"))
            if success:
                message = "Gmailを開きました"
                return True, message
                
            # 失敗した場合は従来のコントローラーを使用
            success = self.browser_controller.open_gmail()
            message = "Gmailを開き" + ("ました" if success else "ませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"Gmail操作エラー: {e}")
            return False, f"Gmail操作中にエラーが発生しました: {str(e)}"
    
    def _open_calendar(self, match, command_text: str) -> Tuple[bool, str]:
        """カレンダーを開くコマンドを処理 (browser-useを使用)"""
        try:
            # browser-useを使用
            success = self._run_browser_async(self.browser.navigate("https://calendar.google.com"))
            if success:
                message = "カレンダーを開きました"
                return True, message
                
            # 失敗した場合は従来のコントローラーを使用
            success = self.browser_controller.open_calendar()
            message = "カレンダーを開き" + ("ました" if success else "ませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"カレンダー操作エラー: {e}")
            return False, f"カレンダー操作中にエラーが発生しました: {str(e)}"
    
    # 高度なブラウザ操作コマンド (browser-useでのみ実装)
    def _click_element(self, match, command_text: str) -> Tuple[bool, str]:
        """要素をクリックするコマンドを処理"""
        selector = match.group(3).strip()
        
        try:
            # セレクタの前処理
            if not selector.startswith(('#', '.', '[', '/')):
                # 単純なテキストの場合は、テキストを含む要素を探す
                selector = f"//*[contains(text(), '{selector}')]"
            
            # browser-useを使用して要素をクリック
            success = self._run_browser_async(self.browser.click(selector))
            message = f"要素 '{selector}' を" + ("クリックしました" if success else "クリックできませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"要素クリックエラー: {e}")
            return False, f"要素クリック中にエラーが発生しました: {str(e)}"
    
    def _take_screenshot(self, match, command_text: str) -> Tuple[bool, str]:
        """スクリーンショットを撮るコマンドを処理"""
        try:
            # スクリーンショットの保存先
            now = time.strftime("%Y%m%d_%H%M%S")
            screenshot_dir = os.path.join(os.path.expanduser("~"), "Documents", "DesktopAgent", "Screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshot_dir, f"screenshot_{now}.png")
            
            # browser-useを使用してスクリーンショット撮影
            success = self._run_browser_async(self.browser.screenshot(screenshot_path))
            message = f"スクリーンショットを" + (f"{screenshot_path}に保存しました" if success else "保存できませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"スクリーンショットエラー: {e}")
            return False, f"スクリーンショット撮影中にエラーが発生しました: {str(e)}"
    
    # システム関連ハンドラ
    def _volume_up(self, match, command_text: str) -> Tuple[bool, str]:
        """音量を上げるコマンドを処理"""
        try:
            # 音量を上げる（Windows）
            for _ in range(5):  # 5段階上げる
                pyautogui.press('volumeup')
            return True, "音量を上げました"
        except Exception as e:
            self.logger.error(f"音量調整エラー: {e}")
            return False, f"音量を上げられませんでした: {str(e)}"
    
    def _volume_down(self, match, command_text: str) -> Tuple[bool, str]:
        """音量を下げるコマンドを処理"""
        try:
            # 音量を下げる（Windows）
            for _ in range(5):  # 5段階下げる
                pyautogui.press('volumedown')
            return True, "音量を下げました"
        except Exception as e:
            self.logger.error(f"音量調整エラー: {e}")
            return False, f"音量を下げられませんでした: {str(e)}"
    
    def _mute(self, match, command_text: str) -> Tuple[bool, str]:
        """ミュートするコマンドを処理"""
        try:
            # ミュート（Windows）
            pyautogui.press('volumemute')
            return True, "ミュートしました"
        except Exception as e:
            self.logger.error(f"ミュートエラー: {e}")
            return False, f"ミュートできませんでした: {str(e)}"
    
    def get_available_browsers(self) -> List[str]:
        """利用可能なブラウザのリストを取得"""
        return self.browser_controller.get_available_browsers()

    def close_browser(self):
        """browser-useのブラウザを閉じる"""
        if self.browser is not None:
            try:
                # 非同期関数を同期的に実行
                if self.browser_loop:
                    self.browser_loop.run_until_complete(self.browser.close())
                self.logger.info("browser-useブラウザインスタンスを閉じました")
            except Exception as e:
                self.logger.error(f"ブラウザを閉じる際にエラーが発生しました: {e}")
            finally:
                self.browser = None
                
        if self.browser_loop is not None:
            try:
                self.browser_loop.close()
            except Exception:
                pass
            finally:
                self.browser_loop = None

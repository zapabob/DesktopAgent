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

from .keyboard_monitor import KeyboardMonitor
from ..desktop.browser_controller import BrowserController

class CommandInterpreter:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.keyboard_monitor = KeyboardMonitor()
        self.command_buffer = []
        self.is_recording = False
        self.browser_controller = BrowserController()
        
        # コマンドパターンを定義
        self.command_patterns = [
            # ブラウザ関連コマンド
            (r'(ブラウザ|browser)(\s*で|\s*を)?(.+)(を)?(開く|開いて|見る|表示)', self._open_browser),
            (r'(youtube|ユーチューブ)(\s*で|\s*を)?(.+)(を)?(検索|見る|開く|再生)', self._search_youtube),
            (r'(google|グーグル)(\s*で|\s*を)?(.+)(を)?(検索|調べる)', self._search_google),
            (r'(gmail|メール)(を)?(開く|開いて|見る|表示)', self._open_gmail),
            (r'(カレンダー|calendar)(を)?(開く|開いて|見る|表示)', self._open_calendar),
            
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
    
    # ブラウザ関連ハンドラ
    def _open_browser(self, match, command_text: str) -> Tuple[bool, str]:
        """ブラウザを開くコマンドを処理"""
        url = match.group(3).strip()
        # URLにスキームがない場合は追加
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        success = self.browser_controller.open_browser(url)
        message = f"ブラウザで {url} を開き" + ("ました" if success else "ませんでした")
        return success, message
    
    def _search_youtube(self, match, command_text: str) -> Tuple[bool, str]:
        """YouTubeで検索するコマンドを処理"""
        query = match.group(3).strip()
        success = self.browser_controller.search_on_youtube(query)
        message = f"YouTubeで '{query}' を検索し" + ("ました" if success else "ませんでした")
        return success, message
    
    def _search_google(self, match, command_text: str) -> Tuple[bool, str]:
        """Googleで検索するコマンドを処理"""
        query = match.group(3).strip()
        success = self.browser_controller.search_on_google(query)
        message = f"Googleで '{query}' を検索し" + ("ました" if success else "ませんでした")
        return success, message
    
    def _open_gmail(self, match, command_text: str) -> Tuple[bool, str]:
        """Gmailを開くコマンドを処理"""
        success = self.browser_controller.open_gmail()
        message = "Gmailを開き" + ("ました" if success else "ませんでした")
        return success, message
    
    def _open_calendar(self, match, command_text: str) -> Tuple[bool, str]:
        """カレンダーを開くコマンドを処理"""
        success = self.browser_controller.open_calendar()
        message = "カレンダーを開き" + ("ました" if success else "ませんでした")
        return success, message
    
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

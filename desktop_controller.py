import os
import sys
import logging
import pyautogui
import keyboard
import mouse
import psutil
import time
from typing import Optional, Dict, Tuple, List, Union
from pathlib import Path
from datetime import datetime
import win32gui
import win32con

class CursorCommands:
    """Cursorのコマンド定義"""
    TOGGLE_COMMAND_BAR = "ctrl+shift+p"  # コマンドバーの表示/非表示
    TOGGLE_COPILOT = "ctrl+shift+i"      # Copilotの表示/非表示
    ACCEPT_SUGGESTION = "tab"            # 提案を受け入れ
    NEXT_SUGGESTION = "alt+]"            # 次の提案へ
    PREV_SUGGESTION = "alt+["            # 前の提案へ
    TRIGGER_INLINE_CHAT = "ctrl+i"       # インラインチャットの起動
    TRIGGER_COMPLETION = "ctrl+space"    # 補完の手動トリガー

class DesktopController:
    """デスクトップ操作を制御するクラス"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 安全設定
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        
        # 画面サイズの取得
        self.screen_width, self.screen_height = pyautogui.size()
        
        # 状態の初期化
        self.is_active = False
        self.last_position = (0, 0)
        self.active_window = None
        
        # Cursor関連の状態
        self.is_cursor_focused = False
        self.last_cursor_command = None
        self.completion_active = False
    
    def start(self):
        """制御の開始"""
        if not self.is_active:
            self.is_active = True
            self.logger.info("デスクトップ制御を開始")
    
    def stop(self):
        """制御の停止"""
        if self.is_active:
            self.is_active = False
            self.logger.info("デスクトップ制御を停止")
    
    def move_mouse(self, x: int, y: int, duration: float = 0.5):
        """マウスを移動"""
        try:
            if self.is_active:
                pyautogui.moveTo(x, y, duration=duration)
                self.last_position = (x, y)
        except Exception as e:
            self.logger.error(f"マウス移動エラー: {e}")
    
    def click(self, x: Optional[int] = None, y: Optional[int] = None):
        """クリック操作"""
        try:
            if self.is_active:
                if x is not None and y is not None:
                    pyautogui.click(x, y)
                else:
                    pyautogui.click()
        except Exception as e:
            self.logger.error(f"クリックエラー: {e}")
    
    def type_text(self, text: str, interval: float = 0.1):
        """テキストを入力"""
        try:
            if self.is_active:
                pyautogui.typewrite(text, interval=interval)
        except Exception as e:
            self.logger.error(f"テキスト入力エラー: {e}")
    
    def press_key(self, key: str):
        """キーを押下"""
        try:
            if self.is_active:
                pyautogui.press(key)
        except Exception as e:
            self.logger.error(f"キー押下エラー: {e}")
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """マウス位置を取得"""
        return pyautogui.position()
    
    def get_active_window(self) -> Optional[str]:
        """アクティブウィンドウを取得"""
        try:
            window = win32gui.GetForegroundWindow()
            return win32gui.GetWindowText(window)
        except Exception as e:
            self.logger.error(f"ウィンドウ取得エラー: {e}")
            return None
    
    def take_screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[str]:
        """スクリーンショットを撮影"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()
            
            save_path = Path("screenshots") / filename
            save_path.parent.mkdir(exist_ok=True)
            screenshot.save(save_path)
            
            return str(save_path)
            
        except Exception as e:
            self.logger.error(f"スクリーンショットエラー: {e}")
            return None
    
    def find_image(self, image_path: str, confidence: float = 0.9) -> Optional[Tuple[int, int]]:
        """画像を検索"""
        try:
            location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
            return location if location else None
        except Exception as e:
            self.logger.error(f"画像検索エラー: {e}")
            return None
    
    def get_system_metrics(self) -> Dict[str, float]:
        """システムメトリクスを取得"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "disk_usage": disk.percent
            }
        except Exception as e:
            self.logger.error(f"システムメトリクス取得エラー: {e}")
            return {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "disk_usage": 0.0
            }
    
    def list_windows(self) -> List[str]:
        """ウィンドウ一覧を取得"""
        try:
            return [win.title for win in pyautogui.getAllWindows()]
        except Exception as e:
            self.logger.error(f"ウィンドウ一覧取得エラー: {e}")
            return []
    
    def focus_window(self, window_title: str) -> bool:
        """ウィンドウにフォーカス"""
        try:
            def callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    window_title = win32gui.GetWindowText(hwnd)
                    if window_title.lower() == window_title.lower():
                        windows.append(hwnd)
            
            windows = []
            win32gui.EnumWindows(callback, windows)
            
            if windows:
                win32gui.SetForegroundWindow(windows[0])
                self.active_window = windows[0]
                return True
            return False
        except Exception as e:
            self.logger.error(f"ウィンドウフォーカスエラー: {e}")
            return False
    
    def send_prompt_to_chatgpt(self, prompt: str) -> bool:
        """ChatGPTにプロンプトを送信"""
        try:
            # ChatGPTウィンドウを探してフォーカス
            if not self.focus_window("ChatGPT"):
                self.logger.error("ChatGPTウィンドウが見つかりません")
                return False
            
            time.sleep(1)  # UIの読み込みを待機
            
            # Ctrl+Aで既存のテキストを選択
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.5)
            
            # プロンプトを入力
            self.type_text(prompt)
            time.sleep(0.5)
            
            # Enterキーを押して送信
            self.press_key("enter")
            
            self.logger.info(f"ChatGPTにプロンプトを送信: {prompt[:50]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"ChatGPT操作エラー: {e}")
            return False

    def focus_cursor(self) -> bool:
        """Cursorウィンドウにフォーカス"""
        return self.focus_window("Cursor")

    def send_cursor_command(self, command: str) -> bool:
        """Cursorにコマンドを送信"""
        try:
            if not self.is_active:
                return False

            if not self.is_cursor_focused:
                if not self.focus_cursor():
                    self.logger.error("Cursorウィンドウが見つかりません")
                    return False
                self.is_cursor_focused = True
                time.sleep(0.5)

            # コマンドのキー組み合わせを送信
            pyautogui.hotkey(*command.split('+'))
            self.last_cursor_command = command
            self.logger.info(f"Cursorコマンドを送信: {command}")
            return True

        except Exception as e:
            self.logger.error(f"Cursorコマンド送信エラー: {e}")
            return False

    def trigger_completion(self) -> bool:
        """コード補完をトリガー"""
        return self.send_cursor_command(CursorCommands.TRIGGER_COMPLETION)

    def accept_suggestion(self) -> bool:
        """現在の提案を受け入れ"""
        return self.send_cursor_command(CursorCommands.ACCEPT_SUGGESTION)

    def next_suggestion(self) -> bool:
        """次の提案に移動"""
        return self.send_cursor_command(CursorCommands.NEXT_SUGGESTION)

    def prev_suggestion(self) -> bool:
        """前の提案に移動"""
        return self.send_cursor_command(CursorCommands.PREV_SUGGESTION)

    def toggle_copilot(self) -> bool:
        """Copilotパネルの表示/非表示を切り替え"""
        return self.send_cursor_command(CursorCommands.TOGGLE_COPILOT)

    def trigger_inline_chat(self) -> bool:
        """インラインチャットを起動"""
        return self.send_cursor_command(CursorCommands.TRIGGER_INLINE_CHAT)

    def assist_coding(self, code_context: str, wait_time: float = 1.0) -> bool:
        """コーディング支援を実行"""
        try:
            if not self.is_active:
                return False

            # Cursorにフォーカス
            if not self.focus_cursor():
                return False

            # コンテキストの入力
            self.type_text(code_context)
            time.sleep(0.5)

            # 補完をトリガー
            self.trigger_completion()
            time.sleep(wait_time)  # 提案を待つ

            # 提案を受け入れ
            self.accept_suggestion()

            self.logger.info("コーディング支援を実行しました")
            return True

        except Exception as e:
            self.logger.error(f"コーディング支援エラー: {e}")
            return False

    def request_code_review(self, file_path: Union[str, Path]) -> bool:
        """コードレビューを要求"""
        try:
            if not self.is_active:
                return False

            # Cursorにフォーカス
            if not self.focus_cursor():
                return False

            # Copilotパネルを表示
            self.toggle_copilot()
            time.sleep(0.5)

            # レビュー要求を入力
            review_request = f"Please review the code in {file_path} and suggest improvements."
            self.type_text(review_request)
            self.press_key("enter")

            self.logger.info(f"コードレビューを要求: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"コードレビュー要求エラー: {e}")
            return False 
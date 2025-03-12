import pyautogui
import keyboard
import win32gui
import win32con
import win32api
import cv2
import numpy as np
from PIL import ImageGrab
from typing import Tuple, Optional, List, Dict, Any
import json
import logging
from pathlib import Path
import asyncio
import win32process
import psutil
from PIL import Image
import io
from datetime import datetime

class DesktopTools:
    """デスクトップ操作ツールセット"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.screenshot_dir = Path("screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # 安全設定
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        
    async def take_screenshot(self, region: Optional[Tuple[int, int, int, int]] = None,
                            save_path: Optional[str] = None) -> str:
        """スクリーンショットの取得"""
        try:
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()
                
            if save_path:
                path = Path(save_path)
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = self.screenshot_dir / f"screenshot_{timestamp}.png"
                
            screenshot.save(path)
            return str(path)
            
        except Exception as e:
            self.logger.error(f"スクリーンショットエラー: {e}")
            raise
            
    async def find_image_on_screen(self, template_path: str,
                                 confidence: float = 0.8) -> Optional[Tuple[int, int]]:
        """画面上の画像検索"""
        try:
            # テンプレート画像の読み込み
            template = cv2.imread(template_path)
            if template is None:
                raise ValueError(f"テンプレート画像が読み込めません: {template_path}")
                
            # スクリーンショットの取得と変換
            screenshot = pyautogui.screenshot()
            screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # テンプレートマッチング
            result = cv2.matchTemplate(screenshot, template,
                                     cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= confidence:
                return max_loc
            return None
            
        except Exception as e:
            self.logger.error(f"画像検索エラー: {e}")
            raise
            
    async def click_image(self, template_path: str, confidence: float = 0.8,
                         clicks: int = 1, button: str = "left") -> bool:
        """画像の位置をクリック"""
        try:
            location = await self.find_image_on_screen(template_path, confidence)
            if location:
                x, y = location
                pyautogui.click(x, y, clicks=clicks, button=button)
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"画像クリックエラー: {e}")
            raise
            
    async def type_text(self, text: str, interval: float = 0.1) -> None:
        """テキストの入力"""
        try:
            pyautogui.write(text, interval=interval)
        except Exception as e:
            self.logger.error(f"テキスト入力エラー: {e}")
            raise
            
    async def press_hotkey(self, *keys: str) -> None:
        """ホットキーの入力"""
        try:
            pyautogui.hotkey(*keys)
        except Exception as e:
            self.logger.error(f"ホットキー入力エラー: {e}")
            raise
            
    async def get_active_window_info(self) -> Dict[str, Any]:
        """アクティブウィンドウの情報取得"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            
            return {
                "title": win32gui.GetWindowText(hwnd),
                "process_name": process.name(),
                "pid": pid,
                "rect": win32gui.GetWindowRect(hwnd)
            }
            
        except Exception as e:
            self.logger.error(f"ウィンドウ情報取得エラー: {e}")
            raise
            
    async def set_window_state(self, title: str,
                             state: str = "normal") -> bool:
        """ウィンドウの状態を設定"""
        try:
            def callback(hwnd, _):
                if win32gui.GetWindowText(hwnd) == title:
                    if state == "minimize":
                        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                    elif state == "maximize":
                        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    elif state == "normal":
                        win32gui.ShowWindow(hwnd, win32con.SW_NORMAL)
                        
            win32gui.EnumWindows(callback, None)
            return True
            
        except Exception as e:
            self.logger.error(f"ウィンドウ状態設定エラー: {e}")
            raise
            
    async def get_window_list(self) -> List[Dict[str, Any]]:
        """ウィンドウ一覧の取得"""
        windows = []
        
        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        process = psutil.Process(pid)
                        windows.append({
                            "title": title,
                            "process_name": process.name(),
                            "pid": pid,
                            "rect": win32gui.GetWindowRect(hwnd)
                        })
                    except Exception:
                        pass
                        
        try:
            win32gui.EnumWindows(callback, None)
            return windows
        except Exception as e:
            self.logger.error(f"ウィンドウ一覧取得エラー: {e}")
            raise
            
    async def start_key_recording(self) -> None:
        """キー入力の記録開始"""
        try:
            self.recorded_keys = []
            keyboard.hook(lambda e: self.recorded_keys.append(e))
        except Exception as e:
            self.logger.error(f"キー記録開始エラー: {e}")
            raise
            
    async def stop_key_recording(self) -> List[Dict[str, Any]]:
        """キー入力の記録停止"""
        try:
            keyboard.unhook_all()
            return self.recorded_keys
        except Exception as e:
            self.logger.error(f"キー記録停止エラー: {e}")
            raise
            
    async def replay_keys(self, recorded_keys: List[Dict[str, Any]],
                         speed: float = 1.0) -> None:
        """記録したキー入力の再生"""
        try:
            for event in recorded_keys:
                if event.event_type == "down":
                    keyboard.press(event.name)
                elif event.event_type == "up":
                    keyboard.release(event.name)
                await asyncio.sleep(event.time / speed)
        except Exception as e:
            self.logger.error(f"キー再生エラー: {e}")
            raise
            
    async def get_screen_text(self, region: Optional[Tuple[int, int, int, int]] = None) -> str:
        """画面上のテキスト認識"""
        try:
            import pytesseract
            
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()
                
            # 画像の前処理
            img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255,
                                   cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                                   
            # テキスト認識
            text = pytesseract.image_to_string(binary, lang="jpn+eng")
            return text.strip()
            
        except Exception as e:
            self.logger.error(f"テキスト認識エラー: {e}")
            raise
            
    async def click_position(self, x: int, y: int, button: str = "left") -> None:
        """指定位置をクリック"""
        try:
            pyautogui.click(x=x, y=y, button=button)
        except Exception as e:
            self.logger.error(f"クリックエラー: {e}")
            raise
            
    async def press_key(self, key: str) -> None:
        """キー入力"""
        try:
            keyboard.press_and_release(key)
        except Exception as e:
            self.logger.error(f"キー入力エラー: {e}")
            raise
            
    async def focus_window(self, title: str) -> bool:
        """ウィンドウのフォーカス"""
        try:
            windows = await self.get_window_list()
            target = next(
                (w for w in windows if title.lower() in w["title"].lower()),
                None
            )
            
            if target:
                hwnd = target["handle"]
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"ウィンドウフォーカスエラー: {e}")
            raise
            
    async def drag_mouse(self, start_x: int, start_y: int,
                      end_x: int, end_y: int, duration: float = 0.5) -> None:
        """マウスドラッグ"""
        try:
            pyautogui.moveTo(start_x, start_y)
            pyautogui.dragTo(end_x, end_y, duration=duration)
        except Exception as e:
            self.logger.error(f"マウスドラッグエラー: {e}")
            raise
            
    async def scroll(self, clicks: int) -> None:
        """スクロール"""
        try:
            pyautogui.scroll(clicks)
        except Exception as e:
            self.logger.error(f"スクロールエラー: {e}")
            raise
            
    async def get_mouse_position(self) -> Tuple[int, int]:
        """マウス位置の取得"""
        try:
            x, y = win32api.GetCursorPos()
            return x, y
        except Exception as e:
            self.logger.error(f"マウス位置取得エラー: {e}")
            raise
            
    def cleanup(self) -> None:
        """クリーンアップ処理"""
        try:
            # スクリーンショットの削除
            for file in self.screenshot_dir.glob("*.png"):
                file.unlink()
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}")
            raise 
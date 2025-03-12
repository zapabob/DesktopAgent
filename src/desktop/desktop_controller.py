import pyautogui
import win32gui
import win32con
import psutil
import logging
from typing import Optional, Dict, Any

class DesktopController:
    def __init__(self, db_logger):
        self.logger = logging.getLogger(__name__)
        self.db_logger = db_logger
        pyautogui.FAILSAFE = True
    
    def minimize_window(self, window_title: str) -> bool:
        """指定したウィンドウを最小化"""
        try:
            def callback(hwnd, window_title):
                if win32gui.IsWindowVisible(hwnd) and window_title.lower() in win32gui.GetWindowText(hwnd).lower():
                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                    return True
                return False
            
            found = win32gui.EnumWindows(lambda hwnd, _: callback(hwnd, window_title), window_title)
            
            if found:
                self.db_logger.log_operation(
                    "DESKTOP_MINIMIZE",
                    f"ウィンドウを最小化: {window_title}",
                    "SUCCESS"
                )
                return True
            else:
                self.logger.warning(f"ウィンドウが見つかりません: {window_title}")
                return False
                
        except Exception as e:
            self.logger.error(f"ウィンドウ最小化エラー: {e}")
            return False
    
    def launch_application(self, app_name: str) -> bool:
        """アプリケーションを起動"""
        try:
            # TODO: アプリケーションパスの解決ロジックを実装
            import subprocess
            subprocess.Popen(app_name)
            
            self.db_logger.log_operation(
                "DESKTOP_LAUNCH",
                f"アプリケーションを起動: {app_name}",
                "SUCCESS"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"アプリケーション起動エラー: {e}")
            return False
    
    def get_system_state(self) -> Dict[str, Any]:
        """システム状態を取得"""
        try:
            cpu_usage = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            active_window = win32gui.GetWindowText(win32gui.GetForegroundWindow())
            
            state = {
                'cpu_usage': cpu_usage,
                'memory_usage': memory.percent,
                'active_window': active_window
            }
            
            self.db_logger.log_system_state(**state)
            return state
            
        except Exception as e:
            self.logger.error(f"システム状態取得エラー: {e}")
            return {} 
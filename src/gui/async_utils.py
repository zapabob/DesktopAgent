import asyncio
import threading
from typing import Callable, Any
from functools import partial
import tkinter as tk
from tkinter import ttk
import logging

class AsyncTkHelper:
    """非同期TkInterヘルパー"""
    def __init__(self, root: tk.Tk):
        self.root = root
        self.loop = asyncio.new_event_loop()
        self.thread = None
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """非同期ループの開始"""
        def run_loop():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
            
        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()
        
    def stop(self):
        """非同期ループの停止"""
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread and self.thread.is_alive():
            self.thread.join()
            
    def create_task(self, coro) -> asyncio.Task:
        """非同期タスクの作成"""
        return asyncio.run_coroutine_threadsafe(coro, self.loop)
        
    def run_async(self, func: Callable, *args, **kwargs):
        """非同期関数の実行"""
        async def wrapper():
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"非同期実行エラー: {e}")
                raise
                
        return self.create_task(wrapper())
        
class AsyncButton(ttk.Button):
    """非同期処理対応ボタン"""
    def __init__(self, master, async_helper: AsyncTkHelper, **kwargs):
        self.async_helper = async_helper
        self.async_command = kwargs.pop("command", None)
        self.progress_var = tk.StringVar(value="")
        self.master = master
        
        # masterからrootを取得
        self.root = master.winfo_toplevel()
        
        super().__init__(master, **kwargs)
        
        if self.async_command:
            self.configure(command=self._handle_click)
            
        # プログレスバーの追加
        self.progress = ttk.Progressbar(
            master,
            mode="indeterminate",
            length=100
        )
        
    def _handle_click(self):
        """クリックイベントの処理"""
        if not self.async_command:
            return
            
        # ボタンを無効化
        self.state(["disabled"])
        self.progress.pack(pady=5)
        self.progress.start()
        
        def done_callback(future):
            try:
                result = future.result()
                if result:
                    self.progress_var.set("完了")
            except Exception as e:
                self.progress_var.set(f"エラー: {e}")
            finally:
                # UIの更新
                self.root.after(0, self._cleanup)
                
        # 非同期処理の実行
        task = self.async_helper.run_async(self.async_command)
        task.add_done_callback(done_callback)
        
    def _cleanup(self):
        """クリーンアップ処理"""
        self.progress.stop()
        self.progress.pack_forget()
        self.state(["!disabled"])
        self.progress_var.set("")
        
class AsyncProgressDialog:
    """非同期処理用プログレスダイアログ"""
    def __init__(self, parent, title: str, message: str):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # ダイアログを中央に配置
        window_width = 300
        window_height = 150
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # メッセージラベル
        self.message_label = ttk.Label(
            self.dialog,
            text=message,
            wraplength=250
        )
        self.message_label.pack(pady=10, padx=20)
        
        # プログレスバー
        self.progress = ttk.Progressbar(
            self.dialog,
            mode="indeterminate",
            length=200
        )
        self.progress.pack(pady=10, padx=20)
        
        # 進捗状況
        self.status_var = tk.StringVar(value="処理中...")
        self.status_label = ttk.Label(
            self.dialog,
            textvariable=self.status_var,
            wraplength=250
        )
        self.status_label.pack(pady=5)
        
        # キャンセルボタン
        self.cancel_button = ttk.Button(
            self.dialog,
            text="キャンセル",
            command=self._on_close
        )
        self.cancel_button.pack(pady=10)
        
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
        self.cancelled = False
        self.task = None
        
    def start(self):
        """プログレス表示の開始"""
        self.progress.start()
        
    def stop(self):
        """プログレス表示の停止"""
        try:
            self.progress.stop()
            if self.task and not self.task.done():
                self.task.cancel()
            self.dialog.destroy()
        except Exception as e:
            logging.error(f"プログレスダイアログ停止エラー: {e}")
            
    def update_status(self, message: str):
        """状態メッセージの更新"""
        self.status_var.set(message)
        
    def set_task(self, task: asyncio.Task):
        """タスクの設定"""
        self.task = task
        
    def _on_close(self):
        """ダイアログのクローズ処理"""
        if not self.cancelled:
            self.cancelled = True
            self.update_status("キャンセル中...")
            self.cancel_button.state(["disabled"])
            self.stop()
            
async def run_with_progress(parent: tk.Tk, title: str, message: str,
                         func: Callable, *args, **kwargs) -> Any:
    """プログレスダイアログ付きで非同期処理を実行"""
    dialog = AsyncProgressDialog(parent, title, message)
    
    try:
        dialog.start()
        task = asyncio.create_task(func(*args, **kwargs))
        dialog.set_task(task)
        
        result = await task
        if dialog.cancelled:
            return None
        return result
        
    except asyncio.CancelledError:
        return None
        
    except Exception as e:
        dialog.update_status(f"エラー: {e}")
        raise
        
    finally:
        dialog.stop() 
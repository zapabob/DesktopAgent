<<<<<<< HEAD
import psutil
import win32gui
import logging
import time
import threading
import queue
from threading import Thread
from typing import Optional, Dict, Any
from db.models import DatabaseManager

class SystemMonitor(Thread):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseManager()
        self.interval = 60
        self.running = False
        self.metrics_queue = queue.Queue()
        
        # メインスレッドでのデータベース更新用スレッド
        self.db_thread = Thread(target=self._process_metrics)
        self.db_thread.daemon = True
    
    def run(self):
        """モニタリングループを実行"""
        self.running = True
        self.db_thread.start()
        
        while self.running:
            try:
                metrics = self._collect_system_metrics()
                self.metrics_queue.put(metrics)
                time.sleep(self.interval)
            except Exception as e:
                self.logger.error(f"システムメトリクス収集エラー: {e}")
    
    def stop(self):
        """モニタリングを停止"""
        self.running = False
        self.metrics_queue.put(None)  # 終了シグナル
        self.db_thread.join()
        self.db_manager.close_all()
    
    def _process_metrics(self):
        """メインスレッドでメトリクスを処理"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        while True:
            metrics = self.metrics_queue.get()
            if metrics is None:  # 終了シグナル
                break
                
            try:
                cursor.execute('''
                INSERT INTO system_state (cpu_usage, memory_usage, active_window)
                VALUES (?, ?, ?)
                ''', (metrics['cpu_usage'], metrics['memory_usage'], metrics['active_window']))
                conn.commit()
            except Exception as e:
                self.logger.error(f"メトリクス記録エラー: {e}")
            
            self.metrics_queue.task_done()
        
        conn.close()
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """システムメトリクスを収集"""
        try:
            # CPU使用率
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # アクティブウィンドウ
            active_window = win32gui.GetWindowText(win32gui.GetForegroundWindow())
            
            # プロセス情報
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # 上位5つのCPU使用プロセスを取得
            top_cpu_processes = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:5]
            
            # メトリクスを返す
            metrics = {
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'active_window': active_window,
                'top_processes': top_cpu_processes
            }
            
            # デバッグ情報を記録
            self.logger.debug(f"CPU使用率: {cpu_usage}%")
            self.logger.debug(f"メモリ使用率: {memory_usage}%")
            self.logger.debug(f"アクティブウィンドウ: {active_window}")
            self.logger.debug("Top CPU使用プロセス:")
            for proc in top_cpu_processes:
                self.logger.debug(f"  {proc['name']}: {proc['cpu_percent']}%")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"メトリクス収集エラー: {e}")
=======
import psutil
import win32gui
import logging
import time
import threading
import queue
from threading import Thread
from typing import Optional, Dict, Any
from db.models import DatabaseManager

class SystemMonitor(Thread):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseManager()
        self.interval = 60
        self.running = False
        self.metrics_queue = queue.Queue()
        
        # メインスレッドでのデータベース更新用スレッド
        self.db_thread = Thread(target=self._process_metrics)
        self.db_thread.daemon = True
    
    def run(self):
        """モニタリングループを実行"""
        self.running = True
        self.db_thread.start()
        
        while self.running:
            try:
                metrics = self._collect_system_metrics()
                self.metrics_queue.put(metrics)
                time.sleep(self.interval)
            except Exception as e:
                self.logger.error(f"システムメトリクス収集エラー: {e}")
    
    def stop(self):
        """モニタリングを停止"""
        self.running = False
        self.metrics_queue.put(None)  # 終了シグナル
        self.db_thread.join()
        self.db_manager.close_all()
    
    def _process_metrics(self):
        """メインスレッドでメトリクスを処理"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        while True:
            metrics = self.metrics_queue.get()
            if metrics is None:  # 終了シグナル
                break
                
            try:
                cursor.execute('''
                INSERT INTO system_state (cpu_usage, memory_usage, active_window)
                VALUES (?, ?, ?)
                ''', (metrics['cpu_usage'], metrics['memory_usage'], metrics['active_window']))
                conn.commit()
            except Exception as e:
                self.logger.error(f"メトリクス記録エラー: {e}")
            
            self.metrics_queue.task_done()
        
        conn.close()
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """システムメトリクスを収集"""
        try:
            # CPU使用率
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # アクティブウィンドウ
            active_window = win32gui.GetWindowText(win32gui.GetForegroundWindow())
            
            # プロセス情報
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # 上位5つのCPU使用プロセスを取得
            top_cpu_processes = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:5]
            
            # メトリクスを返す
            metrics = {
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'active_window': active_window,
                'top_processes': top_cpu_processes
            }
            
            # デバッグ情報を記録
            self.logger.debug(f"CPU使用率: {cpu_usage}%")
            self.logger.debug(f"メモリ使用率: {memory_usage}%")
            self.logger.debug(f"アクティブウィンドウ: {active_window}")
            self.logger.debug("Top CPU使用プロセス:")
            for proc in top_cpu_processes:
                self.logger.debug(f"  {proc['name']}: {proc['cpu_percent']}%")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"メトリクス収集エラー: {e}")
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
            raise 
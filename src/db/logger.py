import logging
import threading
from typing import Optional

class DatabaseLogger:
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor()
        self.logger = logging.getLogger(__name__)
    
    @classmethod
    def get_instance(cls, conn=None):
        if not cls._instance and conn:
            with cls._lock:
                if not cls._instance:
                    cls._instance = cls(conn)
        return cls._instance
    
    def log_operation(self, operation_type: str, details: str, status: str = "SUCCESS", error_message: Optional[str] = None):
        with self._lock:
            try:
                self.cursor.execute('''
                INSERT INTO operation_history 
                (operation_type, operation_details, status, error_message)
                VALUES (?, ?, ?, ?)
                ''', (operation_type, details, status, error_message))
                self.conn.commit()
            except Exception as e:
                self.logger.error(f"操作ログの記録に失敗: {e}")
    
    def log_system_state(self, cpu_usage: float, memory_usage: float, active_window: str):
        with self._lock:
            try:
                self.cursor.execute('''
                INSERT INTO system_state 
                (cpu_usage, memory_usage, active_window)
                VALUES (?, ?, ?)
                ''', (cpu_usage, memory_usage, active_window))
                self.conn.commit()
            except Exception as e:
                self.logger.error(f"システム状態の記録に失敗: {e}")
                
    def close(self):
        """データベース接続を閉じる"""
        with self._lock:
            if self.conn:
                self.cursor.close()
                self.conn.close() 
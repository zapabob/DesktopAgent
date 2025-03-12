from pathlib import Path
import sqlite3
import logging
import threading
from typing import Optional
from datetime import datetime
from .logger import DatabaseLogger

class DatabaseManager:
    _instance = None
    _lock = threading.Lock()
    _local = threading.local()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.logger = logging.getLogger(__name__)
            self.db_path = Path('data/agent.db')
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.initialized = True
    
    def get_connection(self) -> sqlite3.Connection:
        """スレッドローカルなデータベース接続を取得"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(self.db_path)
        return self._local.connection
    
    def get_logger(self) -> DatabaseLogger:
        """データベースロガーを取得"""
        if not hasattr(self._local, 'logger'):
            self._local.logger = DatabaseLogger.get_instance(self.get_connection())
        return self._local.logger
    
    def initialize_database(self):
        """データベースの初期化"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # システム状態テーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            cpu_usage REAL,
            memory_usage REAL,
            active_window TEXT
        )
        ''')
        
        # 操作履歴テーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS operation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            operation_type TEXT,
            operation_details TEXT,
            status TEXT,
            error_message TEXT
        )
        ''')
        
        conn.commit()
    
    def close_all(self):
        """全てのデータベース接続を閉じる"""
        if hasattr(self._local, 'connection'):
            if hasattr(self._local, 'logger'):
                self._local.logger.close()
                del self._local.logger
            self._local.connection.close()
            del self._local.connection 
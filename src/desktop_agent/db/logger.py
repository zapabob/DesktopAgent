# -*- coding: utf-8 -*-
import logging
import threading
from typing import Optional
import logging.handlers
import os
from pathlib import Path

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

def setup_logging(
    level: str = "INFO",
    log_file: str = "logs/desktop_agent.log",
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5
):
    """ロギングの設定"""
    try:
        # ログディレクトリの作成
        log_dir = os.path.dirname(log_file)
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        # ロガーの設定
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, level.upper()))
        
        # フォーマッターの設定
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # ファイルハンドラーの設定
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # コンソールハンドラーの設定
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        logging.info("ロギングの設定が完了しました")
        
    except Exception as e:
        print(f"ロギングの設定中にエラーが発生しました: {e}")
        raise 
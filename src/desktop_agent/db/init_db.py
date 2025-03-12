import sqlite3
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def init_db(db_path: str = "data/permissions.db"):
    """データベースを初期化する"""
    try:
        # データベースディレクトリの作成
        db_dir = os.path.dirname(db_path)
        Path(db_dir).mkdir(parents=True, exist_ok=True)
        
        # データベース接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # テーブルの作成
        cursor.executescript("""
            -- パーミッションテーブル
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_type TEXT NOT NULL,
                resource_path TEXT NOT NULL,
                allowed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- 操作ログテーブル
            CREATE TABLE IF NOT EXISTS operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                resource_path TEXT,
                status TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- キャッシュテーブル
            CREATE TABLE IF NOT EXISTS response_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL,
                params TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            );
            
            -- インデックスの作成
            CREATE INDEX IF NOT EXISTS idx_permissions_resource ON permissions(resource_type, resource_path);
            CREATE INDEX IF NOT EXISTS idx_operation_logs_type ON operation_logs(operation_type);
            CREATE INDEX IF NOT EXISTS idx_response_cache_command ON response_cache(command);
        """)
        
        # 初期データの挿入
        cursor.executescript("""
            INSERT OR IGNORE INTO permissions (resource_type, resource_path, allowed)
            VALUES 
                ('directory', 'C:/Users/Public/Documents', TRUE),
                ('directory', 'C:/Users/Public/Downloads', TRUE),
                ('protocol', 'http', TRUE),
                ('protocol', 'https', TRUE),
                ('domain', 'github.com', TRUE),
                ('domain', 'google.com', TRUE),
                ('domain', 'microsoft.com', TRUE),
                ('application', 'chrome.exe', TRUE),
                ('application', 'msedge.exe', TRUE),
                ('application', 'notepad.exe', TRUE);
        """)
        
        conn.commit()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
        
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db() 
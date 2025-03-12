import sqlite3
from typing import Dict, Any, List, Optional, Tuple
import logging
from pathlib import Path
from datetime import datetime
from langchain.vectorstores import SQLiteVectorStore
from langchain.embeddings import OpenAIEmbeddings
from contextlib import contextmanager

class SecureDatabase:
    """セキュアなデータベース操作クラス"""
    def __init__(self, db_path: str = "metrics.db"):
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
        self.vector_store = None
        self._init_db()
        
    def _init_db(self):
        """データベースの初期化"""
        try:
            with self._get_connection() as conn:
                # スキーマの読み込みと実行
                schema_path = Path(__file__).parent / "schema.sql"
                with open(schema_path) as f:
                    conn.executescript(f.read())
                    
            # Vector Storeの初期化
            self.vector_store = SQLiteVectorStore(
                connection=sqlite3.connect(self.db_path),
                embedding=OpenAIEmbeddings()
            )
            
        except Exception as e:
            self.logger.error(f"データベース初期化エラー: {e}")
            raise
            
    @contextmanager
    def _get_connection(self):
        """データベース接続のコンテキストマネージャ"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        except Exception as e:
            self.logger.error(f"データベース接続エラー: {e}")
            raise
        finally:
            if conn:
                conn.close()
                
    def insert_metrics(self, metrics: Dict[str, Any]) -> bool:
        """メトリクスの安全な挿入"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # プリペアドステートメントの使用
                query = """
                INSERT INTO metrics (
                    timestamp, metric_type, metric_name,
                    metric_value, metadata
                ) VALUES (?, ?, ?, ?, ?)
                """
                
                # メトリクスのフラット化と挿入
                timestamp = datetime.now().isoformat()
                for metric_type, values in metrics.items():
                    self._insert_metric_recursively(
                        cursor, query, timestamp, metric_type, values
                    )
                    
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"メトリクス挿入エラー: {e}")
            return False
            
    def _insert_metric_recursively(self, cursor: sqlite3.Cursor,
                                query: str, timestamp: str,
                                metric_type: str, values: Any,
                                parent_key: str = ""):
        """メトリクスの再帰的な挿入"""
        if isinstance(values, dict):
            for key, value in values.items():
                new_key = f"{parent_key}.{key}" if parent_key else key
                self._insert_metric_recursively(
                    cursor, query, timestamp, metric_type,
                    value, new_key
                )
        else:
            cursor.execute(
                query,
                (
                    timestamp,
                    metric_type,
                    parent_key,
                    str(values),
                    None
                )
            )
            
    def query_metrics(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """メトリクスの安全なクエリ"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 動的なクエリの構築（安全に）
                query = "SELECT * FROM metrics WHERE 1=1"
                params = []
                
                if "start_time" in conditions:
                    query += " AND timestamp >= ?"
                    params.append(conditions["start_time"])
                    
                if "end_time" in conditions:
                    query += " AND timestamp <= ?"
                    params.append(conditions["end_time"])
                    
                if "metric_type" in conditions:
                    query += " AND metric_type = ?"
                    params.append(conditions["metric_type"])
                    
                if "metric_name" in conditions:
                    query += " AND metric_name = ?"
                    params.append(conditions["metric_name"])
                    
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"メトリクスクエリエラー: {e}")
            return []
            
    def search_similar_metrics(self, query: str,
                           limit: int = 10) -> List[Dict[str, Any]]:
        """類似メトリクスの検索"""
        try:
            if not self.vector_store:
                raise ValueError("Vector Storeが初期化されていません")
                
            results = self.vector_store.similarity_search(
                query,
                k=limit
            )
            
            return [
                {
                    "metric": result.page_content,
                    "metadata": result.metadata,
                    "similarity": result.similarity
                }
                for result in results
            ]
            
        except Exception as e:
            self.logger.error(f"類似メトリクス検索エラー: {e}")
            return []
            
    def delete_old_metrics(self, days: int) -> bool:
        """古いメトリクスの安全な削除"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                DELETE FROM metrics
                WHERE timestamp < datetime('now', ? || ' days')
                """
                
                cursor.execute(query, (f"-{days}",))
                conn.commit()
                
                return True
                
        except Exception as e:
            self.logger.error(f"古いメトリクス削除エラー: {e}")
            return False
            
    def validate_metric_value(self, value: Any) -> Tuple[bool, str]:
        """メトリクス値のバリデーション"""
        try:
            if isinstance(value, (int, float)):
                return True, ""
            elif isinstance(value, str):
                # SQLインジェクション対策
                if any(char in value for char in "';\""):
                    return False, "不正な文字が含まれています"
                return True, ""
            elif isinstance(value, (list, dict)):
                return True, ""
            else:
                return False, "未対応の値の型です"
                
        except Exception as e:
            return False, str(e)
            
    def backup_database(self, backup_path: str) -> bool:
        """データベースの安全なバックアップ"""
        try:
            with self._get_connection() as conn:
                backup_conn = sqlite3.connect(backup_path)
                conn.backup(backup_conn)
                backup_conn.close()
                return True
                
        except Exception as e:
            self.logger.error(f"データベースバックアップエラー: {e}")
            return False 
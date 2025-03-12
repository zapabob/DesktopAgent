import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import sqlite3

class IndexAnalyzer:
    """インデックス分析クラス"""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._lock = asyncio.Lock()
        
    async def analyze_indexes(self) -> Dict[str, Any]:
        """インデックスの分析"""
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                # インデックス情報の取得
                indexes = self._get_indexes(conn)
                
                # インデックスの使用状況
                usage_stats = self._analyze_index_usage(conn)
                
                # インデックスサイズの取得
                size_stats = self._get_index_sizes(conn)
                
                # 推奨事項の生成
                recommendations = self._generate_recommendations(
                    indexes, usage_stats, size_stats
                )
                
                return {
                    "indexes": indexes,
                    "usage_stats": usage_stats,
                    "size_stats": size_stats,
                    "recommendations": recommendations,
                    "timestamp": datetime.now().isoformat()
                }
                
            finally:
                conn.close()
                
        except Exception as e:
            self.logger.error(f"インデックス分析エラー: {e}")
            return {}
            
    def _get_indexes(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """インデックス情報の取得"""
        try:
            cursor = conn.cursor()
            indexes = []
            
            # 各テーブルのインデックスを取得
            for table in self._get_tables(conn):
                cursor.execute(f"PRAGMA index_list({table})")
                for idx in cursor.fetchall():
                    index_name = idx[1]
                    cursor.execute(f"PRAGMA index_info({index_name})")
                    columns = [col[2] for col in cursor.fetchall()]
                    
                    indexes.append({
                        "table": table,
                        "index_name": index_name,
                        "columns": columns,
                        "unique": idx[2] == 1
                    })
                    
            return indexes
            
        except Exception as e:
            self.logger.error(f"インデックス情報取得エラー: {e}")
            return []
            
    def _get_tables(self, conn: sqlite3.Connection) -> List[str]:
        """テーブル一覧の取得"""
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"テーブル一覧取得エラー: {e}")
            return []
            
    def _analyze_index_usage(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """インデックスの使用状況分析"""
        try:
            cursor = conn.cursor()
            stats = {}
            
            # 各インデックスの使用状況を分析
            for table in self._get_tables(conn):
                cursor.execute(f"ANALYZE {table}")
                cursor.execute(f"PRAGMA index_list({table})")
                
                for idx in cursor.fetchall():
                    index_name = idx[1]
                    cursor.execute(
                        f"SELECT * FROM sqlite_stat1 WHERE idx = ?",
                        (index_name,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        stats[index_name] = {
                            "table": table,
                            "rows_in_table": row[1],
                            "avg_rows_per_key": float(row[2].split()[0])
                            if row[2] else None
                        }
                        
            return stats
            
        except Exception as e:
            self.logger.error(f"インデックス使用状況分析エラー: {e}")
            return {}
            
    def _get_index_sizes(self, conn: sqlite3.Connection) -> Dict[str, int]:
        """インデックスサイズの取得"""
        try:
            cursor = conn.cursor()
            sizes = {}
            
            # 各インデックスのサイズを取得
            for table in self._get_tables(conn):
                cursor.execute(f"PRAGMA index_list({table})")
                for idx in cursor.fetchall():
                    index_name = idx[1]
                    cursor.execute(f"PRAGMA page_count")
                    page_count = cursor.fetchone()[0]
                    cursor.execute(f"PRAGMA page_size")
                    page_size = cursor.fetchone()[0]
                    
                    sizes[index_name] = page_count * page_size
                    
            return sizes
            
        except Exception as e:
            self.logger.error(f"インデックスサイズ取得エラー: {e}")
            return {}
            
    def _generate_recommendations(self,
                              indexes: List[Dict[str, Any]],
                              usage_stats: Dict[str, Any],
                              size_stats: Dict[str, int]) -> List[str]:
        """推奨事項の生成"""
        try:
            recommendations = []
            
            # 未使用インデックスの検出
            for idx in indexes:
                index_name = idx["index_name"]
                if index_name not in usage_stats:
                    recommendations.append(
                        f"インデックス '{index_name}' は未使用の可能性があります"
                    )
                    
            # 重複インデックスの検出
            column_sets = {}
            for idx in indexes:
                columns = tuple(sorted(idx["columns"]))
                if columns in column_sets:
                    recommendations.append(
                        f"インデックス '{idx['index_name']}' と "
                        f"'{column_sets[columns]}' が重複している可能性があります"
                    )
                else:
                    column_sets[columns] = idx["index_name"]
                    
            # 大きなインデックスの検出
            for index_name, size in size_stats.items():
                if size > 100 * 1024 * 1024:  # 100MB
                    recommendations.append(
                        f"インデックス '{index_name}' が大きすぎます "
                        f"({size / 1024 / 1024:.1f}MB)"
                    )
                    
            return recommendations
            
        except Exception as e:
            self.logger.error(f"推奨事項生成エラー: {e}")
            return []
            
    async def export_analysis(self, file_path: str):
        """分析結果のエクスポート"""
        try:
            import json
            analysis = await self.analyze_indexes()
            with open(file_path, "w") as f:
                json.dump(analysis, f, indent=2)
            self.logger.info(f"分析結果をエクスポートしました: {file_path}")
        except Exception as e:
            self.logger.error(f"分析結果エクスポートエラー: {e}")
            raise 
"""プリフェッチマネージャーモジュール。"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from ..database import ConnectionPool, TransactionManager

class PrefetchManager:
    """データのプリフェッチを管理するクラス"""
    
    def __init__(self, pool: ConnectionPool):
        self.pool = pool
        self.transaction_manager = TransactionManager(pool)
        self.logger = logging.getLogger(__name__)
        self._cache: Dict[str, Dict] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
    async def start(self):
        """プリフェッチの開始"""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._prefetch_loop())
            self.logger.info("プリフェッチマネージャーを開始しました")
            
    def stop(self):
        """プリフェッチの停止"""
        if self._running:
            self._running = False
            if self._task:
                self._task.cancel()
            self.logger.info("プリフェッチマネージャーを停止しました")
            
    async def get_cached_data(self, key: str) -> Optional[Dict]:
        """キャッシュされたデータの取得"""
        if key in self._cache:
            data = self._cache[key]
            if not self._is_cache_expired(data):
                return data
            else:
                del self._cache[key]
        return None
        
    async def _prefetch_loop(self):
        """プリフェッチループ"""
        try:
            while self._running:
                await self._prefetch_frequently_accessed_data()
                await self._cleanup_expired_cache()
                await asyncio.sleep(300)  # 5分間隔
        except asyncio.CancelledError:
            self.logger.info("プリフェッチループを終了します")
        except Exception as e:
            self.logger.error(f"プリフェッチループエラー: {e}")
            
    async def _prefetch_frequently_accessed_data(self):
        """頻繁にアクセスされるデータのプリフェッチ"""
        try:
            async with self.transaction_manager.transaction() as conn:
                # アクセス頻度の高いデータを取得
                cursor = await conn.execute("""
                    SELECT key, data
                    FROM access_stats
                    WHERE access_count > 10
                    AND last_access > datetime('now', '-1 day')
                    ORDER BY access_count DESC
                    LIMIT 100
                """)
                rows = await cursor.fetchall()
                
                for row in rows:
                    key = row[0]
                    data = row[1]
                    self._cache[key] = {
                        'data': data,
                        'timestamp': datetime.now(),
                        'ttl': timedelta(hours=1)
                    }
                    
        except Exception as e:
            self.logger.error(f"データプリフェッチエラー: {e}")
            
    async def _cleanup_expired_cache(self):
        """期限切れキャッシュのクリーンアップ"""
        try:
            expired_keys = [
                key for key, data in self._cache.items()
                if self._is_cache_expired(data)
            ]
            for key in expired_keys:
                del self._cache[key]
                
            if expired_keys:
                self.logger.info(f"{len(expired_keys)}件の期限切れキャッシュを削除しました")
                
        except Exception as e:
            self.logger.error(f"キャッシュクリーンアップエラー: {e}")
            
    def _is_cache_expired(self, data: Dict) -> bool:
        """キャッシュの期限切れチェック"""
        return datetime.now() - data['timestamp'] > data['ttl'] 
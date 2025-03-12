<<<<<<< HEAD
import asyncio
import logging
import aiosqlite
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from ..config.settings import settings

class ConnectionPool:
    """データベースコネクションプールクラス"""
    def __init__(self):
        self.db_settings = settings.get_db_settings()
        self.db_path = self.db_settings['metrics_db_path']
        self.max_connections = self.db_settings['max_connections']
        self.timeout = self.db_settings['connection_timeout']
        
        self._pool: List[aiosqlite.Connection] = []
        self._in_use: Dict[aiosqlite.Connection, datetime] = {}
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """プールの初期化"""
        try:
            async with self._lock:
                # 初期コネクションの作成
                initial_size = min(3, self.max_connections)
                for _ in range(initial_size):
                    conn = await self._create_connection()
                    self._pool.append(conn)
                self.logger.info(f"コネクションプールを初期化しました（サイズ: {initial_size}）")
        except Exception as e:
            self.logger.error(f"プール初期化エラー: {e}")
            raise
            
    async def _create_connection(self) -> aiosqlite.Connection:
        """新しいコネクションの作成"""
        try:
            conn = await aiosqlite.connect(
                self.db_path,
                timeout=self.timeout
            )
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            return conn
        except Exception as e:
            self.logger.error(f"コネクション作成エラー: {e}")
            raise
            
    async def acquire(self) -> aiosqlite.Connection:
        """コネクションの取得"""
        async with self._lock:
            try:
                # 利用可能なコネクションを探す
                for conn in self._pool:
                    if conn not in self._in_use:
                        self._in_use[conn] = datetime.now()
                        return conn
                        
                # プールが最大サイズに達していない場合は新規作成
                if len(self._pool) < self.max_connections:
                    conn = await self._create_connection()
                    self._pool.append(conn)
                    self._in_use[conn] = datetime.now()
                    return conn
                    
                # 最大サイズに達している場合は待機
                self.logger.warning("利用可能なコネクションがありません。待機中...")
                await asyncio.sleep(1)
                return await self.acquire()
                
            except Exception as e:
                self.logger.error(f"コネクション取得エラー: {e}")
                raise
                
    async def release(self, conn: aiosqlite.Connection):
        """コネクションの解放"""
        async with self._lock:
            try:
                if conn in self._in_use:
                    del self._in_use[conn]
                    self.logger.debug("コネクションを解放しました")
            except Exception as e:
                self.logger.error(f"コネクション解放エラー: {e}")
                
    async def cleanup(self):
        """未使用コネクションのクリーンアップ"""
        async with self._lock:
            try:
                now = datetime.now()
                idle_timeout = timedelta(minutes=5)
                
                # 長時間未使用のコネクションを閉じる
                for conn in list(self._pool):
                    if conn not in self._in_use:
                        last_used = self._in_use.get(conn)
                        if last_used and (now - last_used) > idle_timeout:
                            await conn.close()
                            self._pool.remove(conn)
                            self.logger.info("未使用コネクションをクローズしました")
                            
            except Exception as e:
                self.logger.error(f"クリーンアップエラー: {e}")
                
    async def close_all(self):
        """全コネクションのクローズ"""
        async with self._lock:
            try:
                for conn in self._pool:
                    await conn.close()
                self._pool.clear()
                self._in_use.clear()
                self.logger.info("全コネクションをクローズしました")
            except Exception as e:
                self.logger.error(f"コネクションクローズエラー: {e}")
                
    def get_stats(self) -> Dict[str, int]:
        """プールの統計情報を取得"""
        return {
            'total_connections': len(self._pool),
            'active_connections': len(self._in_use),
            'idle_connections': len(self._pool) - len(self._in_use)
=======
import asyncio
import logging
import aiosqlite
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from ..config.settings import settings

class ConnectionPool:
    """データベースコネクションプールクラス"""
    def __init__(self):
        self.db_settings = settings.get_db_settings()
        self.db_path = self.db_settings['metrics_db_path']
        self.max_connections = self.db_settings['max_connections']
        self.timeout = self.db_settings['connection_timeout']
        
        self._pool: List[aiosqlite.Connection] = []
        self._in_use: Dict[aiosqlite.Connection, datetime] = {}
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """プールの初期化"""
        try:
            async with self._lock:
                # 初期コネクションの作成
                initial_size = min(3, self.max_connections)
                for _ in range(initial_size):
                    conn = await self._create_connection()
                    self._pool.append(conn)
                self.logger.info(f"コネクションプールを初期化しました（サイズ: {initial_size}）")
        except Exception as e:
            self.logger.error(f"プール初期化エラー: {e}")
            raise
            
    async def _create_connection(self) -> aiosqlite.Connection:
        """新しいコネクションの作成"""
        try:
            conn = await aiosqlite.connect(
                self.db_path,
                timeout=self.timeout
            )
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            return conn
        except Exception as e:
            self.logger.error(f"コネクション作成エラー: {e}")
            raise
            
    async def acquire(self) -> aiosqlite.Connection:
        """コネクションの取得"""
        async with self._lock:
            try:
                # 利用可能なコネクションを探す
                for conn in self._pool:
                    if conn not in self._in_use:
                        self._in_use[conn] = datetime.now()
                        return conn
                        
                # プールが最大サイズに達していない場合は新規作成
                if len(self._pool) < self.max_connections:
                    conn = await self._create_connection()
                    self._pool.append(conn)
                    self._in_use[conn] = datetime.now()
                    return conn
                    
                # 最大サイズに達している場合は待機
                self.logger.warning("利用可能なコネクションがありません。待機中...")
                await asyncio.sleep(1)
                return await self.acquire()
                
            except Exception as e:
                self.logger.error(f"コネクション取得エラー: {e}")
                raise
                
    async def release(self, conn: aiosqlite.Connection):
        """コネクションの解放"""
        async with self._lock:
            try:
                if conn in self._in_use:
                    del self._in_use[conn]
                    self.logger.debug("コネクションを解放しました")
            except Exception as e:
                self.logger.error(f"コネクション解放エラー: {e}")
                
    async def cleanup(self):
        """未使用コネクションのクリーンアップ"""
        async with self._lock:
            try:
                now = datetime.now()
                idle_timeout = timedelta(minutes=5)
                
                # 長時間未使用のコネクションを閉じる
                for conn in list(self._pool):
                    if conn not in self._in_use:
                        last_used = self._in_use.get(conn)
                        if last_used and (now - last_used) > idle_timeout:
                            await conn.close()
                            self._pool.remove(conn)
                            self.logger.info("未使用コネクションをクローズしました")
                            
            except Exception as e:
                self.logger.error(f"クリーンアップエラー: {e}")
                
    async def close_all(self):
        """全コネクションのクローズ"""
        async with self._lock:
            try:
                for conn in self._pool:
                    await conn.close()
                self._pool.clear()
                self._in_use.clear()
                self.logger.info("全コネクションをクローズしました")
            except Exception as e:
                self.logger.error(f"コネクションクローズエラー: {e}")
                
    def get_stats(self) -> Dict[str, int]:
        """プールの統計情報を取得"""
        return {
            'total_connections': len(self._pool),
            'active_connections': len(self._in_use),
            'idle_connections': len(self._pool) - len(self._in_use)
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
        } 
import asyncio
import logging
from typing import Any, Callable, Optional, TypeVar
from contextlib import asynccontextmanager
from .connection_pool import ConnectionPool
from .query_builder import QueryBuilder

T = TypeVar('T')

class TransactionManager:
    """トランザクション管理クラス"""
    
    def __init__(self, pool: ConnectionPool):
        self.pool = pool
        self.query_builder = QueryBuilder()
        self.logger = logging.getLogger(__name__)
        self._local = asyncio.local()
        
    @asynccontextmanager
    async def transaction(self):
        """トランザクションコンテキストマネージャー"""
        conn = None
        try:
            # コネクションの取得
            conn = await self.pool.acquire()
            
            # トランザクションの開始
            await conn.execute("BEGIN")
            
            try:
                # コネクションをローカルストレージに保存
                self._local.connection = conn
                
                # トランザクションの実行
                yield conn
                
                # コミット
                await conn.commit()
                self.logger.debug("トランザクションをコミットしました")
                
            except Exception as e:
                # ロールバック
                await conn.rollback()
                self.logger.error(f"トランザクションをロールバックしました: {e}")
                raise
                
        finally:
            if conn:
                # ローカルストレージのクリア
                if hasattr(self._local, 'connection'):
                    delattr(self._local, 'connection')
                    
                # コネクションの解放
                await self.pool.release(conn)
                
    async def execute_with_retry(self,
                              operation: Callable[[], T],
                              max_retries: int = 3,
                              retry_delay: float = 1.0) -> T:
        """
        リトライ機能付きの操作実行
        
        Args:
            operation: 実行する操作
            max_retries: 最大リトライ回数
            retry_delay: リトライ間隔（秒）
            
        Returns:
            操作の結果
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await operation()
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = retry_delay * (2 ** attempt)  # 指数バックオフ
                    self.logger.warning(
                        f"操作に失敗しました（{attempt + 1}/{max_retries}回目）: {e}"
                        f" {delay}秒後にリトライします"
                    )
                    await asyncio.sleep(delay)
                    
        self.logger.error(f"操作が{max_retries}回失敗しました: {last_error}")
        raise last_error
        
    async def execute_query(self,
                         query: str,
                         params: Optional[list] = None) -> Any:
        """
        クエリの実行
        
        Args:
            query: SQLクエリ
            params: クエリパラメータ
            
        Returns:
            クエリの結果
        """
        conn = getattr(self._local, 'connection', None)
        if not conn:
            raise RuntimeError(
                "トランザクションコンテキスト外でクエリを実行することはできません"
            )
            
        try:
            cursor = await conn.execute(query, params or [])
            return cursor
            
        except Exception as e:
            self.logger.error(f"クエリ実行エラー: {e}\nQuery: {query}\nParams: {params}")
            raise
            
    async def fetch_one(self,
                     query: str,
                     params: Optional[list] = None) -> Optional[Any]:
        """1行のフェッチ"""
        cursor = await self.execute_query(query, params)
        return await cursor.fetchone()
        
    async def fetch_all(self,
                     query: str,
                     params: Optional[list] = None) -> list:
        """全行のフェッチ"""
        cursor = await self.execute_query(query, params)
        return await cursor.fetchall()
        
    async def execute(self,
                   query: str,
                   params: Optional[list] = None) -> int:
        """
        更新系クエリの実行
        
        Returns:
            影響を受けた行数
        """
        cursor = await self.execute_query(query, params)
        return cursor.rowcount 
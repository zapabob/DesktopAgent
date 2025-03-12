<<<<<<< HEAD
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

class QueryBuilder:
    """安全なSQLクエリビルダー"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def build_select(self,
                   table: str,
                   columns: List[str],
                   where: Optional[Dict[str, Any]] = None,
                   order_by: Optional[str] = None,
                   limit: Optional[int] = None) -> Tuple[str, List[Any]]:
        """
        SELECTクエリの構築
        
        Args:
            table: テーブル名
            columns: カラム名のリスト
            where: WHERE句の条件
            order_by: ORDER BY句
            limit: LIMIT句
            
        Returns:
            (クエリ文字列, パラメータのリスト)
        """
        try:
            # テーブル名とカラム名のバリデーション
            if not self._validate_identifier(table):
                raise ValueError(f"無効なテーブル名: {table}")
            for column in columns:
                if not self._validate_identifier(column):
                    raise ValueError(f"無効なカラム名: {column}")
                    
            # クエリの構築
            query = f"SELECT {', '.join(columns)} FROM {table}"
            params: List[Any] = []
            
            # WHERE句の構築
            if where:
                where_clause, where_params = self._build_where_clause(where)
                query += f" WHERE {where_clause}"
                params.extend(where_params)
                
            # ORDER BY句の追加
            if order_by:
                if not self._validate_identifier(order_by.replace(" ASC", "").replace(" DESC", "").strip()):
                    raise ValueError(f"無効なORDER BY句: {order_by}")
                query += f" ORDER BY {order_by}"
                
            # LIMIT句の追加
            if limit is not None:
                if not isinstance(limit, int) or limit < 0:
                    raise ValueError(f"無効なLIMIT値: {limit}")
                query += " LIMIT ?"
                params.append(limit)
                
            return query, params
            
        except Exception as e:
            self.logger.error(f"SELECTクエリ構築エラー: {e}")
            raise
            
    def build_insert(self,
                   table: str,
                   data: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """
        INSERTクエリの構築
        
        Args:
            table: テーブル名
            data: 挿入するデータ
            
        Returns:
            (クエリ文字列, パラメータのリスト)
        """
        try:
            # テーブル名のバリデーション
            if not self._validate_identifier(table):
                raise ValueError(f"無効なテーブル名: {table}")
                
            # カラム名のバリデーション
            columns = list(data.keys())
            for column in columns:
                if not self._validate_identifier(column):
                    raise ValueError(f"無効なカラム名: {column}")
                    
            # クエリの構築
            placeholders = ["?" for _ in range(len(data))]
            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
            
            # パラメータの準備
            params = list(data.values())
            
            return query, params
            
        except Exception as e:
            self.logger.error(f"INSERTクエリ構築エラー: {e}")
            raise
            
    def build_update(self,
                   table: str,
                   data: Dict[str, Any],
                   where: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """
        UPDATEクエリの構築
        
        Args:
            table: テーブル名
            data: 更新するデータ
            where: WHERE句の条件
            
        Returns:
            (クエリ文字列, パラメータのリスト)
        """
        try:
            # テーブル名のバリデーション
            if not self._validate_identifier(table):
                raise ValueError(f"無効なテーブル名: {table}")
                
            # カラム名のバリデーション
            for column in data.keys():
                if not self._validate_identifier(column):
                    raise ValueError(f"無効なカラム名: {column}")
                    
            # SET句の構築
            set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
            params = list(data.values())
            
            # WHERE句の構築
            where_clause, where_params = self._build_where_clause(where)
            params.extend(where_params)
            
            query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
            
            return query, params
            
        except Exception as e:
            self.logger.error(f"UPDATEクエリ構築エラー: {e}")
            raise
            
    def build_delete(self,
                   table: str,
                   where: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """
        DELETEクエリの構築
        
        Args:
            table: テーブル名
            where: WHERE句の条件
            
        Returns:
            (クエリ文字列, パラメータのリスト)
        """
        try:
            # テーブル名のバリデーション
            if not self._validate_identifier(table):
                raise ValueError(f"無効なテーブル名: {table}")
                
            # WHERE句の構築
            where_clause, params = self._build_where_clause(where)
            query = f"DELETE FROM {table} WHERE {where_clause}"
            
            return query, params
            
        except Exception as e:
            self.logger.error(f"DELETEクエリ構築エラー: {e}")
            raise
            
    def _build_where_clause(self,
                         conditions: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """WHERE句の構築"""
        try:
            clauses = []
            params = []
            
            for column, value in conditions.items():
                # カラム名のバリデーション
                if not self._validate_identifier(column):
                    raise ValueError(f"無効なカラム名: {column}")
                    
                if value is None:
                    clauses.append(f"{column} IS NULL")
                else:
                    clauses.append(f"{column} = ?")
                    params.append(value)
                    
            return " AND ".join(clauses), params
            
        except Exception as e:
            self.logger.error(f"WHERE句構築エラー: {e}")
            raise
            
    def _validate_identifier(self, identifier: str) -> bool:
        """SQLインジェクション対策のための識別子バリデーション"""
        # 英数字、アンダースコアのみを許可
        pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
        return bool(pattern.match(identifier))
        
    def sanitize_value(self, value: Any) -> Any:
        """値のサニタイズ"""
        if isinstance(value, str):
            # 特殊文字のエスケープ
            return value.replace("'", "''")
        elif isinstance(value, datetime):
            # 日時のフォーマット
            return value.isoformat()
=======
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

class QueryBuilder:
    """安全なSQLクエリビルダー"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def build_select(self,
                   table: str,
                   columns: List[str],
                   where: Optional[Dict[str, Any]] = None,
                   order_by: Optional[str] = None,
                   limit: Optional[int] = None) -> Tuple[str, List[Any]]:
        """
        SELECTクエリの構築
        
        Args:
            table: テーブル名
            columns: カラム名のリスト
            where: WHERE句の条件
            order_by: ORDER BY句
            limit: LIMIT句
            
        Returns:
            (クエリ文字列, パラメータのリスト)
        """
        try:
            # テーブル名とカラム名のバリデーション
            if not self._validate_identifier(table):
                raise ValueError(f"無効なテーブル名: {table}")
            for column in columns:
                if not self._validate_identifier(column):
                    raise ValueError(f"無効なカラム名: {column}")
                    
            # クエリの構築
            query = f"SELECT {', '.join(columns)} FROM {table}"
            params: List[Any] = []
            
            # WHERE句の構築
            if where:
                where_clause, where_params = self._build_where_clause(where)
                query += f" WHERE {where_clause}"
                params.extend(where_params)
                
            # ORDER BY句の追加
            if order_by:
                if not self._validate_identifier(order_by.replace(" ASC", "").replace(" DESC", "").strip()):
                    raise ValueError(f"無効なORDER BY句: {order_by}")
                query += f" ORDER BY {order_by}"
                
            # LIMIT句の追加
            if limit is not None:
                if not isinstance(limit, int) or limit < 0:
                    raise ValueError(f"無効なLIMIT値: {limit}")
                query += " LIMIT ?"
                params.append(limit)
                
            return query, params
            
        except Exception as e:
            self.logger.error(f"SELECTクエリ構築エラー: {e}")
            raise
            
    def build_insert(self,
                   table: str,
                   data: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """
        INSERTクエリの構築
        
        Args:
            table: テーブル名
            data: 挿入するデータ
            
        Returns:
            (クエリ文字列, パラメータのリスト)
        """
        try:
            # テーブル名のバリデーション
            if not self._validate_identifier(table):
                raise ValueError(f"無効なテーブル名: {table}")
                
            # カラム名のバリデーション
            columns = list(data.keys())
            for column in columns:
                if not self._validate_identifier(column):
                    raise ValueError(f"無効なカラム名: {column}")
                    
            # クエリの構築
            placeholders = ["?" for _ in range(len(data))]
            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
            
            # パラメータの準備
            params = list(data.values())
            
            return query, params
            
        except Exception as e:
            self.logger.error(f"INSERTクエリ構築エラー: {e}")
            raise
            
    def build_update(self,
                   table: str,
                   data: Dict[str, Any],
                   where: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """
        UPDATEクエリの構築
        
        Args:
            table: テーブル名
            data: 更新するデータ
            where: WHERE句の条件
            
        Returns:
            (クエリ文字列, パラメータのリスト)
        """
        try:
            # テーブル名のバリデーション
            if not self._validate_identifier(table):
                raise ValueError(f"無効なテーブル名: {table}")
                
            # カラム名のバリデーション
            for column in data.keys():
                if not self._validate_identifier(column):
                    raise ValueError(f"無効なカラム名: {column}")
                    
            # SET句の構築
            set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
            params = list(data.values())
            
            # WHERE句の構築
            where_clause, where_params = self._build_where_clause(where)
            params.extend(where_params)
            
            query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
            
            return query, params
            
        except Exception as e:
            self.logger.error(f"UPDATEクエリ構築エラー: {e}")
            raise
            
    def build_delete(self,
                   table: str,
                   where: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """
        DELETEクエリの構築
        
        Args:
            table: テーブル名
            where: WHERE句の条件
            
        Returns:
            (クエリ文字列, パラメータのリスト)
        """
        try:
            # テーブル名のバリデーション
            if not self._validate_identifier(table):
                raise ValueError(f"無効なテーブル名: {table}")
                
            # WHERE句の構築
            where_clause, params = self._build_where_clause(where)
            query = f"DELETE FROM {table} WHERE {where_clause}"
            
            return query, params
            
        except Exception as e:
            self.logger.error(f"DELETEクエリ構築エラー: {e}")
            raise
            
    def _build_where_clause(self,
                         conditions: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """WHERE句の構築"""
        try:
            clauses = []
            params = []
            
            for column, value in conditions.items():
                # カラム名のバリデーション
                if not self._validate_identifier(column):
                    raise ValueError(f"無効なカラム名: {column}")
                    
                if value is None:
                    clauses.append(f"{column} IS NULL")
                else:
                    clauses.append(f"{column} = ?")
                    params.append(value)
                    
            return " AND ".join(clauses), params
            
        except Exception as e:
            self.logger.error(f"WHERE句構築エラー: {e}")
            raise
            
    def _validate_identifier(self, identifier: str) -> bool:
        """SQLインジェクション対策のための識別子バリデーション"""
        # 英数字、アンダースコアのみを許可
        pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
        return bool(pattern.match(identifier))
        
    def sanitize_value(self, value: Any) -> Any:
        """値のサニタイズ"""
        if isinstance(value, str):
            # 特殊文字のエスケープ
            return value.replace("'", "''")
        elif isinstance(value, datetime):
            # 日時のフォーマット
            return value.isoformat()
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
        return value 
<<<<<<< HEAD
# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any
from enum import Enum

class ErrorCode(Enum):
    """エラーコード定義"""
    # データベース関連
    DB_CONNECTION_ERROR = "E1001"
    DB_QUERY_ERROR = "E1002"
    DB_TRANSACTION_ERROR = "E1003"
    DB_POOL_EXHAUSTED = "E1004"
    
    # キャッシュ関連
    CACHE_INIT_ERROR = "E2001"
    CACHE_SET_ERROR = "E2002"
    CACHE_GET_ERROR = "E2003"
    CACHE_DELETE_ERROR = "E2004"
    
    # バリデーション関連
    INVALID_TABLE_NAME = "E3001"
    INVALID_COLUMN_NAME = "E3002"
    INVALID_PARAMETER = "E3003"
    INVALID_QUERY = "E3004"
    
    # セキュリティ関連
    SQL_INJECTION_ATTEMPT = "E4001"
    UNAUTHORIZED_ACCESS = "E4002"
    INVALID_CREDENTIALS = "E4003"
    
    # システム関連
    SYSTEM_ERROR = "E9001"
    UNEXPECTED_ERROR = "E9999"

class BaseError(Exception):
    """基本例外クラス"""
    def __init__(self,
                code: ErrorCode,
                message: str,
                details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
        
    def to_dict(self) -> Dict[str, Any]:
        """エラー情報を辞書形式で取得"""
        return {
            'code': self.code.value,
            'message': self.message,
            'details': self.details
        }
        
class DatabaseError(BaseError):
    """データベース関連の例外"""
    pass

class CacheError(BaseError):
    """キャッシュ関連の例外"""
    pass

class ValidationError(BaseError):
    """バリデーション関連の例外"""
    pass

class SecurityError(BaseError):
    """セキュリティ関連の例外"""
    pass

class SystemError(BaseError):
    """システム関連の例外"""
    pass

def create_error(code: ErrorCode,
               message: Optional[str] = None,
               details: Optional[Dict[str, Any]] = None) -> BaseError:
    """
    エラーインスタンスの作成
    
    Args:
        code: エラーコード
        message: エラーメッセージ（Noneの場合はデフォルトメッセージを使用）
        details: 追加の詳細情報
        
    Returns:
        対応するエラーインスタンス
    """
    # デフォルトメッセージの定義
    default_messages = {
        # データベース関連
        ErrorCode.DB_CONNECTION_ERROR: "データベース接続エラー",
        ErrorCode.DB_QUERY_ERROR: "クエリ実行エラー",
        ErrorCode.DB_TRANSACTION_ERROR: "トランザクションエラー",
        ErrorCode.DB_POOL_EXHAUSTED: "コネクションプール枯渇",
        
        # キャッシュ関連
        ErrorCode.CACHE_INIT_ERROR: "キャッシュ初期化エラー",
        ErrorCode.CACHE_SET_ERROR: "キャッシュ設定エラー",
        ErrorCode.CACHE_GET_ERROR: "キャッシュ取得エラー",
        ErrorCode.CACHE_DELETE_ERROR: "キャッシュ削除エラー",
        
        # バリデーション関連
        ErrorCode.INVALID_TABLE_NAME: "無効なテーブル名",
        ErrorCode.INVALID_COLUMN_NAME: "無効なカラム名",
        ErrorCode.INVALID_PARAMETER: "無効なパラメータ",
        ErrorCode.INVALID_QUERY: "無効なクエリ",
        
        # セキュリティ関連
        ErrorCode.SQL_INJECTION_ATTEMPT: "SQLインジェクションの試行を検知",
        ErrorCode.UNAUTHORIZED_ACCESS: "不正なアクセス",
        ErrorCode.INVALID_CREDENTIALS: "無効な認証情報",
        
        # システム関連
        ErrorCode.SYSTEM_ERROR: "システムエラー",
        ErrorCode.UNEXPECTED_ERROR: "予期せぬエラー"
    }
    
    # エラーメッセージの設定
    error_message = message or default_messages.get(code, "不明なエラー")
    
    # エラークラスの選択
    if code.value.startswith("E1"):
        return DatabaseError(code, error_message, details)
    elif code.value.startswith("E2"):
        return CacheError(code, error_message, details)
    elif code.value.startswith("E3"):
        return ValidationError(code, error_message, details)
    elif code.value.startswith("E4"):
        return SecurityError(code, error_message, details)
    else:
        return SystemError(code, error_message, details)

class VectorStoreError(Exception):
    """ベクトルストアの基本例外クラス"""
    pass

class ChromaDBError(VectorStoreError):
    """ChromaDB操作エラー"""
    pass

class ConnectionError(VectorStoreError):
    """接続エラー"""
    pass

class HardwareMonitorError(Exception):
    """ハードウェアモニタリングの例外クラス"""
=======
# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any
from enum import Enum

class ErrorCode(Enum):
    """エラーコード定義"""
    # データベース関連
    DB_CONNECTION_ERROR = "E1001"
    DB_QUERY_ERROR = "E1002"
    DB_TRANSACTION_ERROR = "E1003"
    DB_POOL_EXHAUSTED = "E1004"
    
    # キャッシュ関連
    CACHE_INIT_ERROR = "E2001"
    CACHE_SET_ERROR = "E2002"
    CACHE_GET_ERROR = "E2003"
    CACHE_DELETE_ERROR = "E2004"
    
    # バリデーション関連
    INVALID_TABLE_NAME = "E3001"
    INVALID_COLUMN_NAME = "E3002"
    INVALID_PARAMETER = "E3003"
    INVALID_QUERY = "E3004"
    
    # セキュリティ関連
    SQL_INJECTION_ATTEMPT = "E4001"
    UNAUTHORIZED_ACCESS = "E4002"
    INVALID_CREDENTIALS = "E4003"
    
    # システム関連
    SYSTEM_ERROR = "E9001"
    UNEXPECTED_ERROR = "E9999"

class BaseError(Exception):
    """基本例外クラス"""
    def __init__(self,
                code: ErrorCode,
                message: str,
                details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
        
    def to_dict(self) -> Dict[str, Any]:
        """エラー情報を辞書形式で取得"""
        return {
            'code': self.code.value,
            'message': self.message,
            'details': self.details
        }
        
class DatabaseError(BaseError):
    """データベース関連の例外"""
    pass

class CacheError(BaseError):
    """キャッシュ関連の例外"""
    pass

class ValidationError(BaseError):
    """バリデーション関連の例外"""
    pass

class SecurityError(BaseError):
    """セキュリティ関連の例外"""
    pass

class SystemError(BaseError):
    """システム関連の例外"""
    pass

def create_error(code: ErrorCode,
               message: Optional[str] = None,
               details: Optional[Dict[str, Any]] = None) -> BaseError:
    """
    エラーインスタンスの作成
    
    Args:
        code: エラーコード
        message: エラーメッセージ（Noneの場合はデフォルトメッセージを使用）
        details: 追加の詳細情報
        
    Returns:
        対応するエラーインスタンス
    """
    # デフォルトメッセージの定義
    default_messages = {
        # データベース関連
        ErrorCode.DB_CONNECTION_ERROR: "データベース接続エラー",
        ErrorCode.DB_QUERY_ERROR: "クエリ実行エラー",
        ErrorCode.DB_TRANSACTION_ERROR: "トランザクションエラー",
        ErrorCode.DB_POOL_EXHAUSTED: "コネクションプール枯渇",
        
        # キャッシュ関連
        ErrorCode.CACHE_INIT_ERROR: "キャッシュ初期化エラー",
        ErrorCode.CACHE_SET_ERROR: "キャッシュ設定エラー",
        ErrorCode.CACHE_GET_ERROR: "キャッシュ取得エラー",
        ErrorCode.CACHE_DELETE_ERROR: "キャッシュ削除エラー",
        
        # バリデーション関連
        ErrorCode.INVALID_TABLE_NAME: "無効なテーブル名",
        ErrorCode.INVALID_COLUMN_NAME: "無効なカラム名",
        ErrorCode.INVALID_PARAMETER: "無効なパラメータ",
        ErrorCode.INVALID_QUERY: "無効なクエリ",
        
        # セキュリティ関連
        ErrorCode.SQL_INJECTION_ATTEMPT: "SQLインジェクションの試行を検知",
        ErrorCode.UNAUTHORIZED_ACCESS: "不正なアクセス",
        ErrorCode.INVALID_CREDENTIALS: "無効な認証情報",
        
        # システム関連
        ErrorCode.SYSTEM_ERROR: "システムエラー",
        ErrorCode.UNEXPECTED_ERROR: "予期せぬエラー"
    }
    
    # エラーメッセージの設定
    error_message = message or default_messages.get(code, "不明なエラー")
    
    # エラークラスの選択
    if code.value.startswith("E1"):
        return DatabaseError(code, error_message, details)
    elif code.value.startswith("E2"):
        return CacheError(code, error_message, details)
    elif code.value.startswith("E3"):
        return ValidationError(code, error_message, details)
    elif code.value.startswith("E4"):
        return SecurityError(code, error_message, details)
    else:
        return SystemError(code, error_message, details)

class VectorStoreError(Exception):
    """ベクトルストアの基本例外クラス"""
    pass

class ChromaDBError(VectorStoreError):
    """ChromaDB操作エラー"""
    pass

class ConnectionError(VectorStoreError):
    """接続エラー"""
    pass

class HardwareMonitorError(Exception):
    """ハードウェアモニタリングの例外クラス"""
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
    pass 
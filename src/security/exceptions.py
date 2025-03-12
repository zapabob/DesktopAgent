# -*- coding: utf-8 -*-
# セキュリティ関連の例外クラス
def init_security_exceptions():
    """セキュリティ関連の例外クラスの初期化"""
    pass
class SecurityException(Exception):
    """セキュリティ関連の基底例外クラス"""
    pass

class ConfigError(SecurityException):
    """設定関連の例外"""
    def __init__(self, message: str, missing_keys: list = None):
        super().__init__(message)
        self.missing_keys = missing_keys or []

class DatabaseError(SecurityException):
    """データベース操作関連の例外"""
    pass

class ValidationError(SecurityException):
    """入力検証失敗例外"""
    pass 
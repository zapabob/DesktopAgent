import os
from pathlib import Path
from typing import Dict, Any

class Settings:
    """アプリケーション設定クラス"""
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        
        # データベース設定
        self.db_settings = {
            'metrics_db_path': str(self.base_dir / "data" / "metrics.db"),
            'permissions_db_path': str(self.base_dir / "data" / "permissions.db"),
            'max_connections': 10,
            'connection_timeout': 30
        }
        
        # キャッシュ設定
        self.cache_settings = {
            'max_size': 1000,
            'ttl': 3600,  # 1時間
            'cleanup_interval': 300  # 5分
        }
        
        # モニタリング設定
        self.monitoring_settings = {
            'interval': 60,  # 1分
            'history_size': 1000,
            'export_interval': 3600  # 1時間
        }
        
        # ロギング設定
        self.logging_settings = {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'log_dir': str(self.base_dir / "logs")
        }
        
    def get_all(self) -> Dict[str, Any]:
        """全設定を取得"""
        return {
            'database': self.db_settings,
            'cache': self.cache_settings,
            'monitoring': self.monitoring_settings,
            'logging': self.logging_settings
        }
        
    def get_db_settings(self) -> Dict[str, Any]:
        """データベース設定を取得"""
        return self.db_settings
        
    def get_cache_settings(self) -> Dict[str, Any]:
        """キャッシュ設定を取得"""
        return self.cache_settings
        
    def get_monitoring_settings(self) -> Dict[str, Any]:
        """モニタリング設定を取得"""
        return self.monitoring_settings
        
    def get_logging_settings(self) -> Dict[str, Any]:
        """ロギング設定を取得"""
        return self.logging_settings

# シングルトンインスタンス
settings = Settings() 
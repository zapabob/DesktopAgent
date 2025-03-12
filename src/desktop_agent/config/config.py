<<<<<<< HEAD
# -*- coding: utf-8 -*-
import os
import json
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# .envファイルの読み込み
load_dotenv()

class Config:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.config = {
            'permissions_db_path': str(self.base_dir / 'db' / 'permissions.db'),
            'log_dir': str(self.base_dir / 'logs'),
            'rate_limit': {
                'requests': 100,
                'period': 3600  # 1時間
            },
            'api_keys': {
                'openai': os.getenv('OPENAI_API_KEY'),
                'anthropic': os.getenv('ANTHROPIC_API_KEY'),
                'google': os.getenv('GOOGLE_API_KEY'),
                'deepseek': os.getenv('DEEPSEEK_API_KEY')
            },
            'models': {
                'default': 'gemini-pro',
                'vision': 'gemini-pro-vision'
            },
            'agents': [],
            'system_settings': {
                'cpu_threshold': 80,
                'memory_threshold': 85,
                'requests_per_minute': 60,
                'concurrent_tasks': 5
            },
            'logging_settings': {
                'level': 'INFO',
                'file_path': 'logs/desktop_agent.log',
                'max_size': 10485760,  # 10MB
                'backup_count': 5
            },
            'security_settings': {
                'encryption_key': 'your_encryption_key_here',
                'token_expiry': 3600,
                'max_retries': 3
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        return self.config.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """設定値を取得（添字形式）"""
        return self.config[key]

    async def load(self, config_path: str = "config.json"):
        """設定ファイルを読み込む"""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")

            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # エージェント設定
            self.config['agents'] = config_data.get('agents', [])

            # システム設定
            self.config['system_settings'] = config_data.get('system_settings', {
                'cpu_threshold': 80,
                'memory_threshold': 85,
                'requests_per_minute': 60,
                'concurrent_tasks': 5
            })

            # ロギング設定
            self.config['logging_settings'] = config_data.get('logging_settings', {
                'level': 'INFO',
                'file_path': 'logs/desktop_agent.log',
                'max_size': 10485760,  # 10MB
                'backup_count': 5
            })

            # セキュリティ設定
            self.config['security_settings'] = config_data.get('security_settings', {
                'encryption_key': 'your_encryption_key_here',
                'token_expiry': 3600,
                'max_retries': 3
            })

        except Exception as e:
            raise ConfigError(f"設定の読み込みに失敗: {e}")

class ConfigError(Exception):
    """設定関連のエラー"""
    pass

def get_config() -> Dict[str, Any]:
    """設定を読み込む"""
    config_path = Path(__file__).parent / "config.json"

    if not config_path.exists():
        # デフォルト設定
        return {
            'permissions_db_path': 'data/permissions.db',
            'allowed_directories': [
                os.path.expanduser('~/Documents'),
                os.path.expanduser('~/Downloads')
            ],
            'allowed_protocols': ['http', 'https'],
            'allowed_domains': [],
            'allowed_applications': ['notepad.exe', 'calc.exe'],
            'cpu_threshold': 90,
            'memory_threshold': 90,
            'rate_limit': {
                'requests': 100,
                'period': 60
            }
        }

    with open(config_path, 'r') as f:
=======
# -*- coding: utf-8 -*-
import os
import json
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# .envファイルの読み込み
load_dotenv()

class Config:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.config = {
            'permissions_db_path': str(self.base_dir / 'db' / 'permissions.db'),
            'log_dir': str(self.base_dir / 'logs'),
            'rate_limit': {
                'requests': 100,
                'period': 3600  # 1時間
            },
            'api_keys': {
                'openai': os.getenv('OPENAI_API_KEY'),
                'anthropic': os.getenv('ANTHROPIC_API_KEY'),
                'google': os.getenv('GOOGLE_API_KEY'),
                'deepseek': os.getenv('DEEPSEEK_API_KEY')
            },
            'models': {
                'default': 'gemini-pro',
                'vision': 'gemini-pro-vision'
            },
            'agents': [],
            'system_settings': {
                'cpu_threshold': 80,
                'memory_threshold': 85,
                'requests_per_minute': 60,
                'concurrent_tasks': 5
            },
            'logging_settings': {
                'level': 'INFO',
                'file_path': 'logs/desktop_agent.log',
                'max_size': 10485760,  # 10MB
                'backup_count': 5
            },
            'security_settings': {
                'encryption_key': 'your_encryption_key_here',
                'token_expiry': 3600,
                'max_retries': 3
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得"""
        return self.config.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """設定値を取得（添字形式）"""
        return self.config[key]

    async def load(self, config_path: str = "config.json"):
        """設定ファイルを読み込む"""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")

            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # エージェント設定
            self.config['agents'] = config_data.get('agents', [])

            # システム設定
            self.config['system_settings'] = config_data.get('system_settings', {
                'cpu_threshold': 80,
                'memory_threshold': 85,
                'requests_per_minute': 60,
                'concurrent_tasks': 5
            })

            # ロギング設定
            self.config['logging_settings'] = config_data.get('logging_settings', {
                'level': 'INFO',
                'file_path': 'logs/desktop_agent.log',
                'max_size': 10485760,  # 10MB
                'backup_count': 5
            })

            # セキュリティ設定
            self.config['security_settings'] = config_data.get('security_settings', {
                'encryption_key': 'your_encryption_key_here',
                'token_expiry': 3600,
                'max_retries': 3
            })

        except Exception as e:
            raise ConfigError(f"設定の読み込みに失敗: {e}")

class ConfigError(Exception):
    """設定関連のエラー"""
    pass

def get_config() -> Dict[str, Any]:
    """設定を読み込む"""
    config_path = Path(__file__).parent / "config.json"

    if not config_path.exists():
        # デフォルト設定
        return {
            'permissions_db_path': 'data/permissions.db',
            'allowed_directories': [
                os.path.expanduser('~/Documents'),
                os.path.expanduser('~/Downloads')
            ],
            'allowed_protocols': ['http', 'https'],
            'allowed_domains': [],
            'allowed_applications': ['notepad.exe', 'calc.exe'],
            'cpu_threshold': 90,
            'memory_threshold': 90,
            'rate_limit': {
                'requests': 100,
                'period': 60
            }
        }

    with open(config_path, 'r') as f:
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
        return json.load(f)
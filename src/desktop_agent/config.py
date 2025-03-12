# -*- coding: utf-8 -*-
"""Configuration module."""

import yaml
from pathlib import Path
from typing import Dict, Any, List

class Config:
    """設定管理クラス"""
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(__file__).parent.parent / config_path
        self.config_data = {}
        
    async def load(self):
        """設定ファイルの読み込み"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f)
        except FileNotFoundError:
            # デフォルト設定の使用
            self.config_data = self._get_default_config()
            
        # 設定読み込み後にバリデーションを追加
        self._validate_agents()
        
    def get(self, key: str, default: Any = None) -> Any:
        """設定値の取得"""
        return self.config_data.get(key, default)
        
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定"""
        return {
            'ai_providers': {
                'use_vertexai': True,
                'use_openai': False,
                'use_anthropic': False
            },
            'system_settings': {
                'cpu_threshold': 80,
                'memory_threshold': 85,
                'log_level': 'INFO'
            },
            'agents': [
                {
                    'id': 'agent1',
                    'role': 'task_executor',
                    'type': 'worker',
                    'priority': 1,
                    'capabilities': ['mouse_control', 'keyboard_control']
                }
            ],
            'database': {
                'path': 'desktop_agent.db',
                'backup_interval': 3600
            },
            'model': {
                'input_dim': 8,
                'hidden_dim': 256,
                'num_layers': 4,
                'num_heads': 8,
                'dropout': 0.1,
                'batch_size': 32,
                'learning_rate': 0.001,
                'max_epochs': 100
            }
        } 

    def _validate_agents(self):
        required_fields = ['type', 'model', 'max_tokens']
        valid_models = ['gemini-pro', 'gpt-4-turbo', 'claude-3-opus']
        
        for agent_id, settings in self.config_data.get('agents', {}).items():
            if not isinstance(settings, dict):
                raise ValueError(f"Agent {agent_id} has invalid configuration format")
            
            # モデル名の検証
            if 'model' in settings and settings['model'] not in valid_models:
                raise ValueError(f"無効なモデル指定: {settings['model']}")

            for field in required_fields:
                if field not in settings:
                    raise ValueError(f"Agent {agent_id} missing required field: {field}") 
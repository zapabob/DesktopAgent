"""
MCPモジュール - Model Context Protocol
MCPサーバーとの通信を管理するモジュール
"""

import logging

# ロギングの設定
logger = logging.getLogger(__name__)
logger.info("MCPモジュールが初期化されました")

# MCPアダプタークラスをインポート可能にする
try:
    from .mcp_adapter import MCPAdapter
except ImportError as e:
    logger.error(f"MCPアダプタのインポートに失敗しました: {e}")

__all__ = ["MCPAdapter"] 
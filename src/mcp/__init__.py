"""
MCP (Model Context Protocol) モジュール

このモジュールはDesktopAgentとMCPサーバーとの連携機能を提供します。
"""

import logging

# モジュールのロガー設定
logger = logging.getLogger(__name__)

# 主要なクラスのインポート
try:
    from .mcp_adapter import MCPAdapter
except ImportError as e:
    logger.warning(f"MCPAdapterのインポートに失敗しました: {e}")
    MCPAdapter = None

__all__ = ["MCPAdapter"] 
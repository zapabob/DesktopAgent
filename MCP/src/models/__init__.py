"""
モデルモジュール - AI言語モデルの管理
"""

import logging

# ロギングの設定
logger = logging.getLogger(__name__)
logger.info("モデルモジュールが初期化されました")

# モデルマネージャーをインポート可能にする
try:
    from .model_manager import ModelManager
except ImportError as e:
    logger.error(f"ModelManagerのインポートに失敗しました: {e}")

__all__ = ["ModelManager"]




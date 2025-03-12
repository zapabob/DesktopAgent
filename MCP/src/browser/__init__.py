"""
ブラウザモジュール - Web操作機能の管理
"""

import logging

# ロギングの設定
logger = logging.getLogger(__name__)
logger.info("ブラウザモジュールが初期化されました")

# ブラウザコントローラーをインポート可能にする
try:
    from .browser_controller import BrowserController, BROWSER_USE_AVAILABLE
except ImportError as e:
    logger.error(f"BrowserControllerのインポートに失敗しました: {e}")
    BROWSER_USE_AVAILABLE = False

__all__ = ["BrowserController", "BROWSER_USE_AVAILABLE"]



"""
アプリケーションのエントリーポイント
"""
import sys
import logging
from pathlib import Path
from .config.config import Config
from .gui.main_window import main as gui_main
from datetime import datetime

def setup_logging():
    """ロギングの設定"""
    Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                Config.LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log",
                encoding='utf-8'
            )
        ]
    )

def main():
    """メインエントリーポイント"""
    try:
        # 設定の初期化
        Config.setup()
        
        # ロギングの設定
        setup_logging()
        
        # GUIの起動
        gui_main()
        
    except Exception as e:
        logging.error(f"アプリケーション実行エラー: {e}", exc_info=True)
        return 1
        
    return 0

if __name__ == '__main__':
    sys.exit(main()) 
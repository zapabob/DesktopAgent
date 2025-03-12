#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from dotenv import load_dotenv

# プロジェクトルートの取得
script_dir = Path(__file__).parent
project_root = script_dir.parent

# 環境変数の読み込み
load_dotenv(project_root / '.env')

# DPI設定を調整
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

# ロギングの設定
log_level = getattr(logging, os.environ.get('LOG_LEVEL', 'INFO'))
log_file = os.environ.get('LOG_FILE', 'app.log')
log_file_path = project_root / log_file

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file_path, encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)
logger.info("アプリケーションを起動しています...")

# 必要なモジュールのインポート
try:
    from gui.main_window import MainWindow
    from agent.autonomous_agent import AutonomousAgent
    from agent.command_interpreter import CommandInterpreter
    from db.models import DatabaseManager
    import wmi
except ImportError as e:
    logger.error(f"モジュールのインポートに失敗しました: {e}")
    sys.exit(1)

def main():
    try:
        # データベースの初期化
        db_manager = DatabaseManager()
        db_manager.initialize_database()
        
        # アプリケーションの初期化
        app = QApplication(sys.argv)
        
        # エージェントとインタープリタの初期化
        agent = AutonomousAgent(db_manager.get_logger())
        interpreter = CommandInterpreter()
        
        # システム情報の初期化
        system = wmi.WMI()
        
        # メインウィンドウの作成と表示
        window = MainWindow(agent, interpreter, system)
        window.show()
        
        logger.info("アプリケーションの準備が完了しました")
        
        # アプリケーションの実行
        return app.exec()
    except Exception as e:
        logger.error(f"アプリケーションの起動中にエラーが発生しました: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())

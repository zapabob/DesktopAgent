#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from dotenv import load_dotenv
import wmi

# プロジェクトルートとsrcディレクトリをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# DPI設定を調整
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

# ロギングの設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)

# 必要なモジュールのインポート
from src.gui.main_window import MainWindow
from src.agent.autonomous_agent import AutonomousAgent
from src.agent.command_interpreter import CommandInterpreter
from src.db.models import DatabaseManager

def main():
    load_dotenv()
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
    
    # アプリケーションの実行
    return app.exec()

if __name__ == '__main__':
    sys.exit(main())

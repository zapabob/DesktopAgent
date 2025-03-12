<<<<<<< HEAD
# -*- coding: utf-8 -*-
import logging
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from dotenv import load_dotenv  # 追加

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
        logging.StreamHandler(sys.stdout),  # 標準出力へのハンドラ
        logging.FileHandler('app.log', encoding='utf-8')  # ファイルへのハンドラ（UTF-8指定）
    ]
)

# プロジェクトルートとsrcディレクトリをPythonパスに追加
project_root = Path(__file__).parent.parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

# 必要なモジュールのインポート
from gui.main_window import MainWindow
from agent.autonomous_agent import AutonomousAgent
from agent.command_interpreter import CommandInterpreter
from db.models import DatabaseManager

def main():
    load_dotenv()  # .envの値を読み込む
    # データベースの初期化
    db_manager = DatabaseManager()
    db_manager.initialize_database()
    
    # アプリケーションの初期化
    app = QApplication(sys.argv)
    
    # エージェントとインタープリタの初期化
    agent = AutonomousAgent(db_manager.get_logger())
    interpreter = CommandInterpreter()
    
    # メインウィンドウの作成と表示
    window = MainWindow(agent, interpreter)
    window.show()
    
    # アプリケーションの実行
    return app.exec()

if __name__ == '__main__':
=======
# -*- coding: utf-8 -*-
import logging
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from dotenv import load_dotenv  # 追加
import wmi

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
        logging.StreamHandler(sys.stdout),  # 標準出力へのハンドラ
        logging.FileHandler('app.log', encoding='utf-8')  # ファイルへのハンドラ（UTF-8指定）
    ]
)

# プロジェクトルートとsrcディレクトリをPythonパスに追加
project_root = Path(__file__).parent.parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

# 必要なモジュールのインポート
from gui.main_window import MainWindow
from agent.autonomous_agent import AutonomousAgent
from agent.command_interpreter import CommandInterpreter
from db.models import DatabaseManager

def main():
    load_dotenv()  # .envの値を読み込む
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
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
    sys.exit(main())
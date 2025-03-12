# -*- coding: utf-8 -*-
import logging
import sys
import socket
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from dotenv import load_dotenv
import wmi

# シングルインスタンス制御のための設定
SINGLE_INSTANCE_PORT = 47789  # 使用するポート番号
single_instance_socket = None

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
project_root = Path(__file__).resolve().parent.parent
src_path = project_root / 'src'
sys.path.insert(0, str(project_root))  # プロジェクトルートを追加
sys.path.insert(0, str(src_path))      # srcディレクトリを追加

# 必要なモジュールのインポート
from gui.main_window import MainWindow
from agent.autonomous_agent import AutonomousAgent
from agent.command_interpreter import CommandInterpreter
from db.models import DatabaseManager

def is_already_running():
    """既に同じアプリケーションが起動しているかチェック"""
    global single_instance_socket
    
    logger = logging.getLogger(__name__)
    logger.info("他のインスタンスが実行中かチェックしています...")
    
    try:
        # ソケットの作成とバインド
        single_instance_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        single_instance_socket.bind(('localhost', SINGLE_INSTANCE_PORT))
        single_instance_socket.setblocking(False)
        logger.info("アプリケーションの新規インスタンスを起動します")
        return False
    except socket.error:
        logger.warning("アプリケーションのインスタンスは既に実行中です")
        return True

def main():
    """メイン関数"""
    logger = logging.getLogger(__name__)
    
    # 多重起動のチェック
    if is_already_running():
        # QApplicationがまだ作成されていない場合は作成
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # 既に起動しているというメッセージを表示
        QMessageBox.warning(
            None,
            "デスクトップエージェント - 多重起動の警告",
            "デスクトップエージェントは既に起動しています。\n"
            "複数のインスタンスを同時に実行することはできません。",
            QMessageBox.StandardButton.Ok
        )
        return 1  # エラーコードを返して終了
    
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

def cleanup():
    """終了時の後片付け"""
    global single_instance_socket
    
    if single_instance_socket:
        try:
            single_instance_socket.close()
        except:
            pass

if __name__ == '__main__':
    try:
        exit_code = main()
    finally:
        cleanup()
    sys.exit(exit_code)
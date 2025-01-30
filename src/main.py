# -*- coding: utf-8 -*-
import os
import sys
import asyncio
import traceback
from pathlib import Path
import logging

# プロジェクトルートをPYTHONPATHに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root.parent))

from PyQt6.QtWidgets import QApplication
from desktop_agent.config import Config
from desktop_agent.agent.agent_manager import AutonomousAgentManager
from desktop_agent.gui.main_window import MainWindow
from desktop_agent.langchain_integration import LangChainManager
from desktop_agent.database.init_db import init_database

# メイン関数の先頭に環境変数設定を追加
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_CPP_MIN_VLOG_LEVEL'] = '0'  # 詳細ログ抑制
os.environ['TF_XLA_FLAGS'] = '--tf_xla_enable_xla_devices'
os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # GPU使用を明示
os.environ['PYTHONWARNINGS'] = 'ignore::UserWarning'

async def main():
    try:
        os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
        os.environ['TF_XLA_FLAGS'] = '--tf_xla_enable_xla_devices'
        os.environ['PYTHONWARNINGS'] = 'ignore::UserWarning'
        
        # データベースの初期化
        db_session = init_database()
        
        # 設定の初期化
        config = Config()
        await config.load()
        
        # コンポーネントの初期化
        agent_manager = AutonomousAgentManager(config, db_session)
        langchain_manager = LangChainManager(config)
        
        # エージェントマネージャーの開始
        await agent_manager.start()
        
        # Qtアプリケーションの作成
        app = QApplication(sys.argv)
        
        # メインウィンドウの作成と表示
        window = MainWindow(agent_manager, langchain_manager)
        window.show()
        
        # イベントループの開始
        exit_code = app.exec()
        
        # エージェントマネージャーの停止
        await agent_manager.stop()
        
        # データベースセッションのクローズ
        db_session.close()
        
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        print(f"トレースバック: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('desktop_agent.log'),
            logging.StreamHandler()
        ]
    )
    
    # Windows環境でのイベントループポリシーの設定
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # メインループの実行
    asyncio.run(main()) 
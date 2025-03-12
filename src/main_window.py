from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QLabel, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, pyqtSlot
import logging

class MainWindow(QMainWindow):
    def __init__(self, agent, command_interpreter):
        super().__init__()
        self.agent = agent
        self.command_interpreter = command_interpreter
        self.logger = logging.getLogger(__name__)
        self.init_ui()
        
    def init_ui(self):
        """UIの初期化"""
        self.setWindowTitle('デスクトップエージェント')
        self.setGeometry(100, 100, 1000, 700)
        
        # タブウィジェットの作成
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # メインタブの追加
        main_tab = self._create_main_tab()
        self.tab_widget.addTab(main_tab, "メイン")
        
        # コマンド一覧タブの追加
        commands_tab = self._create_commands_tab()
        self.tab_widget.addTab(commands_tab, "コマンド一覧")
    
    def _create_main_tab(self):
        """メインタブの作成"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # ログ表示エリア
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        layout.addWidget(QLabel('操作ログ:'))
        layout.addWidget(self.log_display)
        
        # コマンド入力エリア
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText('コマンドを入力してください...')
        self.command_input.returnPressed.connect(self.execute_command)
        layout.addWidget(QLabel('コマンド入力:'))
        layout.addWidget(self.command_input)
        
        # 実行ボタン
        execute_button = QPushButton('実行')
        execute_button.clicked.connect(self.execute_command)
        layout.addWidget(execute_button)
        
        tab.setLayout(layout)
        return tab
    
    def _create_commands_tab(self):
        """コマンド一覧タブの作成"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # コマンド一覧テーブル
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(['コマンド', '説明', '例'])
        
        # コマンド一覧データ
        commands = [
            ('edge URL', 'Microsoft EdgeでURLを開く', 'edge google.com'),
            ('chrome URL', 'Google ChromeでURLを開く', 'chrome youtube.com'),
            ('browser URL', 'デフォルトブラウザでURLを開く', 'browser github.com'),
            ('フォルダ作成', 'フォルダを作成', 'documentsフォルダを作成して'),
            ('ファイル移動', 'ファイルを移動', 'test.txtをdocumentsに移動して'),
            ('削除', 'ファイルまたはフォルダを削除', 'temp.txtを削除して'),
            ('最小化', 'ウィンドウを最小化', 'Chromeを最小化して'),
            ('起動', 'アプリケーションを起動', 'メモ帳を起動して'),
            ('マウス移動', 'マウスを指定座標に移動', 'マウスを100, 200に移動して'),
            ('マウスクリック', '指定座標をクリック', '100, 200を2回右クリックして'),
            ('ドラッグ', '指定座標間をドラッグ', '100, 200から300, 400までドラッグして'),
            ('スクロール', '指定量スクロール', '下に300スクロールして'),
            ('キー記録', 'キーボード操作の記録を開始', 'キー操作を記録して'),
            ('キー停止', 'キーボード操作の記録を停止', 'キー操作を停止して'),
            ('キー再生', '記録したキーボード操作を再生', 'キー操作を再生して'),
            ('テキスト入力', '指定したテキストを入力', '「Hello, World!」と入力して'),
            ('ホットキー', '指定したホットキーを実行', 'ホットキーctrl+cを実行して'),
            ('画面分析', '画面全体を分析', '画面を分析して'),
            ('領域分析', '指定領域を分析', '100, 200から300, 400の範囲を分析して')
        ]
        
        # テーブルにデータを設定
        table.setRowCount(len(commands))
        for i, (cmd, desc, example) in enumerate(commands):
            table.setItem(i, 0, QTableWidgetItem(cmd))
            table.setItem(i, 1, QTableWidgetItem(desc))
            table.setItem(i, 2, QTableWidgetItem(example))
        
        # テーブルの設定
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(table)
        tab.setLayout(layout)
        return tab
    
    @pyqtSlot()
    def execute_command(self):
        """コマンドの実行"""
        command = self.command_input.text().strip()
        if not command:
            return
            
        self.log_display.append(f"\n> {command}")
        self.command_input.clear()
        
        try:
            # コマンドの解釈と実行
            result = self.command_interpreter.interpret(command)
            if result:
                command_type, params = result
                success = self.agent.execute_command(command_type, params)
                if success:
                    self.log_display.append("✓ コマンドを実行しました")
                else:
                    self.log_display.append("✗ コマンドの実行に失敗しました")
            else:
                self.log_display.append("？ コマンドを理解できませんでした")
                
        except Exception as e:
            self.logger.error(f"コマンド実行エラー: {e}")
            self.log_display.append(f"⚠ エラー: {str(e)}")
        
        # スクロールを最下部に移動
        self.log_display.verticalScrollBar().setValue(
            self.log_display.verticalScrollBar().maximum()
        ) 
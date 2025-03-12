from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QLabel, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QHBoxLayout, QProgressBar, QSystemTrayIcon, QMenu, QDialog,
    QSpinBox, QGroupBox, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QIcon, QAction
import logging
import sys
from datetime import datetime
import psutil
import GPUtil
import wmi

class TaskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("タスクの追加/編集")
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # タスク名
        self.name_edit = QLineEdit()
        layout.addWidget(QLabel("タスク名:"))
        layout.addWidget(self.name_edit)
        
        # 説明
        self.description_edit = QTextEdit()
        layout.addWidget(QLabel("説明:"))
        layout.addWidget(self.description_edit)
        
        # 所要時間（分）
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 120)
        self.duration_spin.setValue(25)
        layout.addWidget(QLabel("所要時間（分）:"))
        layout.addWidget(self.duration_spin)
        
        # ボタン
        buttons_layout = QHBoxLayout()
        save_button = QPushButton("保存")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("キャンセル")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
    def get_task_data(self):
        return {
            "name": self.name_edit.text(),
            "description": self.description_edit.toPlainText(),
            "duration": self.duration_spin.value()
        }

class MainWindow(QMainWindow):
    def __init__(self, agent, command_interpreter, system):
        super().__init__()
        self.agent = agent
        self.command_interpreter = command_interpreter
        self.system = system
        self.pomodoro_time = 25 * 60  # 25分
        self.break_time = 5 * 60      # 5分
        self.timer_running = False
        self.remaining_time = self.pomodoro_time
        self.is_break = False
        self.logger = logging.getLogger(__name__)
        self.init_ui()
        
        # WMIの初期化
        self.wmi_interface = wmi.WMI(namespace="root\\OpenHardwareMonitor")
        
        self.setup_system_tray()
        self.setup_timers()
        
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
        
        # ブラウザセクションを追加
        browser_group = QGroupBox("ブラウザ操作")
        browser_layout = QVBoxLayout()
        
        # URL入力フォーム
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        url_layout.addWidget(self.url_input)
        
        # ブラウザ選択
        browser_selector_layout = QHBoxLayout()
        browser_selector_layout.addWidget(QLabel("ブラウザ:"))
        self.browser_selector = QComboBox()
        
        # 利用可能なブラウザを取得
        try:
            available_browsers = self.command_interpreter.get_available_browsers()
            self.browser_selector.addItems(available_browsers)
            if not available_browsers:
                self.browser_selector.addItem("デフォルト")
        except Exception as e:
            self.logger.error(f"ブラウザリスト取得エラー: {e}")
            self.browser_selector.addItem("デフォルト")
        
        browser_selector_layout.addWidget(self.browser_selector)
        
        # 操作ボタン
        browser_buttons_layout = QHBoxLayout()
        
        open_url_btn = QPushButton("URLを開く")
        open_url_btn.clicked.connect(self.open_url)
        
        search_google_btn = QPushButton("Google検索")
        search_google_btn.clicked.connect(self.search_google)
        
        youtube_btn = QPushButton("YouTube検索")
        youtube_btn.clicked.connect(self.play_youtube)
        
        gmail_btn = QPushButton("Gmail")
        gmail_btn.clicked.connect(self.open_gmail)
        
        calendar_btn = QPushButton("カレンダー")
        calendar_btn.clicked.connect(self.open_calendar)
        
        browser_buttons_layout.addWidget(open_url_btn)
        browser_buttons_layout.addWidget(search_google_btn)
        browser_buttons_layout.addWidget(youtube_btn)
        browser_buttons_layout.addWidget(gmail_btn)
        browser_buttons_layout.addWidget(calendar_btn)
        
        # レイアウトをグループに追加
        browser_layout.addLayout(url_layout)
        browser_layout.addLayout(browser_selector_layout)
        browser_layout.addLayout(browser_buttons_layout)
        browser_group.setLayout(browser_layout)
        
        # メインレイアウトに追加
        main_layout = QVBoxLayout()
        main_layout.addWidget(browser_group)
        main_layout.addWidget(self.log_display)
        main_layout.addWidget(self.command_input)
        main_layout.addWidget(execute_button)
        
        tab.setLayout(main_layout)
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

    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon.png"))
        
        tray_menu = QMenu()
        show_action = QAction("表示", self)
        show_action.triggered.connect(self.show)
        quit_action = QAction("終了", self)
        quit_action.triggered.connect(self.close)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
    def setup_timers(self):
        # 時計更新タイマー
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        
        # システムモニタリングタイマー
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.update_system_stats)
        self.monitor_timer.start(2000)
        
        # ポモドーロタイマー
        self.pomodoro_timer = QTimer(self)
        self.pomodoro_timer.timeout.connect(self.update_timer)
        
    def update_clock(self):
        current_time = datetime.now().strftime("%H:%M:%S")
        self.clock_label.setText(current_time)
        
    def update_system_stats(self):
        # CPU使用率と温度
        cpu_percent = psutil.cpu_percent()
        self.cpu_bar.setValue(int(cpu_percent))
        
        try:
            temperature_infos = self.wmi_interface.Sensor()
            for sensor in temperature_infos:
                if sensor.SensorType == 'Temperature':
                    if 'CPU' in sensor.Name:
                        self.cpu_temp_label.setText(f"CPU温度: {sensor.Value}°C")
                    elif 'GPU' in sensor.Name:
                        self.gpu_temp_label.setText(f"GPU温度: {sensor.Value}°C")
        except Exception as e:
            self.cpu_temp_label.setText("CPU温度: N/A")
            self.gpu_temp_label.setText("GPU温度: N/A")
        
        # メモリ使用率
        memory = psutil.virtual_memory()
        self.memory_bar.setValue(int(memory.percent))
        
        # GPU使用率
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                self.gpu_bar.setValue(int(gpu.load * 100))
        except Exception as e:
            self.gpu_bar.setValue(0)
            
    def toggle_timer(self):
        if self.timer_running:
            self.pomodoro_timer.stop()
            self.start_button.setText("開始")
        else:
            self.pomodoro_timer.start(1000)
            self.start_button.setText("停止")
        self.timer_running = not self.timer_running
        
    def reset_timer(self):
        self.pomodoro_timer.stop()
        self.timer_running = False
        self.start_button.setText("開始")
        self.remaining_time = self.pomodoro_time if not self.is_break else self.break_time
        self.update_timer_display()
        
    def update_timer(self):
        self.remaining_time -= 1
        if self.remaining_time <= 0:
            self.pomodoro_timer.stop()
            self.timer_running = False
            self.start_button.setText("開始")
            
            if not self.is_break:
                self.tray_icon.showMessage(
                    "ポモドーロタイマー",
                    "作業時間が終了しました。休憩を取りましょう。",
                    QSystemTrayIcon.MessageIcon.Information
                )
                self.is_break = True
                self.remaining_time = self.break_time
            else:
                self.tray_icon.showMessage(
                    "ポモドーロタイマー",
                    "休憩時間が終了しました。作業を再開しましょう。",
                    QSystemTrayIcon.MessageIcon.Information
                )
                self.is_break = False
                self.remaining_time = self.pomodoro_time
                
        self.update_timer_display()
        
    def update_timer_display(self):
        minutes = self.remaining_time // 60
        seconds = self.remaining_time % 60
        self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")
        
    def add_task(self):
        dialog = TaskDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            task_data = dialog.get_task_data()
            row = self.task_table.rowCount()
            self.task_table.insertRow(row)
            self.task_table.setItem(row, 0, QTableWidgetItem(task_data["name"]))
            self.task_table.setItem(row, 1, QTableWidgetItem(task_data["description"]))
            self.task_table.setItem(row, 2, QTableWidgetItem(str(task_data["duration"])))
            self.task_table.setItem(row, 3, QTableWidgetItem("未開始"))
            
    def edit_task(self):
        current_row = self.task_table.currentRow()
        if current_row >= 0:
            dialog = TaskDialog(self)
            dialog.name_edit.setText(self.task_table.item(current_row, 0).text())
            dialog.description_edit.setText(self.task_table.item(current_row, 1).text())
            dialog.duration_spin.setValue(int(self.task_table.item(current_row, 2).text()))
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                task_data = dialog.get_task_data()
                self.task_table.setItem(current_row, 0, QTableWidgetItem(task_data["name"]))
                self.task_table.setItem(current_row, 1, QTableWidgetItem(task_data["description"]))
                self.task_table.setItem(current_row, 2, QTableWidgetItem(str(task_data["duration"])))
                
    def delete_task(self):
        current_row = self.task_table.currentRow()
        if current_row >= 0:
            self.task_table.removeRow(current_row)
            
    def play_youtube(self):
        """YouTubeで検索・再生する"""
        query = self.url_input.text().strip()
        if not query:
            QMessageBox.warning(self, "入力エラー", "検索するキーワードを入力してください")
            return
        
        selected_browser = self.browser_selector.currentText() if self.browser_selector.count() > 0 else None
        
        # コマンドインタープリタを使用してYouTube検索を実行
        command_text = f"YouTubeで {query} を検索"
        self.logger.info(f"実行コマンド: {command_text}")
        success = self.command_interpreter.execute_command(command_text)
        
        if not success:
            QMessageBox.warning(self, "実行エラー", f"YouTubeでの検索に失敗しました: {query}")

    def open_url(self):
        """URLをブラウザで開く"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "入力エラー", "URLを入力してください")
            return
        
        # スキームがない場合は追加
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        selected_browser = self.browser_selector.currentText() if self.browser_selector.count() > 0 else None
        
        # コマンドインタープリタを使用してURLを開く
        command_text = f"ブラウザで {url} を開く"
        self.logger.info(f"実行コマンド: {command_text}")
        success = self.command_interpreter.execute_command(command_text)
        
        if not success:
            QMessageBox.warning(self, "実行エラー", f"URLを開けませんでした: {url}")

    def search_google(self):
        """Googleで検索する"""
        query = self.url_input.text().strip()
        if not query:
            QMessageBox.warning(self, "入力エラー", "検索するキーワードを入力してください")
            return
        
        selected_browser = self.browser_selector.currentText() if self.browser_selector.count() > 0 else None
        
        # コマンドインタープリタを使用してGoogle検索を実行
        command_text = f"Googleで {query} を検索"
        self.logger.info(f"実行コマンド: {command_text}")
        success = self.command_interpreter.execute_command(command_text)
        
        if not success:
            QMessageBox.warning(self, "実行エラー", f"Googleでの検索に失敗しました: {query}")

    def open_gmail(self):
        """Gmailを開く"""
        # コマンドインタープリタを使用してGmailを開く
        command_text = "Gmailを開く"
        self.logger.info(f"実行コマンド: {command_text}")
        success = self.command_interpreter.execute_command(command_text)
        
        if not success:
            QMessageBox.warning(self, "実行エラー", "Gmailを開けませんでした")

    def open_calendar(self):
        """Googleカレンダーを開く"""
        # コマンドインタープリタを使用してカレンダーを開く
        command_text = "カレンダーを開く"
        self.logger.info(f"実行コマンド: {command_text}")
        success = self.command_interpreter.execute_command(command_text)
        
        if not success:
            QMessageBox.warning(self, "実行エラー", "カレンダーを開けませんでした")

    def closeEvent(self, event):
        self.hide()
        event.ignore() 
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QLabel, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QHBoxLayout, QProgressBar, QSystemTrayIcon, QMenu, QDialog,
    QSpinBox)
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
        url = self.url_edit.text()
        if "youtube.com" in url or "youtu.be" in url:
            self.web_view.setUrl(QUrl(url))
            
    def closeEvent(self, event):
        self.hide()
        event.ignore() 
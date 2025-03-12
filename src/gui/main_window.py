from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QLabel, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QHBoxLayout, QProgressBar, QSystemTrayIcon, QMenu, QDialog,
    QSpinBox, QGroupBox, QComboBox, QMessageBox, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer, QUrl, QTime
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QIcon, QAction
import logging
import sys
from datetime import datetime
import psutil
import GPUtil
import wmi
import threading
import os
from pathlib import Path

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
        try:
            self.wmi_interface = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            self.ohm_available = True
        except Exception as e:
            self.logger.warning(f"OpenHardwareMonitorに接続できません。システム監視の一部機能が制限されます: {e}")
            self.ohm_available = False
        
        self.setup_system_tray()
        self.setup_timers()
        
    def init_ui(self):
        """UIの初期化"""
        self.setWindowTitle('デスクトップエージェント')
        self.setGeometry(100, 100, 1000, 700)
        
        # 時計ラベルの作成
        self.clock_label = QLabel()
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.clock_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        
        # システム監視コンポーネントの初期化
        self.setup_system_monitor()
        
        self.create_tabs()
        
    def setup_system_monitor(self):
        """システム監視用のUIコンポーネントを初期化"""
        # CPU使用率表示
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setMaximum(100)
        self.cpu_bar.setFormat("%v%")
        self.cpu_bar.setTextVisible(True)
        
        # GPU使用率表示
        self.gpu_bar = QProgressBar()
        self.gpu_bar.setMaximum(100)
        self.gpu_bar.setFormat("%v%")
        self.gpu_bar.setTextVisible(True)
        
        # メモリ使用率表示
        self.memory_bar = QProgressBar()
        self.memory_bar.setMaximum(100)
        self.memory_bar.setFormat("%v%")
        self.memory_bar.setTextVisible(True)
        
        # 温度表示ラベル
        self.cpu_temp_label = QLabel("CPU温度: N/A")
        self.gpu_temp_label = QLabel("GPU温度: N/A")
        
    def create_tabs(self):
        """メインのタブを作成"""
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # ステータスバーに時計を表示
        status_bar = self.statusBar()
        status_bar.addPermanentWidget(self.clock_label)
        
        # メイン機能タブ
        self.main_tab = QWidget()
        self.tabs.addTab(self.main_tab, "メイン")
        self.setup_main_tab()
        
        # コマンドリストタブ
        self.command_list_tab = QWidget()
        self.tabs.addTab(self.command_list_tab, "コマンド一覧")
        self.setup_command_list_tab()
        
        # ブラウザ機能タブ
        self.browser_tab = QWidget()
        self.tabs.addTab(self.browser_tab, "ブラウザ機能")
        self.setup_browser_tab()
        
        # タブが変更されたときのイベント
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def setup_main_tab(self):
        """メインタブの作成"""
        layout = QVBoxLayout()
        
        # システム情報セクション
        system_group = QGroupBox("システム情報")
        system_layout = QVBoxLayout()
        
        # CPU情報
        cpu_layout = QHBoxLayout()
        cpu_layout.addWidget(QLabel("CPU使用率:"))
        cpu_layout.addWidget(self.cpu_bar)
        cpu_layout.addWidget(self.cpu_temp_label)
        system_layout.addLayout(cpu_layout)
        
        # GPU情報
        gpu_layout = QHBoxLayout()
        gpu_layout.addWidget(QLabel("GPU使用率:"))
        gpu_layout.addWidget(self.gpu_bar)
        gpu_layout.addWidget(self.gpu_temp_label)
        system_layout.addLayout(gpu_layout)
        
        # メモリ情報
        memory_layout = QHBoxLayout()
        memory_layout.addWidget(QLabel("メモリ使用率:"))
        memory_layout.addWidget(self.memory_bar)
        system_layout.addLayout(memory_layout)
        
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)
        
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
        
        self.main_tab.setLayout(main_layout)

    def setup_command_list_tab(self):
        """コマンドリストタブの設定"""
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
        self.command_list_tab.setLayout(layout)

    def setup_browser_tab(self):
        """ブラウザ機能タブの設定"""
        layout = QVBoxLayout()
        
        # タイトル
        title_label = QLabel("高度なブラウザ操作機能")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 説明
        description_label = QLabel("browser-useパッケージを使用した高度なブラウザ操作機能を利用できます。")
        description_label.setWordWrap(True)
        layout.addWidget(description_label)
        
        # 機能リスト（スクロールエリア内）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_container = QWidget()
        scroll_layout = QVBoxLayout(scroll_container)
        
        # 機能カードを作成
        features = [
            {
                "title": "インテリジェントなウェブ自動化",
                "description": "AIを活用したウェブブラウザの操作が可能です。自然言語で指示するだけで、様々なウェブサイトでの操作を自動化します。",
                "commands": ["「ブラウザでYahooを開いて」", "「YouTubeで猫の動画を再生して」"]
            },
            {
                "title": "要素操作",
                "description": "ウェブページ上の特定の要素（ボタン、リンク、テキストなど）を指示して操作できます。",
                "commands": ["「ブラウザで要素ログインボタンをクリック」", "「ブラウザで要素検索をクリック」"]
            },
            {
                "title": "スクリーンショット",
                "description": "現在表示しているウェブページのスクリーンショットを撮影し保存できます。",
                "commands": ["「ブラウザでスクリーンショットを撮る」"]
            },
            {
                "title": "マルチLLMサポート",
                "description": "様々なLLMを使用して、より高度なウェブ操作が可能です。",
                "commands": []
            }
        ]
        
        for feature in features:
            # 機能カードのフレーム
            card = QFrame()
            card.setFrameShape(QFrame.Shape.StyledPanel)
            card.setStyleSheet("background-color: #f5f5f5; border-radius: 5px; padding: 10px; margin: 5px;")
            card_layout = QVBoxLayout(card)
            
            # タイトル
            title = QLabel(feature["title"])
            title.setStyleSheet("font-size: 14pt; font-weight: bold;")
            card_layout.addWidget(title)
            
            # 説明
            desc = QLabel(feature["description"])
            desc.setWordWrap(True)
            desc.setStyleSheet("font-size: 10pt; margin-top: 5px; margin-bottom: 5px;")
            card_layout.addWidget(desc)
            
            # コマンド例
            if feature["commands"]:
                commands_label = QLabel("コマンド例:")
                commands_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
                card_layout.addWidget(commands_label)
                
                for cmd in feature["commands"]:
                    cmd_label = QLabel(f"• {cmd}")
                    cmd_label.setStyleSheet("font-family: monospace; padding-left: 10px;")
                    card_layout.addWidget(cmd_label)
            
            scroll_layout.addWidget(card)
        
        # 余白を追加
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_container)
        layout.addWidget(scroll_area)
        
        # ブラウザ起動ボタン
        browser_button = QPushButton("ブラウザを起動")
        browser_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                padding: 10px;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        browser_button.clicked.connect(self.launch_browser)
        layout.addWidget(browser_button)
        
        self.browser_tab.setLayout(layout)

    def launch_browser(self):
        """ブラウザを起動する"""
        try:
            # browser_useパッケージのインポートを試行
            try:
                from browser_use import Browser
            except ImportError:
                self.log("browser_useパッケージが見つかりません。pip install browser-useでインストールしてください。", logging.ERROR)
                return

            # 非同期関数なので、簡単なURLを開くだけにする
            import asyncio
            import threading
            
            def run_browser():
                async def navigate():
                    try:
                        # headlessパラメータを削除し、デフォルト設定を使用
                        browser = Browser()
                        await browser.navigate("https://www.google.com")
                        # ブラウザは自動的に閉じず、開いたままにする
                    except Exception as e:
                        self.log(f"ブラウザ起動エラー: {e}", logging.ERROR)
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(navigate())
                except Exception as e:
                    self.log(f"ブラウザ実行エラー: {e}", logging.ERROR)
            
            # 別スレッドで実行
            thread = threading.Thread(target=run_browser)
            thread.daemon = True
            thread.start()
            
            self.log("ブラウザを起動しました")
        except Exception as e:
            self.log(f"ブラウザの起動に失敗しました: {str(e)}")

    def on_tab_changed(self, index):
        """タブが変更されたときの処理"""
        pass  # 必要に応じて処理を追加

    def execute_command(self):
        """コマンド入力からコマンドを実行"""
        command = self.command_input.text().strip()
        if not command:
            return
            
        self.log(f"コマンド: {command}")
        self.command_input.clear()
        
        if self.command_interpreter is not None:
            # コマンドの実行は別スレッドで行う
            threading.Thread(target=self._execute_command_thread, args=(command,), daemon=True).start()
        else:
            self.log("コマンドインタープリタが初期化されていません")

    def _execute_command_thread(self, command):
        """別スレッドでコマンドを実行"""
        try:
            success = self.command_interpreter.execute_command(command)
            if success:
                self.log("コマンドを実行しました")
            else:
                self.log("コマンドの実行に失敗しました")
        except Exception as e:
            self.log(f"コマンド実行エラー: {str(e)}")

    def log(self, message):
        """ログを表示"""
        current_time = QTime.currentTime().toString("HH:mm:ss")
        log_message = f"[{current_time}] {message}"
        self.log_display.append(log_message)
        
        # ログをファイルにも書き込む
        try:
            if hasattr(self, 'logger') and self.logger:
                self.logger.info(message)
        except Exception:
            pass  # ロギングエラーは無視

    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # アイコンファイルの検索
        project_root = Path(__file__).resolve().parent.parent.parent
        icon_paths = [
            "icon.png",  # 現在のディレクトリ
            os.path.join(project_root, "icon.png"),  # プロジェクトルート
            os.path.join(project_root, "src", "assets", "icon.png"),  # アセットフォルダ
            os.path.join(project_root, "assets", "icon.png"),  # アセットフォルダ
        ]
        
        icon_found = False
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                self.tray_icon.setIcon(QIcon(icon_path))
                icon_found = True
                break
                
        if not icon_found:
            # アイコンがない場合はデフォルトアイコンを使用
            self.logger.warning("アイコンファイルが見つかりません: icon.png")
            # PyQt6のデフォルトアイコンを使用
            self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        
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
            if hasattr(self, 'ohm_available') and self.ohm_available:
                temperature_infos = self.wmi_interface.Sensor()
                for sensor in temperature_infos:
                    if sensor.SensorType == 'Temperature':
                        if 'CPU' in sensor.Name:
                            self.cpu_temp_label.setText(f"CPU温度: {sensor.Value}°C")
                        elif 'GPU' in sensor.Name:
                            self.gpu_temp_label.setText(f"GPU温度: {sensor.Value}°C")
            else:
                self.cpu_temp_label.setText("CPU温度: N/A (OHM未接続)")
                self.gpu_temp_label.setText("GPU温度: N/A (OHM未接続)")
        except Exception as e:
            self.logger.warning(f"温度情報取得エラー: {e}")
            self.cpu_temp_label.setText("CPU温度: エラー")
            self.gpu_temp_label.setText("GPU温度: エラー")
        
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
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QProgressBar,
    QComboBox, QSpinBox, QTextEdit, QGroupBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
import psutil
import GPUtil
from typing import Dict, Any, List
import json
from datetime import datetime
import logging

class AgentDashboard(QWidget):
    """エージェントダッシュボード"""
    agent_command = pyqtSignal(str, dict)  # エージェントへのコマンド送信用シグナル
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.setup_ui()
        self.setup_timers()
        
    def setup_ui(self):
        """UIの初期化"""
        layout = QVBoxLayout()
        
        # システムモニタリング
        system_group = QGroupBox("システムモニタリング")
        system_layout = QVBoxLayout()
        
        # CPU使用率
        cpu_layout = QHBoxLayout()
        self.cpu_label = QLabel("CPU使用率:")
        self.cpu_bar = QProgressBar()
        self.cpu_temp_label = QLabel("温度: N/A")
        cpu_layout.addWidget(self.cpu_label)
        cpu_layout.addWidget(self.cpu_bar)
        cpu_layout.addWidget(self.cpu_temp_label)
        system_layout.addLayout(cpu_layout)
        
        # メモリ使用率
        memory_layout = QHBoxLayout()
        self.memory_label = QLabel("メモリ使用率:")
        self.memory_bar = QProgressBar()
        memory_layout.addWidget(self.memory_label)
        memory_layout.addWidget(self.memory_bar)
        system_layout.addLayout(memory_layout)
        
        # GPU使用率
        gpu_layout = QHBoxLayout()
        self.gpu_label = QLabel("GPU使用率:")
        self.gpu_bar = QProgressBar()
        self.gpu_temp_label = QLabel("温度: N/A")
        gpu_layout.addWidget(self.gpu_label)
        gpu_layout.addWidget(self.gpu_bar)
        gpu_layout.addWidget(self.gpu_temp_label)
        system_layout.addLayout(gpu_layout)
        
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)
        
        # エージェント管理
        agent_group = QGroupBox("エージェント管理")
        agent_layout = QVBoxLayout()
        
        # エージェントテーブル
        self.agent_table = QTableWidget()
        self.agent_table.setColumnCount(5)
        self.agent_table.setHorizontalHeaderLabels([
            "エージェントID", "状態", "タスク数", "CPU使用率", "メモリ使用率"
        ])
        agent_layout.addWidget(self.agent_table)
        
        # エージェント操作ボタン
        button_layout = QHBoxLayout()
        self.add_agent_button = QPushButton("エージェント追加")
        self.remove_agent_button = QPushButton("エージェント削除")
        self.pause_agent_button = QPushButton("一時停止")
        self.resume_agent_button = QPushButton("再開")
        
        self.add_agent_button.clicked.connect(self.add_agent)
        self.remove_agent_button.clicked.connect(self.remove_agent)
        self.pause_agent_button.clicked.connect(self.pause_agent)
        self.resume_agent_button.clicked.connect(self.resume_agent)
        
        button_layout.addWidget(self.add_agent_button)
        button_layout.addWidget(self.remove_agent_button)
        button_layout.addWidget(self.pause_agent_button)
        button_layout.addWidget(self.resume_agent_button)
        agent_layout.addLayout(button_layout)
        
        agent_group.setLayout(agent_layout)
        layout.addWidget(agent_group)
        
        # タスク管理
        task_group = QGroupBox("タスク管理")
        task_layout = QVBoxLayout()
        
        # タスクテーブル
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(5)
        self.task_table.setHorizontalHeaderLabels([
            "タスクID", "エージェントID", "タイプ", "状態", "進捗"
        ])
        task_layout.addWidget(self.task_table)
        
        # タスク操作
        task_control_layout = QHBoxLayout()
        self.task_type_combo = QComboBox()
        self.task_type_combo.addItems([
            "ブラウザ操作", "ファイル操作", "デスクトップ操作",
            "マウス操作", "キーボード操作", "画像認識"
        ])
        
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 10)
        self.priority_spin.setValue(5)
        
        self.submit_task_button = QPushButton("タスク投入")
        self.cancel_task_button = QPushButton("タスクキャンセル")
        
        self.submit_task_button.clicked.connect(self.submit_task)
        self.cancel_task_button.clicked.connect(self.cancel_task)
        
        task_control_layout.addWidget(QLabel("タスクタイプ:"))
        task_control_layout.addWidget(self.task_type_combo)
        task_control_layout.addWidget(QLabel("優先度:"))
        task_control_layout.addWidget(self.priority_spin)
        task_control_layout.addWidget(self.submit_task_button)
        task_control_layout.addWidget(self.cancel_task_button)
        task_layout.addLayout(task_control_layout)
        
        task_group.setLayout(task_layout)
        layout.addWidget(task_group)
        
        # ログ表示
        log_group = QGroupBox("ログ")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        self.setLayout(layout)
        
    def setup_timers(self):
        """タイマーの設定"""
        # システムモニタリング更新タイマー
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.update_system_metrics)
        self.monitor_timer.start(2000)  # 2秒ごとに更新
        
        # エージェント状態更新タイマー
        self.agent_timer = QTimer()
        self.agent_timer.timeout.connect(self.update_agent_status)
        self.agent_timer.start(5000)  # 5秒ごとに更新
        
        # タスク状態更新タイマー
        self.task_timer = QTimer()
        self.task_timer.timeout.connect(self.update_task_status)
        self.task_timer.start(3000)  # 3秒ごとに更新
        
    def update_system_metrics(self):
        """システムメトリクスの更新"""
        try:
            # CPU使用率と温度
            cpu_percent = psutil.cpu_percent()
            self.cpu_bar.setValue(int(cpu_percent))
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            self.memory_bar.setValue(int(memory.percent))
            
            # GPU使用率と温度
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                self.gpu_bar.setValue(int(gpu.load * 100))
                self.gpu_temp_label.setText(f"温度: {gpu.temperature}°C")
                
        except Exception as e:
            self.logger.error(f"システムメトリクス更新エラー: {e}")
            
    def update_agent_status(self):
        """エージェント状態の更新"""
        try:
            # エージェント情報の取得（実際の実装では非同期で取得）
            agents = [
                {
                    "id": "agent1",
                    "status": "running",
                    "tasks": 3,
                    "cpu": 25.5,
                    "memory": 128.4
                },
                {
                    "id": "agent2",
                    "status": "paused",
                    "tasks": 0,
                    "cpu": 0.0,
                    "memory": 64.2
                }
            ]
            
            self.agent_table.setRowCount(len(agents))
            for i, agent in enumerate(agents):
                self.agent_table.setItem(i, 0, QTableWidgetItem(agent["id"]))
                self.agent_table.setItem(i, 1, QTableWidgetItem(agent["status"]))
                self.agent_table.setItem(i, 2, QTableWidgetItem(str(agent["tasks"])))
                self.agent_table.setItem(i, 3, QTableWidgetItem(f"{agent['cpu']:.1f}%"))
                self.agent_table.setItem(i, 4, QTableWidgetItem(f"{agent['memory']:.1f}MB"))
                
                # 状態に応じた色付け
                if agent["status"] == "running":
                    color = QColor(200, 255, 200)  # 薄緑
                elif agent["status"] == "paused":
                    color = QColor(255, 255, 200)  # 薄黄
                else:
                    color = QColor(255, 200, 200)  # 薄赤
                    
                for j in range(5):
                    self.agent_table.item(i, j).setBackground(color)
                    
        except Exception as e:
            self.logger.error(f"エージェント状態更新エラー: {e}")
            
    def update_task_status(self):
        """タスク状態の更新"""
        try:
            # タスク情報の取得（実際の実装では非同期で取得）
            tasks = [
                {
                    "id": "task1",
                    "agent_id": "agent1",
                    "type": "browser",
                    "status": "running",
                    "progress": 75
                },
                {
                    "id": "task2",
                    "agent_id": "agent1",
                    "type": "file",
                    "status": "pending",
                    "progress": 0
                }
            ]
            
            self.task_table.setRowCount(len(tasks))
            for i, task in enumerate(tasks):
                self.task_table.setItem(i, 0, QTableWidgetItem(task["id"]))
                self.task_table.setItem(i, 1, QTableWidgetItem(task["agent_id"]))
                self.task_table.setItem(i, 2, QTableWidgetItem(task["type"]))
                self.task_table.setItem(i, 3, QTableWidgetItem(task["status"]))
                
                progress = QProgressBar()
                progress.setValue(task["progress"])
                self.task_table.setCellWidget(i, 4, progress)
                
                # 状態に応じた色付け
                if task["status"] == "running":
                    color = QColor(200, 255, 200)
                elif task["status"] == "pending":
                    color = QColor(255, 255, 200)
                else:
                    color = QColor(255, 200, 200)
                    
                for j in range(4):  # プログレスバーは除く
                    self.task_table.item(i, j).setBackground(color)
                    
        except Exception as e:
            self.logger.error(f"タスク状態更新エラー: {e}")
            
    def add_agent(self):
        """エージェントの追加"""
        try:
            self.agent_command.emit("add", {})
            self.log_message("エージェントを追加しました")
        except Exception as e:
            self.logger.error(f"エージェント追加エラー: {e}")
            
    def remove_agent(self):
        """エージェントの削除"""
        try:
            selected = self.agent_table.selectedItems()
            if selected:
                agent_id = selected[0].text()
                self.agent_command.emit("remove", {"agent_id": agent_id})
                self.log_message(f"エージェント {agent_id} を削除しました")
        except Exception as e:
            self.logger.error(f"エージェント削除エラー: {e}")
            
    def pause_agent(self):
        """エージェントの一時停止"""
        try:
            selected = self.agent_table.selectedItems()
            if selected:
                agent_id = selected[0].text()
                self.agent_command.emit("pause", {"agent_id": agent_id})
                self.log_message(f"エージェント {agent_id} を一時停止しました")
        except Exception as e:
            self.logger.error(f"エージェント一時停止エラー: {e}")
            
    def resume_agent(self):
        """エージェントの再開"""
        try:
            selected = self.agent_table.selectedItems()
            if selected:
                agent_id = selected[0].text()
                self.agent_command.emit("resume", {"agent_id": agent_id})
                self.log_message(f"エージェント {agent_id} を再開しました")
        except Exception as e:
            self.logger.error(f"エージェント再開エラー: {e}")
            
    def submit_task(self):
        """タスクの投入"""
        try:
            task_type = self.task_type_combo.currentText()
            priority = self.priority_spin.value()
            
            selected = self.agent_table.selectedItems()
            if selected:
                agent_id = selected[0].text()
                self.agent_command.emit("submit_task", {
                    "agent_id": agent_id,
                    "task_type": task_type,
                    "priority": priority
                })
                self.log_message(f"タスクを投入しました: {task_type} (優先度: {priority})")
        except Exception as e:
            self.logger.error(f"タスク投入エラー: {e}")
            
    def cancel_task(self):
        """タスクのキャンセル"""
        try:
            selected = self.task_table.selectedItems()
            if selected:
                task_id = selected[0].text()
                self.agent_command.emit("cancel_task", {"task_id": task_id})
                self.log_message(f"タスク {task_id} をキャンセルしました")
        except Exception as e:
            self.logger.error(f"タスクキャンセルエラー: {e}")
            
    def log_message(self, message: str):
        """ログメッセージの追加"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}") 
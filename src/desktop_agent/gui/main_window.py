# -*- coding: utf-8 -*-
"""Main window module."""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QComboBox,
    QTabWidget, QLineEdit
)
from PyQt6.QtCore import Qt, QTimer, QRunnable, QThreadPool, pyqtSlot
from PyQt6.QtGui import QImage, QPixmap
import cv2
import asyncio
from desktop_agent.vision.video_analyzer import VideoAnalyzer
from datetime import datetime
import psutil
import GPUtil
from desktop_agent.monitoring.hardware_monitor import HardwareMonitor

class MessageWorker(QRunnable):
    def __init__(self, langchain_manager, message, model, callback):
        super().__init__()
        self.langchain_manager = langchain_manager
        self.message = message
        self.model = model
        self.callback = callback

    @pyqtSlot()
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(self.langchain_manager.process_message(self.message, self.model))
            loop.close()
            self.callback(response, None)
        except Exception as e:
            self.callback(None, str(e))

class MainWindow(QMainWindow):
    def __init__(self, agent_manager, langchain_manager):
        super().__init__()
        self.agent_manager = agent_manager
        self.langchain_manager = langchain_manager
        self.video_analyzer = VideoAnalyzer()
        self.hardware_monitor = HardwareMonitor()
        self.thread_pool = QThreadPool()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('Desktop Agent')
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget with tabs
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Chat tab
        self.chat_tab = QWidget()
        self.tabs.addTab(self.chat_tab, "Chat")
        self._create_chat_tab()
        
        # Vision tab
        self.vision_tab = QWidget()
        self.tabs.addTab(self.vision_tab, "Vision")
        self._create_vision_tab()
        
        # Metrics tab
        self.metrics_tab = QWidget()
        self.tabs.addTab(self.metrics_tab, "Metrics")
        self._create_metrics_tab()
        
        # Setup video timer
        self.video_timer = QTimer()
        self.video_timer.timeout.connect(self.update_video_frame)
        self.is_video_running = False
        
        # Metrics timer
        self.metrics_timer = QTimer()
        self.metrics_timer.timeout.connect(self.update_metrics)
        self.metrics_timer.start(1000)  # 1 second update
        
    def _create_chat_tab(self):
        """Create chat tab"""
        chat_layout = QVBoxLayout(self.chat_tab)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_label = QLabel('Model:')
        self.model_combo = QComboBox()
        self.model_combo.addItems(['GPT-4', 'Claude-3', 'Gemini-Pro'])
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        chat_layout.addLayout(model_layout)
        
        # Chat area
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        chat_layout.addWidget(self.chat_area)
        
        # Input area
        self.input_area = QTextEdit()
        self.input_area.setMaximumHeight(100)
        chat_layout.addWidget(self.input_area)
        
        # Chat buttons
        button_layout = QHBoxLayout()
        self.send_button = QPushButton('Send')
        self.send_button.clicked.connect(self.send_message)
        self.clear_button = QPushButton('Clear')
        self.clear_button.clicked.connect(self.clear_chat)
        button_layout.addWidget(self.send_button)
        button_layout.addWidget(self.clear_button)
        chat_layout.addLayout(button_layout)
        
    def _create_vision_tab(self):
        """Create vision tab"""
        vision_layout = QVBoxLayout(self.vision_tab)
        
        # Video display
        self.video_label = QLabel()
        vision_layout.addWidget(self.video_label)
        
        # OCR result
        self.ocr_result = QTextEdit()
        self.ocr_result.setReadOnly(True)
        self.ocr_result.setMaximumHeight(150)
        vision_layout.addWidget(self.ocr_result)
        
        # Vision buttons
        vision_button_layout = QHBoxLayout()
        self.start_video_button = QPushButton('Start Video')
        self.start_video_button.clicked.connect(self.toggle_video)
        self.capture_button = QPushButton('Capture & Analyze')
        self.capture_button.clicked.connect(self.capture_and_analyze)
        vision_button_layout.addWidget(self.start_video_button)
        vision_button_layout.addWidget(self.capture_button)
        vision_layout.addLayout(vision_button_layout)
        
    def _create_metrics_tab(self):
        """Create metrics tab"""
        layout = QVBoxLayout(self.metrics_tab)
        
        # CPU/GPU information section
        temp_group = QWidget()
        temp_layout = QHBoxLayout(temp_group)
        
        # CPU temperature
        self.cpu_label = QLabel("CPU temperature: --°C")
        self.cpu_usage_label = QLabel("CPU usage: --%")
        temp_layout.addWidget(self.cpu_label)
        temp_layout.addWidget(self.cpu_usage_label)
        
        # GPU temperature
        self.gpu_label = QLabel("GPU temperature: --°C")
        self.gpu_usage_label = QLabel("GPU usage: --%")
        temp_layout.addWidget(self.gpu_label)
        temp_layout.addWidget(self.gpu_usage_label)
        
        layout.addWidget(temp_group)
        
        # Network traffic section
        network_group = QWidget()
        network_layout = QHBoxLayout(network_group)
        
        self.network_recv_label = QLabel("Received: -- MB/s")
        self.network_sent_label = QLabel("Sent: -- MB/s")
        network_layout.addWidget(self.network_recv_label)
        network_layout.addWidget(self.network_sent_label)
        
        layout.addWidget(network_group)
        
        # Memory usage
        memory_group = QWidget()
        memory_layout = QHBoxLayout(memory_group)
        
        self.memory_label = QLabel("Memory usage: --%")
        memory_layout.addWidget(self.memory_label)
        
        layout.addWidget(memory_group)
        
        # Placeholder for metrics history
        self.metrics_history = QTextEdit()
        self.metrics_history.setReadOnly(True)
        layout.addWidget(self.metrics_history)
        
        # Previous network counters
        self.last_net_io = psutil.net_io_counters()
        self.last_net_io_time = datetime.now()

    def message_callback(self, response, error):
        if error:
            self.chat_area.append(f'Error: {error}')
        else:
            self.chat_area.append(f'Agent: {response}')
            
            # YouTubeを開く処理
            message = self.last_message
            if "youtube" in message.lower():
                try:
                    import webbrowser
                    search_query = message.replace("youtube", "").strip()
                    url = f"https://www.youtube.com/results?search_query={search_query}"
                    webbrowser.open(url)
                    self.chat_area.append('YouTubeを開きました')
                except Exception as e:
                    self.chat_area.append(f'ブラウザでYouTubeを開けませんでした: {str(e)}')
        
        self.chat_area.append('')

    def send_message(self):
        message = self.input_area.toPlainText().strip()
        if message:
            self.last_message = message  # メッセージを保存
            self.chat_area.append(f'You: {message}')
            self.input_area.clear()
            
            # Get selected model
            model = self.model_combo.currentText()
            
            # Create worker and move to thread
            worker = MessageWorker(self.langchain_manager, message, model, self.message_callback)
            self.thread_pool.start(worker)
            
    def clear_chat(self):
        self.chat_area.clear()
        
    def toggle_video(self):
        if not self.is_video_running:
            try:
                self.video_analyzer.start_capture()
                self.video_timer.start(30)  # 30ms = ~33 fps
                self.is_video_running = True
                self.start_video_button.setText('Stop Video')
            except Exception as e:
                self.ocr_result.setText(f"Error starting video: {str(e)}")
        else:
            self.video_timer.stop()
            self.video_analyzer.stop_capture()
            self.is_video_running = False
            self.start_video_button.setText('Start Video')
            
    def update_video_frame(self):
        try:
            frame = self.video_analyzer.get_frame()
            # 検出結果を描画
            result = self.video_analyzer.analyze_frame(frame)
            
            # 顔の検出結果を描画
            for face in result['faces']:
                x, y = face['position']
                w, h = face['size']
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, f"Face: {face['confidence']:.2f}", 
                           (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.5, (0, 255, 0), 2)
            
            # 手の検出結果を描画
            for hand in result['hands']:
                x, y = hand['position']
                w, h = hand['size']
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv2.putText(frame, "Hand", (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame.data, width, height, bytes_per_line, 
                           QImage.Format.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(q_image))
            
            # OCR結果を更新
            if result['text']:
                self.ocr_result.setText(f"検出されたテキスト:\n{result['text']}\n\n"
                                      f"検出された顔: {len(result['faces'])}\n"
                                      f"検出された手: {len(result['hands'])}")
                
        except Exception as e:
            self.ocr_result.setText(f"フレーム更新エラー: {str(e)}")
            self.toggle_video()
            
    def capture_and_analyze(self):
        if not self.is_video_running:
            self.ocr_result.setText("Please start video first")
            return
            
        try:
            frame = self.video_analyzer.get_frame()
            result = self.video_analyzer.analyze_frame(frame)
            
            # Display results
            text = f"Detected text:\n{result['text']}\n\n"
            text += f"Detected objects: {len(result['objects'])}"
            self.ocr_result.setText(text)
            
        except Exception as e:
            self.ocr_result.setText(f"Error analyzing frame: {str(e)}")
            
    def update_metrics(self):
        """Update metrics"""
        try:
            # Get hardware metrics
            metrics = self.hardware_monitor.get_metrics()
            
            # Update CPU/GPU information
            self.cpu_label.setText(f"CPU temperature: {metrics.cpu_temp:.1f}°C")
            self.cpu_usage_label.setText(f"CPU usage: {metrics.cpu_usage:.1f}%")
            self.gpu_label.setText(f"GPU temperature: {metrics.gpu_temp:.1f}°C")
            self.gpu_usage_label.setText(f"GPU usage: {metrics.gpu_usage:.1f}%")
            
            # Update memory usage
            self.memory_label.setText(f"Memory usage: {metrics.memory_usage:.1f}%")
            
            # Calculate network traffic
            current_net_io = psutil.net_io_counters()
            current_time = datetime.now()
            time_delta = (current_time - self.last_net_io_time).total_seconds()
            
            bytes_recv = (current_net_io.bytes_recv - self.last_net_io.bytes_recv) / time_delta
            bytes_sent = (current_net_io.bytes_sent - self.last_net_io.bytes_sent) / time_delta
            
            self.network_recv_label.setText(f"Received: {bytes_recv/1024/1024:.2f} MB/s")
            self.network_sent_label.setText(f"Sent: {bytes_sent/1024/1024:.2f} MB/s")
            
            # Update history
            self.metrics_history.append(
                f"[{current_time.strftime('%H:%M:%S')}] "
                f"CPU: {metrics.cpu_temp:.1f}°C/{metrics.cpu_usage:.1f}% "
                f"GPU: {metrics.gpu_temp:.1f}°C/{metrics.gpu_usage:.1f}% "
                f"MEM: {metrics.memory_usage:.1f}%"
            )
            
            # Scroll to bottom
            self.metrics_history.verticalScrollBar().setValue(
                self.metrics_history.verticalScrollBar().maximum()
            )
            
            # Update previous values
            self.last_net_io = current_net_io
            self.last_net_io_time = current_time
            
        except Exception as e:
            print(f"Metrics update error: {e}")

    def closeEvent(self, event):
        if self.is_video_running:
            self.video_timer.stop()
            self.video_analyzer.stop_capture()
        event.accept() 
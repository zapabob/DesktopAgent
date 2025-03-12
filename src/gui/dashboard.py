import tkinter as tk
from tkinter import ttk
import asyncio
from typing import Dict, Any
import json
from datetime import datetime, timedelta
import webbrowser
from pathlib import Path
import logging
from src.monitoring.metrics_visualizer import MetricsVisualizer
from src.monitoring.alert_manager import AlertManager, AlertConfig
from src.monitoring.metrics_exporter import MetricsExporter
from tkinter import filedialog
from src.gui.async_utils import AsyncTkHelper, AsyncButton, run_with_progress

class Dashboard:
    """メトリクス可視化ダッシュボード"""
    def __init__(self, vector_store, metrics_dir: str = "metrics_viz"):
        self.vector_store = vector_store
        self.visualizer = MetricsVisualizer(metrics_dir)
        self.alert_manager = AlertManager(AlertConfig())
        self.logger = logging.getLogger(__name__)
        
        self.exporter = MetricsExporter()
        
        # メインウィンドウの設定
        self.root = tk.Tk()
        self.root.title("Vector Store Dashboard")
        self.root.geometry("800x600")
        
        # タブの作成
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both")
        
        # 各タブの作成
        self.hardware_tab = ttk.Frame(self.notebook)
        self.performance_tab = ttk.Frame(self.notebook)
        self.alerts_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.hardware_tab, text="Hardware")
        self.notebook.add(self.performance_tab, text="Performance")
        self.notebook.add(self.alerts_tab, text="Alerts")
        
        # 各タブの初期化
        self._init_hardware_tab()
        self._init_performance_tab()
        self._init_alerts_tab()
        
        # 非同期ヘルパーの初期化
        self.async_helper = AsyncTkHelper(self.root)
        self.async_helper.start()
        
        # エクスポートボタンの追加
        self._add_export_buttons()
        
        # 更新タスクの開始
        self.update_task = None
        
    def _init_hardware_tab(self):
        """ハードウェアタブの初期化"""
        # メトリクス表示領域
        self.hw_metrics_frame = ttk.LabelFrame(self.hardware_tab, text="Hardware Metrics")
        self.hw_metrics_frame.pack(padx=10, pady=5, fill="x")
        
        # CPU温度
        self.cpu_temp_label = ttk.Label(self.hw_metrics_frame, text="CPU Temperature: N/A")
        self.cpu_temp_label.pack(padx=5, pady=2)
        
        # GPU温度
        self.gpu_temp_label = ttk.Label(self.hw_metrics_frame, text="GPU Temperature: N/A")
        self.gpu_temp_label.pack(padx=5, pady=2)
        
        # メモリ使用率
        self.memory_label = ttk.Label(self.hw_metrics_frame, text="Memory Usage: N/A")
        self.memory_label.pack(padx=5, pady=2)
        
        # グラフ表示ボタン
        self.hw_graph_button = ttk.Button(
            self.hardware_tab,
            text="Show Graphs",
            command=self._show_hardware_graphs
        )
        self.hw_graph_button.pack(pady=10)
        
    def _init_performance_tab(self):
        """パフォーマンスタブの初期化"""
        # メトリクス表示領域
        self.perf_metrics_frame = ttk.LabelFrame(self.performance_tab, text="Performance Metrics")
        self.perf_metrics_frame.pack(padx=10, pady=5, fill="x")
        
        # クエリレイテンシー
        self.latency_label = ttk.Label(self.perf_metrics_frame, text="Avg Query Latency: N/A")
        self.latency_label.pack(padx=5, pady=2)
        
        # キャッシュヒット率
        self.cache_label = ttk.Label(self.perf_metrics_frame, text="Cache Hit Rate: N/A")
        self.cache_label.pack(padx=5, pady=2)
        
        # エラー率
        self.error_label = ttk.Label(self.perf_metrics_frame, text="Error Rate: N/A")
        self.error_label.pack(padx=5, pady=2)
        
        # グラフ表示ボタン
        self.perf_graph_button = ttk.Button(
            self.performance_tab,
            text="Show Graphs",
            command=self._show_performance_graphs
        )
        self.perf_graph_button.pack(pady=10)
        
    def _init_alerts_tab(self):
        """アラートタブの初期化"""
        # アラート表示領域
        self.alerts_frame = ttk.LabelFrame(self.alerts_tab, text="Active Alerts")
        self.alerts_frame.pack(padx=10, pady=5, fill="both", expand=True)
        
        # アラートリスト
        self.alerts_tree = ttk.Treeview(
            self.alerts_frame,
            columns=("Severity", "Type", "Message", "Time"),
            show="headings"
        )
        
        self.alerts_tree.heading("Severity", text="Severity")
        self.alerts_tree.heading("Type", text="Type")
        self.alerts_tree.heading("Message", text="Message")
        self.alerts_tree.heading("Time", text="Time")
        
        self.alerts_tree.pack(padx=5, pady=5, fill="both", expand=True)
        
    def _add_export_buttons(self):
        """エクスポートボタンの追加"""
        # ハードウェアタブ
        self.hw_export_frame = ttk.Frame(self.hardware_tab)
        self.hw_export_frame.pack(pady=5)
        
        AsyncButton(
            self.hw_export_frame,
            self.async_helper,
            text="Export to CSV",
            command=lambda: self._export_hardware_metrics("csv")
        ).pack(side="left", padx=5)
        
        AsyncButton(
            self.hw_export_frame,
            self.async_helper,
            text="Export to JSON",
            command=lambda: self._export_hardware_metrics("json")
        ).pack(side="left", padx=5)
        
        # パフォーマンスタブ
        self.perf_export_frame = ttk.Frame(self.performance_tab)
        self.perf_export_frame.pack(pady=5)
        
        AsyncButton(
            self.perf_export_frame,
            self.async_helper,
            text="Export to CSV",
            command=lambda: self._export_performance_metrics("csv")
        ).pack(side="left", padx=5)
        
        AsyncButton(
            self.perf_export_frame,
            self.async_helper,
            text="Export to JSON",
            command=lambda: self._export_performance_metrics("json")
        ).pack(side="left", padx=5)
        
        # アラートタブ
        self.alert_export_frame = ttk.Frame(self.alerts_tab)
        self.alert_export_frame.pack(pady=5)
        
        AsyncButton(
            self.alert_export_frame,
            self.async_helper,
            text="Export Alerts",
            command=self._export_alerts
        ).pack(side="left", padx=5)
        
    async def _update_metrics(self):
        """メトリクスの定期更新"""
        while True:
            try:
                # ハードウェアメトリクスの更新
                hw_metrics = await self.vector_store.get_hardware_metrics()
                self.cpu_temp_label.config(
                    text=f"CPU Temperature: {hw_metrics['cpu_temperature']}°C"
                )
                self.gpu_temp_label.config(
                    text=f"GPU Temperature: {hw_metrics['gpu_temperature']}°C"
                )
                self.memory_label.config(
                    text=f"Memory Usage: {hw_metrics['memory_usage']}%"
                )
                
                # パフォーマンスメトリクスの更新
                perf_metrics = await self.vector_store.get_metrics()
                self.latency_label.config(
                    text=f"Avg Query Latency: {perf_metrics['avg_query_latency']:.3f}s"
                )
                self.cache_label.config(
                    text=f"Cache Hit Rate: {perf_metrics['cache_hit_rate']*100:.1f}%"
                )
                self.error_label.config(
                    text=f"Error Rate: {perf_metrics['error_rate']*100:.1f}%"
                )
                
                # アラートのチェック
                hw_alerts = await self.alert_manager.check_hardware_metrics(hw_metrics)
                perf_alerts = await self.alert_manager.check_performance_metrics(perf_metrics)
                
                await self.alert_manager.process_alerts(hw_alerts + perf_alerts)
                self._update_alerts_tree()
                
                # プロットの更新
                plots = self.visualizer.save_plots(hw_metrics, perf_metrics)
                self._latest_plots = plots
                
            except Exception as e:
                self.logger.error(f"メトリクス更新エラー: {e}")
                
            await asyncio.sleep(5)  # 5秒間隔で更新
            
    def _update_alerts_tree(self):
        """アラートツリーの更新"""
        # 既存のアラートをクリア
        for item in self.alerts_tree.get_children():
            self.alerts_tree.delete(item)
            
        # アクティブなアラートを追加
        for alert in self.alert_manager.get_active_alerts():
            self.alerts_tree.insert(
                "",
                "end",
                values=(
                    alert.severity.upper(),
                    alert.type,
                    alert.message,
                    alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                )
            )
            
    def _show_hardware_graphs(self):
        """ハードウェアグラフの表示"""
        if hasattr(self, '_latest_plots'):
            webbrowser.open(f"file://{self._latest_plots['temperature']}")
            webbrowser.open(f"file://{self._latest_plots['usage']}")
            
    def _show_performance_graphs(self):
        """パフォーマンスグラフの表示"""
        if hasattr(self, '_latest_plots'):
            webbrowser.open(f"file://{self._latest_plots['performance']}")
            
    def start(self):
        """ダッシュボードの起動"""
        # 更新タスクの開始
        self.update_task = asyncio.create_task(self._update_metrics())
        
        # メインループの開始
        self.root.mainloop()
        
    def stop(self):
        """ダッシュボードの停止"""
        if self.update_task:
            self.update_task.cancel()
        self.async_helper.stop()
        self.root.quit()
        
    async def _export_hardware_metrics(self, format_type: str):
        """ハードウェアメトリクスのエクスポート"""
        try:
            async def export_task():
                hw_metrics = await self.vector_store.get_hardware_metrics()
                
                if format_type == "csv":
                    file_path = filedialog.asksaveasfilename(
                        defaultextension=".csv",
                        filetypes=[("CSV files", "*.csv")]
                    )
                    if file_path:
                        return await run_with_progress(
                            self.root,
                            "エクスポート中",
                            "ハードウェアメトリクスをエクスポートしています...",
                            self.exporter.async_export_to_csv,
                            hw_metrics,
                            file_path
                        )
                else:  # json
                    file_path = filedialog.asksaveasfilename(
                        defaultextension=".json",
                        filetypes=[("JSON files", "*.json")]
                    )
                    if file_path:
                        return await run_with_progress(
                            self.root,
                            "エクスポート中",
                            "ハードウェアメトリクスをエクスポートしています...",
                            self.exporter.async_export_to_json,
                            hw_metrics,
                            file_path
                        )
                        
            await export_task()
            
        except Exception as e:
            self.logger.error(f"ハードウェアメトリクスエクスポートエラー: {e}")
            
    async def _export_performance_metrics(self, format_type: str):
        """パフォーマンスメトリクスのエクスポート"""
        try:
            async def export_task():
                perf_metrics = await self.vector_store.get_metrics()
                
                if format_type == "csv":
                    file_path = filedialog.asksaveasfilename(
                        defaultextension=".csv",
                        filetypes=[("CSV files", "*.csv")]
                    )
                    if file_path:
                        return await run_with_progress(
                            self.root,
                            "エクスポート中",
                            "パフォーマンスメトリクスをエクスポートしています...",
                            self.exporter.async_export_to_csv,
                            perf_metrics,
                            file_path
                        )
                else:  # json
                    file_path = filedialog.asksaveasfilename(
                        defaultextension=".json",
                        filetypes=[("JSON files", "*.json")]
                    )
                    if file_path:
                        return await run_with_progress(
                            self.root,
                            "エクスポート中",
                            "パフォーマンスメトリクスをエクスポートしています...",
                            self.exporter.async_export_to_json,
                            perf_metrics,
                            file_path
                        )
                        
            await export_task()
            
        except Exception as e:
            self.logger.error(f"パフォーマンスメトリクスエクスポートエラー: {e}")
            
    async def _export_alerts(self):
        """アラート履歴のエクスポート"""
        try:
            async def export_task():
                alerts = await self.alert_manager.get_alert_history()
                
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv")]
                )
                if file_path:
                    return await run_with_progress(
                        self.root,
                        "エクスポート中",
                        "アラート履歴をエクスポートしています...",
                        self.exporter.async_export_alert_history,
                        alerts,
                        file_path
                    )
                    
            await export_task()
            
        except Exception as e:
            self.logger.error(f"アラートエクスポートエラー: {e}") 
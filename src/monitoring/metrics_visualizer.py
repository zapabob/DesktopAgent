<<<<<<< HEAD
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List, Any
from datetime import datetime
import json
from pathlib import Path
import logging

class MetricsVisualizer:
    """メトリクス可視化クラス"""
    def __init__(self, output_dir: str = "metrics_viz"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
    def create_temperature_plot(self, history: Dict[str, List[Any]]) -> go.Figure:
        """温度履歴のプロット作成"""
        try:
            fig = go.Figure()
            
            # CPU温度
            fig.add_trace(go.Scatter(
                x=history["timestamps"],
                y=history["cpu_temps"],
                name="CPU Temperature",
                line=dict(color="red")
            ))
            
            # GPU温度
            fig.add_trace(go.Scatter(
                x=history["timestamps"],
                y=history["gpu_temps"],
                name="GPU Temperature",
                line=dict(color="blue")
            ))
            
            fig.update_layout(
                title="Hardware Temperature History",
                xaxis_title="Time",
                yaxis_title="Temperature (°C)",
                hovermode="x unified"
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"温度プロット作成エラー: {e}")
            raise
            
    def create_usage_plot(self, history: Dict[str, List[Any]]) -> go.Figure:
        """使用率履歴のプロット作成"""
        try:
            fig = make_subplots(
                rows=3, cols=1,
                subplot_titles=("CPU Usage", "GPU Usage", "Memory Usage")
            )
            
            # CPU使用率
            fig.add_trace(
                go.Scatter(
                    x=history["timestamps"],
                    y=history["cpu_usage"],
                    name="CPU Usage",
                    line=dict(color="red")
                ),
                row=1, col=1
            )
            
            # GPU使用率
            fig.add_trace(
                go.Scatter(
                    x=history["timestamps"],
                    y=history["gpu_usage"],
                    name="GPU Usage",
                    line=dict(color="blue")
                ),
                row=2, col=1
            )
            
            # メモリ使用率
            fig.add_trace(
                go.Scatter(
                    x=history["timestamps"],
                    y=history["memory_usage"],
                    name="Memory Usage",
                    line=dict(color="green")
                ),
                row=3, col=1
            )
            
            fig.update_layout(
                height=900,
                title_text="Hardware Usage History",
                showlegend=True
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"使用率プロット作成エラー: {e}")
            raise
            
    def create_performance_plot(self, metrics: Dict[str, Any]) -> go.Figure:
        """パフォーマンスメトリクスのプロット作成"""
        try:
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=(
                    "Query Latency",
                    "Insert Latency",
                    "Cache Hit Rate",
                    "Error Rate"
                )
            )
            
            # クエリレイテンシー
            fig.add_trace(
                go.Box(
                    y=metrics["query_latencies"],
                    name="Query Latency"
                ),
                row=1, col=1
            )
            
            # 挿入レイテンシー
            fig.add_trace(
                go.Box(
                    y=metrics["insert_latencies"],
                    name="Insert Latency"
                ),
                row=1, col=2
            )
            
            # キャッシュヒット率
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=metrics["cache_hit_rate"] * 100,
                    title={"text": "Cache Hit Rate (%)"},
                    gauge={"axis": {"range": [0, 100]}}
                ),
                row=2, col=1
            )
            
            # エラー率
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=metrics["error_rate"] * 100,
                    title={"text": "Error Rate (%)"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": "red"}
                    }
                ),
                row=2, col=2
            )
            
            fig.update_layout(
                height=800,
                title_text="Performance Metrics",
                showlegend=True
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"パフォーマンスプロット作成エラー: {e}")
            raise
            
    def save_plots(self, hardware_metrics: Dict[str, Any],
                  performance_metrics: Dict[str, Any]) -> Dict[str, str]:
        """全プロットの保存"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plots = {}
            
            # 温度プロット
            temp_fig = self.create_temperature_plot(hardware_metrics)
            temp_path = self.output_dir / f"temperature_{timestamp}.html"
            temp_fig.write_html(str(temp_path))
            plots["temperature"] = str(temp_path)
            
            # 使用率プロット
            usage_fig = self.create_usage_plot(hardware_metrics)
            usage_path = self.output_dir / f"usage_{timestamp}.html"
            usage_fig.write_html(str(usage_path))
            plots["usage"] = str(usage_path)
            
            # パフォーマンスプロット
            perf_fig = self.create_performance_plot(performance_metrics)
            perf_path = self.output_dir / f"performance_{timestamp}.html"
            perf_fig.write_html(str(perf_path))
            plots["performance"] = str(perf_path)
            
            # メタデータの保存
            metadata = {
                "timestamp": timestamp,
                "plots": plots
            }
            with open(self.output_dir / f"metadata_{timestamp}.json", "w") as f:
                json.dump(metadata, f, indent=2)
                
            return plots
            
        except Exception as e:
            self.logger.error(f"プロット保存エラー: {e}")
=======
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List, Any
from datetime import datetime
import json
from pathlib import Path
import logging

class MetricsVisualizer:
    """メトリクス可視化クラス"""
    def __init__(self, output_dir: str = "metrics_viz"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
    def create_temperature_plot(self, history: Dict[str, List[Any]]) -> go.Figure:
        """温度履歴のプロット作成"""
        try:
            fig = go.Figure()
            
            # CPU温度
            fig.add_trace(go.Scatter(
                x=history["timestamps"],
                y=history["cpu_temps"],
                name="CPU Temperature",
                line=dict(color="red")
            ))
            
            # GPU温度
            fig.add_trace(go.Scatter(
                x=history["timestamps"],
                y=history["gpu_temps"],
                name="GPU Temperature",
                line=dict(color="blue")
            ))
            
            fig.update_layout(
                title="Hardware Temperature History",
                xaxis_title="Time",
                yaxis_title="Temperature (°C)",
                hovermode="x unified"
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"温度プロット作成エラー: {e}")
            raise
            
    def create_usage_plot(self, history: Dict[str, List[Any]]) -> go.Figure:
        """使用率履歴のプロット作成"""
        try:
            fig = make_subplots(
                rows=3, cols=1,
                subplot_titles=("CPU Usage", "GPU Usage", "Memory Usage")
            )
            
            # CPU使用率
            fig.add_trace(
                go.Scatter(
                    x=history["timestamps"],
                    y=history["cpu_usage"],
                    name="CPU Usage",
                    line=dict(color="red")
                ),
                row=1, col=1
            )
            
            # GPU使用率
            fig.add_trace(
                go.Scatter(
                    x=history["timestamps"],
                    y=history["gpu_usage"],
                    name="GPU Usage",
                    line=dict(color="blue")
                ),
                row=2, col=1
            )
            
            # メモリ使用率
            fig.add_trace(
                go.Scatter(
                    x=history["timestamps"],
                    y=history["memory_usage"],
                    name="Memory Usage",
                    line=dict(color="green")
                ),
                row=3, col=1
            )
            
            fig.update_layout(
                height=900,
                title_text="Hardware Usage History",
                showlegend=True
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"使用率プロット作成エラー: {e}")
            raise
            
    def create_performance_plot(self, metrics: Dict[str, Any]) -> go.Figure:
        """パフォーマンスメトリクスのプロット作成"""
        try:
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=(
                    "Query Latency",
                    "Insert Latency",
                    "Cache Hit Rate",
                    "Error Rate"
                )
            )
            
            # クエリレイテンシー
            fig.add_trace(
                go.Box(
                    y=metrics["query_latencies"],
                    name="Query Latency"
                ),
                row=1, col=1
            )
            
            # 挿入レイテンシー
            fig.add_trace(
                go.Box(
                    y=metrics["insert_latencies"],
                    name="Insert Latency"
                ),
                row=1, col=2
            )
            
            # キャッシュヒット率
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=metrics["cache_hit_rate"] * 100,
                    title={"text": "Cache Hit Rate (%)"},
                    gauge={"axis": {"range": [0, 100]}}
                ),
                row=2, col=1
            )
            
            # エラー率
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=metrics["error_rate"] * 100,
                    title={"text": "Error Rate (%)"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": "red"}
                    }
                ),
                row=2, col=2
            )
            
            fig.update_layout(
                height=800,
                title_text="Performance Metrics",
                showlegend=True
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"パフォーマンスプロット作成エラー: {e}")
            raise
            
    def save_plots(self, hardware_metrics: Dict[str, Any],
                  performance_metrics: Dict[str, Any]) -> Dict[str, str]:
        """全プロットの保存"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plots = {}
            
            # 温度プロット
            temp_fig = self.create_temperature_plot(hardware_metrics)
            temp_path = self.output_dir / f"temperature_{timestamp}.html"
            temp_fig.write_html(str(temp_path))
            plots["temperature"] = str(temp_path)
            
            # 使用率プロット
            usage_fig = self.create_usage_plot(hardware_metrics)
            usage_path = self.output_dir / f"usage_{timestamp}.html"
            usage_fig.write_html(str(usage_path))
            plots["usage"] = str(usage_path)
            
            # パフォーマンスプロット
            perf_fig = self.create_performance_plot(performance_metrics)
            perf_path = self.output_dir / f"performance_{timestamp}.html"
            perf_fig.write_html(str(perf_path))
            plots["performance"] = str(perf_path)
            
            # メタデータの保存
            metadata = {
                "timestamp": timestamp,
                "plots": plots
            }
            with open(self.output_dir / f"metadata_{timestamp}.json", "w") as f:
                json.dump(metadata, f, indent=2)
                
            return plots
            
        except Exception as e:
            self.logger.error(f"プロット保存エラー: {e}")
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
            raise 
<<<<<<< HEAD
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List, Any, Optional
import json
from pathlib import Path
from datetime import datetime
import logging

class CustomGraph:
    """カスタムグラフ定義クラス"""
    def __init__(self,
                name: str,
                graph_type: str,
                metrics: List[str],
                layout: Optional[Dict[str, Any]] = None):
        self.name = name
        self.graph_type = graph_type
        self.metrics = metrics
        self.layout = layout or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "name": self.name,
            "graph_type": self.graph_type,
            "metrics": self.metrics,
            "layout": self.layout
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomGraph":
        """辞書形式から作成"""
        return cls(
            name=data["name"],
            graph_type=data["graph_type"],
            metrics=data["metrics"],
            layout=data.get("layout", {})
        )

class CustomGraphManager:
    """カスタムグラフ管理クラス"""
    def __init__(self, config_dir: str = "graph_configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.graphs: Dict[str, CustomGraph] = {}
        self._load_configs()
        
    def _load_configs(self):
        """設定ファイルの読み込み"""
        try:
            for config_file in self.config_dir.glob("*.json"):
                try:
                    with open(config_file) as f:
                        data = json.load(f)
                        graph = CustomGraph.from_dict(data)
                        self.graphs[graph.name] = graph
                except Exception as e:
                    self.logger.error(f"グラフ設定読み込みエラー: {config_file}: {e}")
        except Exception as e:
            self.logger.error(f"グラフ設定ディレクトリ読み込みエラー: {e}")
            
    def save_graph(self, graph: CustomGraph):
        """グラフ設定の保存"""
        try:
            config_path = self.config_dir / f"{graph.name}.json"
            with open(config_path, "w") as f:
                json.dump(graph.to_dict(), f, indent=2)
            self.graphs[graph.name] = graph
        except Exception as e:
            self.logger.error(f"グラフ設定保存エラー: {e}")
            raise
            
    def delete_graph(self, name: str):
        """グラフ設定の削除"""
        try:
            config_path = self.config_dir / f"{name}.json"
            if config_path.exists():
                config_path.unlink()
            self.graphs.pop(name, None)
        except Exception as e:
            self.logger.error(f"グラフ設定削除エラー: {e}")
            raise
            
    def get_graph(self, name: str) -> Optional[CustomGraph]:
        """グラフ設定の取得"""
        return self.graphs.get(name)
        
    def list_graphs(self) -> List[str]:
        """利用可能なグラフ一覧を取得"""
        return list(self.graphs.keys())
        
    def create_graph(self, graph: CustomGraph,
                   metrics: Dict[str, Any]) -> go.Figure:
        """グラフの作成"""
        try:
            if graph.graph_type == "line":
                return self._create_line_graph(graph, metrics)
            elif graph.graph_type == "scatter":
                return self._create_scatter_graph(graph, metrics)
            elif graph.graph_type == "bar":
                return self._create_bar_graph(graph, metrics)
            elif graph.graph_type == "box":
                return self._create_box_graph(graph, metrics)
            else:
                raise ValueError(f"未対応のグラフタイプ: {graph.graph_type}")
                
        except Exception as e:
            self.logger.error(f"グラフ作成エラー: {e}")
            raise
            
    def _create_line_graph(self, graph: CustomGraph,
                        metrics: Dict[str, Any]) -> go.Figure:
        """折れ線グラフの作成"""
        fig = go.Figure()
        
        for metric in graph.metrics:
            if metric in metrics:
                fig.add_trace(go.Scatter(
                    y=metrics[metric],
                    name=metric,
                    mode="lines+markers"
                ))
                
        fig.update_layout(**graph.layout)
        return fig
        
    def _create_scatter_graph(self, graph: CustomGraph,
                           metrics: Dict[str, Any]) -> go.Figure:
        """散布図の作成"""
        if len(graph.metrics) != 2:
            raise ValueError("散布図には2つのメトリクスが必要です")
            
        x_metric, y_metric = graph.metrics
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=metrics.get(x_metric, []),
            y=metrics.get(y_metric, []),
            mode="markers",
            name=f"{x_metric} vs {y_metric}"
        ))
        
        fig.update_layout(**graph.layout)
        return fig
        
    def _create_bar_graph(self, graph: CustomGraph,
                       metrics: Dict[str, Any]) -> go.Figure:
        """棒グラフの作成"""
        fig = go.Figure()
        
        for metric in graph.metrics:
            if metric in metrics:
                fig.add_trace(go.Bar(
                    y=metrics[metric],
                    name=metric
                ))
                
        fig.update_layout(**graph.layout)
        return fig
        
    def _create_box_graph(self, graph: CustomGraph,
                       metrics: Dict[str, Any]) -> go.Figure:
        """箱ひげ図の作成"""
        fig = go.Figure()
        
        for metric in graph.metrics:
            if metric in metrics:
                fig.add_trace(go.Box(
                    y=metrics[metric],
                    name=metric
                ))
                
        fig.update_layout(**graph.layout)
=======
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List, Any, Optional
import json
from pathlib import Path
from datetime import datetime
import logging

class CustomGraph:
    """カスタムグラフ定義クラス"""
    def __init__(self,
                name: str,
                graph_type: str,
                metrics: List[str],
                layout: Optional[Dict[str, Any]] = None):
        self.name = name
        self.graph_type = graph_type
        self.metrics = metrics
        self.layout = layout or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "name": self.name,
            "graph_type": self.graph_type,
            "metrics": self.metrics,
            "layout": self.layout
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomGraph":
        """辞書形式から作成"""
        return cls(
            name=data["name"],
            graph_type=data["graph_type"],
            metrics=data["metrics"],
            layout=data.get("layout", {})
        )

class CustomGraphManager:
    """カスタムグラフ管理クラス"""
    def __init__(self, config_dir: str = "graph_configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.graphs: Dict[str, CustomGraph] = {}
        self._load_configs()
        
    def _load_configs(self):
        """設定ファイルの読み込み"""
        try:
            for config_file in self.config_dir.glob("*.json"):
                try:
                    with open(config_file) as f:
                        data = json.load(f)
                        graph = CustomGraph.from_dict(data)
                        self.graphs[graph.name] = graph
                except Exception as e:
                    self.logger.error(f"グラフ設定読み込みエラー: {config_file}: {e}")
        except Exception as e:
            self.logger.error(f"グラフ設定ディレクトリ読み込みエラー: {e}")
            
    def save_graph(self, graph: CustomGraph):
        """グラフ設定の保存"""
        try:
            config_path = self.config_dir / f"{graph.name}.json"
            with open(config_path, "w") as f:
                json.dump(graph.to_dict(), f, indent=2)
            self.graphs[graph.name] = graph
        except Exception as e:
            self.logger.error(f"グラフ設定保存エラー: {e}")
            raise
            
    def delete_graph(self, name: str):
        """グラフ設定の削除"""
        try:
            config_path = self.config_dir / f"{name}.json"
            if config_path.exists():
                config_path.unlink()
            self.graphs.pop(name, None)
        except Exception as e:
            self.logger.error(f"グラフ設定削除エラー: {e}")
            raise
            
    def get_graph(self, name: str) -> Optional[CustomGraph]:
        """グラフ設定の取得"""
        return self.graphs.get(name)
        
    def list_graphs(self) -> List[str]:
        """利用可能なグラフ一覧を取得"""
        return list(self.graphs.keys())
        
    def create_graph(self, graph: CustomGraph,
                   metrics: Dict[str, Any]) -> go.Figure:
        """グラフの作成"""
        try:
            if graph.graph_type == "line":
                return self._create_line_graph(graph, metrics)
            elif graph.graph_type == "scatter":
                return self._create_scatter_graph(graph, metrics)
            elif graph.graph_type == "bar":
                return self._create_bar_graph(graph, metrics)
            elif graph.graph_type == "box":
                return self._create_box_graph(graph, metrics)
            else:
                raise ValueError(f"未対応のグラフタイプ: {graph.graph_type}")
                
        except Exception as e:
            self.logger.error(f"グラフ作成エラー: {e}")
            raise
            
    def _create_line_graph(self, graph: CustomGraph,
                        metrics: Dict[str, Any]) -> go.Figure:
        """折れ線グラフの作成"""
        fig = go.Figure()
        
        for metric in graph.metrics:
            if metric in metrics:
                fig.add_trace(go.Scatter(
                    y=metrics[metric],
                    name=metric,
                    mode="lines+markers"
                ))
                
        fig.update_layout(**graph.layout)
        return fig
        
    def _create_scatter_graph(self, graph: CustomGraph,
                           metrics: Dict[str, Any]) -> go.Figure:
        """散布図の作成"""
        if len(graph.metrics) != 2:
            raise ValueError("散布図には2つのメトリクスが必要です")
            
        x_metric, y_metric = graph.metrics
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=metrics.get(x_metric, []),
            y=metrics.get(y_metric, []),
            mode="markers",
            name=f"{x_metric} vs {y_metric}"
        ))
        
        fig.update_layout(**graph.layout)
        return fig
        
    def _create_bar_graph(self, graph: CustomGraph,
                       metrics: Dict[str, Any]) -> go.Figure:
        """棒グラフの作成"""
        fig = go.Figure()
        
        for metric in graph.metrics:
            if metric in metrics:
                fig.add_trace(go.Bar(
                    y=metrics[metric],
                    name=metric
                ))
                
        fig.update_layout(**graph.layout)
        return fig
        
    def _create_box_graph(self, graph: CustomGraph,
                       metrics: Dict[str, Any]) -> go.Figure:
        """箱ひげ図の作成"""
        fig = go.Figure()
        
        for metric in graph.metrics:
            if metric in metrics:
                fig.add_trace(go.Box(
                    y=metrics[metric],
                    name=metric
                ))
                
        fig.update_layout(**graph.layout)
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
        return fig 
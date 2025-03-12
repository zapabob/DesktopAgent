<<<<<<< HEAD
from typing import Dict, Any, List
from src.visualization.custom_graphs import CustomGraph

class GraphTemplate:
    """グラフテンプレート定義"""
    @staticmethod
    def hardware_monitoring() -> CustomGraph:
        """ハードウェアモニタリング用テンプレート"""
        return CustomGraph(
            name="Hardware Monitoring",
            graph_type="line",
            metrics=["cpu_temperature", "gpu_temperature", "memory_usage"],
            layout={
                "height": 600,
                "showlegend": True,
                "yaxis_title": "Value",
                "xaxis_title": "Time",
                "hovermode": "x unified",
                "updatemenus": [{
                    "buttons": [
                        {"label": "All",
                         "method": "update",
                         "args": [{"visible": [True, True, True]}]},
                        {"label": "CPU",
                         "method": "update",
                         "args": [{"visible": [True, False, False]}]},
                        {"label": "GPU",
                         "method": "update",
                         "args": [{"visible": [False, True, False]}]},
                        {"label": "Memory",
                         "method": "update",
                         "args": [{"visible": [False, False, True]}]}
                    ],
                    "direction": "down",
                    "showactive": True,
                    "x": 0.1,
                    "y": 1.1
                }]
            }
        )
        
    @staticmethod
    def performance_metrics() -> CustomGraph:
        """パフォーマンスメトリクス用テンプレート"""
        return CustomGraph(
            name="Performance Metrics",
            graph_type="box",
            metrics=["query_latencies", "insert_latencies", "update_latencies"],
            layout={
                "height": 500,
                "showlegend": True,
                "yaxis_title": "Time (seconds)",
                "boxmode": "group",
                "annotations": [{
                    "text": "Latency Distribution",
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 1.05,
                    "showarrow": False
                }]
            }
        )
        
    @staticmethod
    def error_analysis() -> CustomGraph:
        """エラー分析用テンプレート"""
        return CustomGraph(
            name="Error Analysis",
            graph_type="bar",
            metrics=["error_count", "error_rate"],
            layout={
                "height": 400,
                "showlegend": True,
                "barmode": "overlay",
                "yaxis": {
                    "title": "Count",
                    "side": "left"
                },
                "yaxis2": {
                    "title": "Rate (%)",
                    "side": "right",
                    "overlaying": "y",
                    "tickformat": ".2%"
                }
            }
        )
        
    @staticmethod
    def resource_correlation() -> CustomGraph:
        """リソース相関分析用テンプレート"""
        return CustomGraph(
            name="Resource Correlation",
            graph_type="scatter",
            metrics=["cpu_usage", "memory_usage"],
            layout={
                "height": 500,
                "showlegend": True,
                "xaxis_title": "CPU Usage (%)",
                "yaxis_title": "Memory Usage (%)",
                "hovermode": "closest",
                "annotations": [{
                    "text": "Resource Usage Correlation",
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 1.05,
                    "showarrow": False
                }]
            }
        )

class TemplateManager:
    """テンプレート管理クラス"""
    @staticmethod
    def get_available_templates() -> List[str]:
        """利用可能なテンプレート一覧を取得"""
        return [
            "hardware_monitoring",
            "performance_metrics",
            "error_analysis",
            "resource_correlation"
        ]
        
    @staticmethod
    def create_from_template(template_name: str) -> CustomGraph:
        """テンプレートからグラフを作成"""
        templates = {
            "hardware_monitoring": GraphTemplate.hardware_monitoring,
            "performance_metrics": GraphTemplate.performance_metrics,
            "error_analysis": GraphTemplate.error_analysis,
            "resource_correlation": GraphTemplate.resource_correlation
        }
        
        if template_name not in templates:
            raise ValueError(f"未対応のテンプレート: {template_name}")
            
=======
from typing import Dict, Any, List
from src.visualization.custom_graphs import CustomGraph

class GraphTemplate:
    """グラフテンプレート定義"""
    @staticmethod
    def hardware_monitoring() -> CustomGraph:
        """ハードウェアモニタリング用テンプレート"""
        return CustomGraph(
            name="Hardware Monitoring",
            graph_type="line",
            metrics=["cpu_temperature", "gpu_temperature", "memory_usage"],
            layout={
                "height": 600,
                "showlegend": True,
                "yaxis_title": "Value",
                "xaxis_title": "Time",
                "hovermode": "x unified",
                "updatemenus": [{
                    "buttons": [
                        {"label": "All",
                         "method": "update",
                         "args": [{"visible": [True, True, True]}]},
                        {"label": "CPU",
                         "method": "update",
                         "args": [{"visible": [True, False, False]}]},
                        {"label": "GPU",
                         "method": "update",
                         "args": [{"visible": [False, True, False]}]},
                        {"label": "Memory",
                         "method": "update",
                         "args": [{"visible": [False, False, True]}]}
                    ],
                    "direction": "down",
                    "showactive": True,
                    "x": 0.1,
                    "y": 1.1
                }]
            }
        )
        
    @staticmethod
    def performance_metrics() -> CustomGraph:
        """パフォーマンスメトリクス用テンプレート"""
        return CustomGraph(
            name="Performance Metrics",
            graph_type="box",
            metrics=["query_latencies", "insert_latencies", "update_latencies"],
            layout={
                "height": 500,
                "showlegend": True,
                "yaxis_title": "Time (seconds)",
                "boxmode": "group",
                "annotations": [{
                    "text": "Latency Distribution",
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 1.05,
                    "showarrow": False
                }]
            }
        )
        
    @staticmethod
    def error_analysis() -> CustomGraph:
        """エラー分析用テンプレート"""
        return CustomGraph(
            name="Error Analysis",
            graph_type="bar",
            metrics=["error_count", "error_rate"],
            layout={
                "height": 400,
                "showlegend": True,
                "barmode": "overlay",
                "yaxis": {
                    "title": "Count",
                    "side": "left"
                },
                "yaxis2": {
                    "title": "Rate (%)",
                    "side": "right",
                    "overlaying": "y",
                    "tickformat": ".2%"
                }
            }
        )
        
    @staticmethod
    def resource_correlation() -> CustomGraph:
        """リソース相関分析用テンプレート"""
        return CustomGraph(
            name="Resource Correlation",
            graph_type="scatter",
            metrics=["cpu_usage", "memory_usage"],
            layout={
                "height": 500,
                "showlegend": True,
                "xaxis_title": "CPU Usage (%)",
                "yaxis_title": "Memory Usage (%)",
                "hovermode": "closest",
                "annotations": [{
                    "text": "Resource Usage Correlation",
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 1.05,
                    "showarrow": False
                }]
            }
        )

class TemplateManager:
    """テンプレート管理クラス"""
    @staticmethod
    def get_available_templates() -> List[str]:
        """利用可能なテンプレート一覧を取得"""
        return [
            "hardware_monitoring",
            "performance_metrics",
            "error_analysis",
            "resource_correlation"
        ]
        
    @staticmethod
    def create_from_template(template_name: str) -> CustomGraph:
        """テンプレートからグラフを作成"""
        templates = {
            "hardware_monitoring": GraphTemplate.hardware_monitoring,
            "performance_metrics": GraphTemplate.performance_metrics,
            "error_analysis": GraphTemplate.error_analysis,
            "resource_correlation": GraphTemplate.resource_correlation
        }
        
        if template_name not in templates:
            raise ValueError(f"未対応のテンプレート: {template_name}")
            
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
        return templates[template_name]() 
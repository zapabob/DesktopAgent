import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from pathlib import Path
import logging
from jinja2 import Template
import plotly.io as pio
from src.visualization.custom_graphs import CustomGraphManager
from src.analysis.metrics_analyzer import MetricsAnalyzer

class ReportGenerator:
    """レポート生成クラス"""
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.graph_manager = CustomGraphManager()
        self.analyzer = MetricsAnalyzer()
        
    def generate_report(self, metrics: Dict[str, Any],
                      report_type: str = "html") -> str:
        """レポートの生成"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 分析の実行
            performance_analysis = self.analyzer.analyze_performance(metrics)
            hardware_analysis = self.analyzer.analyze_hardware(metrics)
            
            # グラフの生成
            graphs = self._generate_graphs(metrics)
            
            if report_type == "html":
                return self._generate_html_report(
                    timestamp,
                    metrics,
                    performance_analysis,
                    hardware_analysis,
                    graphs
                )
            elif report_type == "json":
                return self._generate_json_report(
                    timestamp,
                    metrics,
                    performance_analysis,
                    hardware_analysis
                )
            else:
                raise ValueError(f"未対応のレポート形式: {report_type}")
                
        except Exception as e:
            self.logger.error(f"レポート生成エラー: {e}")
            raise
            
    def _generate_graphs(self, metrics: Dict[str, Any]) -> Dict[str, str]:
        """グラフの生成"""
        graphs = {}
        
        try:
            # テンプレートからグラフを生成
            for template_name in self.graph_manager.get_available_templates():
                graph = self.graph_manager.create_from_template(template_name)
                fig = self.graph_manager.create_graph(graph, metrics)
                
                # HTMLとして保存
                graph_path = self.output_dir / f"graph_{template_name}.html"
                fig.write_html(str(graph_path))
                graphs[template_name] = str(graph_path)
                
        except Exception as e:
            self.logger.error(f"グラフ生成エラー: {e}")
            
        return graphs
        
    def _generate_html_report(self, timestamp: str,
                           metrics: Dict[str, Any],
                           performance_analysis: Dict[str, Any],
                           hardware_analysis: Dict[str, Any],
                           graphs: Dict[str, str]) -> str:
        """HTMLレポートの生成"""
        try:
            template = Template("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>System Metrics Report</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    h1, h2 { color: #333; }
                    .section { margin: 20px 0; padding: 10px; border: 1px solid #ddd; }
                    .metric { margin: 10px 0; }
                    .status-normal { color: green; }
                    .status-warning { color: orange; }
                    .status-critical { color: red; }
                    .graph { margin: 20px 0; }
                </style>
            </head>
            <body>
                <h1>System Metrics Report</h1>
                <p>Generated at: {{ timestamp }}</p>
                
                <div class="section">
                    <h2>Hardware Analysis</h2>
                    {% for metric, analysis in hardware_analysis.items() %}
                    <div class="metric">
                        <h3>{{ metric }}</h3>
                        <p class="status-{{ analysis.status }}">
                            Status: {{ analysis.status }}
                        </p>
                        <p>{{ analysis.recommendation }}</p>
                    </div>
                    {% endfor %}
                </div>
                
                <div class="section">
                    <h2>Performance Analysis</h2>
                    {% for metric, analysis in performance_analysis.items() %}
                    <div class="metric">
                        <h3>{{ metric }}</h3>
                        {% if analysis.outliers %}
                        <p>Outliers detected: {{ analysis.outliers.count }}</p>
                        {% endif %}
                        {% if analysis.recommendation %}
                        <p>{{ analysis.recommendation }}</p>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
                
                <div class="section">
                    <h2>Graphs</h2>
                    {% for name, path in graphs.items() %}
                    <div class="graph">
                        <h3>{{ name }}</h3>
                        <iframe src="{{ path }}" width="100%" height="600px"
                                frameborder="0"></iframe>
                    </div>
                    {% endfor %}
                </div>
            </body>
            </html>
            """)
            
            # レポートの生成
            html = template.render(
                timestamp=timestamp,
                metrics=metrics,
                performance_analysis=performance_analysis,
                hardware_analysis=hardware_analysis,
                graphs=graphs
            )
            
            # ファイルに保存
            report_path = self.output_dir / f"report_{timestamp}.html"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(html)
                
            return str(report_path)
            
        except Exception as e:
            self.logger.error(f"HTMLレポート生成エラー: {e}")
            raise
            
    def _generate_json_report(self, timestamp: str,
                           metrics: Dict[str, Any],
                           performance_analysis: Dict[str, Any],
                           hardware_analysis: Dict[str, Any]) -> str:
        """JSONレポートの生成"""
        try:
            report = {
                "timestamp": timestamp,
                "metrics": metrics,
                "performance_analysis": performance_analysis,
                "hardware_analysis": hardware_analysis
            }
            
            # ファイルに保存
            report_path = self.output_dir / f"report_{timestamp}.json"
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2, default=str)
                
            return str(report_path)
            
        except Exception as e:
            self.logger.error(f"JSONレポート生成エラー: {e}")
            raise 
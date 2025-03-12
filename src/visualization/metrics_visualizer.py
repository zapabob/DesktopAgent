<<<<<<< HEAD
import json
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
import seaborn as sns
from datetime import datetime
import logging

class MetricsVisualizer:
    """メトリクス可視化クラス"""
    def __init__(self, metrics_dir: str, output_dir: str):
        self.metrics_dir = Path(metrics_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
    def load_metrics(self) -> List[Dict[str, Any]]:
        """メトリクスファイルの読み込み"""
        metrics_data = []
        for file in self.metrics_dir.glob("metrics_*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["file_timestamp"] = datetime.strptime(
                        file.stem.split("_")[1], "%Y%m%d_%H%M%S"
                    )
                    metrics_data.append(data)
            except Exception as e:
                self.logger.error(f"メトリクス読み込みエラー {file}: {e}")
                
        return sorted(metrics_data, key=lambda x: x["file_timestamp"])
        
    def create_provider_performance_plot(self, metrics: List[Dict[str, Any]]) -> None:
        """プロバイダーごとのパフォーマンスプロット作成"""
        plt.figure(figsize=(12, 6))
        
        timestamps = [m["file_timestamp"] for m in metrics]
        for provider in {"google", "openai", "anthropic"}:
            latencies = []
            for m in metrics:
                if provider in m["providers"]:
                    latencies.append(m["providers"][provider]["avg_latency"])
                else:
                    latencies.append(None)
                    
            plt.plot(timestamps, latencies, label=f"{provider} Avg Latency",
                    marker="o")
            
        plt.title("Provider Average Latency Over Time")
        plt.xlabel("Timestamp")
        plt.ylabel("Average Latency (seconds)")
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        
        output_file = self.output_dir / "provider_latency.png"
        plt.savefig(output_file, bbox_inches="tight")
        plt.close()
        
    def create_system_metrics_plot(self, metrics: List[Dict[str, Any]]) -> None:
        """システムメトリクスのプロット作成"""
        plt.figure(figsize=(12, 6))
        
        timestamps = [m["file_timestamp"] for m in metrics]
        metrics_to_plot = ["cpu_percent", "memory_percent", "disk_percent"]
        
        for metric in metrics_to_plot:
            values = [m["system"][metric] for m in metrics]
            plt.plot(timestamps, values, label=metric, marker="o")
            
        plt.title("System Resource Usage Over Time")
        plt.xlabel("Timestamp")
        plt.ylabel("Percentage")
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        
        output_file = self.output_dir / "system_metrics.png"
        plt.savefig(output_file, bbox_inches="tight")
        plt.close()
        
    def create_request_distribution_plot(self, metrics: List[Dict[str, Any]]) -> None:
        """リクエスト分布のプロット作成"""
        provider_requests = {
            "google": [],
            "openai": [],
            "anthropic": []
        }
        
        for m in metrics:
            for provider in provider_requests:
                if provider in m["providers"]:
                    provider_requests[provider].append(
                        m["providers"][provider]["requests_per_second"]
                    )
                else:
                    provider_requests[provider].append(0)
                    
        plt.figure(figsize=(10, 6))
        sns.boxplot(data=pd.DataFrame(provider_requests))
        plt.title("Request Rate Distribution by Provider")
        plt.ylabel("Requests per Second")
        
        output_file = self.output_dir / "request_distribution.png"
        plt.savefig(output_file, bbox_inches="tight")
        plt.close()
        
    def create_error_rate_plot(self, metrics: List[Dict[str, Any]]) -> None:
        """エラー率のプロット作成"""
        plt.figure(figsize=(12, 6))
        
        timestamps = [m["file_timestamp"] for m in metrics]
        for provider in {"google", "openai", "anthropic"}:
            error_rates = []
            for m in metrics:
                if provider in m["providers"]:
                    error_rates.append(m["providers"][provider]["error_rate"] * 100)
                else:
                    error_rates.append(None)
                    
            plt.plot(timestamps, error_rates,
                    label=f"{provider} Error Rate", marker="o")
            
        plt.title("Provider Error Rates Over Time")
        plt.xlabel("Timestamp")
        plt.ylabel("Error Rate (%)")
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        
        output_file = self.output_dir / "error_rates.png"
        plt.savefig(output_file, bbox_inches="tight")
        plt.close()
        
    def generate_report(self) -> None:
        """メトリクスレポートの生成"""
        try:
            metrics = self.load_metrics()
            if not metrics:
                self.logger.warning("メトリクスデータが見つかりません")
                return
                
            self.create_provider_performance_plot(metrics)
            self.create_system_metrics_plot(metrics)
            self.create_request_distribution_plot(metrics)
            self.create_error_rate_plot(metrics)
            
            # HTMLレポートの生成
            report_path = self.output_dir / "metrics_report.html"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>AI System Metrics Report</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; }
                        .plot { margin: 20px 0; text-align: center; }
                        img { max-width: 100%; }
                    </style>
                </head>
                <body>
                    <h1>AI System Metrics Report</h1>
                    <div class="plot">
                        <h2>Provider Performance</h2>
                        <img src="provider_latency.png" alt="Provider Latency">
                    </div>
                    <div class="plot">
                        <h2>System Resource Usage</h2>
                        <img src="system_metrics.png" alt="System Metrics">
                    </div>
                    <div class="plot">
                        <h2>Request Distribution</h2>
                        <img src="request_distribution.png" alt="Request Distribution">
                    </div>
                    <div class="plot">
                        <h2>Error Rates</h2>
                        <img src="error_rates.png" alt="Error Rates">
                    </div>
                </body>
                </html>
                """)
                
            self.logger.info(f"レポートを生成しました: {report_path}")
            
        except Exception as e:
            self.logger.error(f"レポート生成エラー: {e}")
=======
import json
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
import seaborn as sns
from datetime import datetime
import logging

class MetricsVisualizer:
    """メトリクス可視化クラス"""
    def __init__(self, metrics_dir: str, output_dir: str):
        self.metrics_dir = Path(metrics_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
    def load_metrics(self) -> List[Dict[str, Any]]:
        """メトリクスファイルの読み込み"""
        metrics_data = []
        for file in self.metrics_dir.glob("metrics_*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["file_timestamp"] = datetime.strptime(
                        file.stem.split("_")[1], "%Y%m%d_%H%M%S"
                    )
                    metrics_data.append(data)
            except Exception as e:
                self.logger.error(f"メトリクス読み込みエラー {file}: {e}")
                
        return sorted(metrics_data, key=lambda x: x["file_timestamp"])
        
    def create_provider_performance_plot(self, metrics: List[Dict[str, Any]]) -> None:
        """プロバイダーごとのパフォーマンスプロット作成"""
        plt.figure(figsize=(12, 6))
        
        timestamps = [m["file_timestamp"] for m in metrics]
        for provider in {"google", "openai", "anthropic"}:
            latencies = []
            for m in metrics:
                if provider in m["providers"]:
                    latencies.append(m["providers"][provider]["avg_latency"])
                else:
                    latencies.append(None)
                    
            plt.plot(timestamps, latencies, label=f"{provider} Avg Latency",
                    marker="o")
            
        plt.title("Provider Average Latency Over Time")
        plt.xlabel("Timestamp")
        plt.ylabel("Average Latency (seconds)")
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        
        output_file = self.output_dir / "provider_latency.png"
        plt.savefig(output_file, bbox_inches="tight")
        plt.close()
        
    def create_system_metrics_plot(self, metrics: List[Dict[str, Any]]) -> None:
        """システムメトリクスのプロット作成"""
        plt.figure(figsize=(12, 6))
        
        timestamps = [m["file_timestamp"] for m in metrics]
        metrics_to_plot = ["cpu_percent", "memory_percent", "disk_percent"]
        
        for metric in metrics_to_plot:
            values = [m["system"][metric] for m in metrics]
            plt.plot(timestamps, values, label=metric, marker="o")
            
        plt.title("System Resource Usage Over Time")
        plt.xlabel("Timestamp")
        plt.ylabel("Percentage")
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        
        output_file = self.output_dir / "system_metrics.png"
        plt.savefig(output_file, bbox_inches="tight")
        plt.close()
        
    def create_request_distribution_plot(self, metrics: List[Dict[str, Any]]) -> None:
        """リクエスト分布のプロット作成"""
        provider_requests = {
            "google": [],
            "openai": [],
            "anthropic": []
        }
        
        for m in metrics:
            for provider in provider_requests:
                if provider in m["providers"]:
                    provider_requests[provider].append(
                        m["providers"][provider]["requests_per_second"]
                    )
                else:
                    provider_requests[provider].append(0)
                    
        plt.figure(figsize=(10, 6))
        sns.boxplot(data=pd.DataFrame(provider_requests))
        plt.title("Request Rate Distribution by Provider")
        plt.ylabel("Requests per Second")
        
        output_file = self.output_dir / "request_distribution.png"
        plt.savefig(output_file, bbox_inches="tight")
        plt.close()
        
    def create_error_rate_plot(self, metrics: List[Dict[str, Any]]) -> None:
        """エラー率のプロット作成"""
        plt.figure(figsize=(12, 6))
        
        timestamps = [m["file_timestamp"] for m in metrics]
        for provider in {"google", "openai", "anthropic"}:
            error_rates = []
            for m in metrics:
                if provider in m["providers"]:
                    error_rates.append(m["providers"][provider]["error_rate"] * 100)
                else:
                    error_rates.append(None)
                    
            plt.plot(timestamps, error_rates,
                    label=f"{provider} Error Rate", marker="o")
            
        plt.title("Provider Error Rates Over Time")
        plt.xlabel("Timestamp")
        plt.ylabel("Error Rate (%)")
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        
        output_file = self.output_dir / "error_rates.png"
        plt.savefig(output_file, bbox_inches="tight")
        plt.close()
        
    def generate_report(self) -> None:
        """メトリクスレポートの生成"""
        try:
            metrics = self.load_metrics()
            if not metrics:
                self.logger.warning("メトリクスデータが見つかりません")
                return
                
            self.create_provider_performance_plot(metrics)
            self.create_system_metrics_plot(metrics)
            self.create_request_distribution_plot(metrics)
            self.create_error_rate_plot(metrics)
            
            # HTMLレポートの生成
            report_path = self.output_dir / "metrics_report.html"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>AI System Metrics Report</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; }
                        .plot { margin: 20px 0; text-align: center; }
                        img { max-width: 100%; }
                    </style>
                </head>
                <body>
                    <h1>AI System Metrics Report</h1>
                    <div class="plot">
                        <h2>Provider Performance</h2>
                        <img src="provider_latency.png" alt="Provider Latency">
                    </div>
                    <div class="plot">
                        <h2>System Resource Usage</h2>
                        <img src="system_metrics.png" alt="System Metrics">
                    </div>
                    <div class="plot">
                        <h2>Request Distribution</h2>
                        <img src="request_distribution.png" alt="Request Distribution">
                    </div>
                    <div class="plot">
                        <h2>Error Rates</h2>
                        <img src="error_rates.png" alt="Error Rates">
                    </div>
                </body>
                </html>
                """)
                
            self.logger.info(f"レポートを生成しました: {report_path}")
            
        except Exception as e:
            self.logger.error(f"レポート生成エラー: {e}")
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
            raise 
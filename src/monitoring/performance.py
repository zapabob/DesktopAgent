<<<<<<< HEAD
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import logging
import psutil
import json
from pathlib import Path

class PerformanceMetrics:
    """パフォーマンスメトリクス"""
    def __init__(self):
        self.start_time: float = time.time()
        self.request_count: int = 0
        self.error_count: int = 0
        self.total_latency: float = 0.0
        self.max_latency: float = 0.0
        self.min_latency: float = float('inf')
        
class PerformanceMonitor:
    """パフォーマンスモニタリングクラス"""
    def __init__(self, metrics_dir: Optional[str] = None):
        self.metrics_dir = Path(metrics_dir) if metrics_dir else Path("metrics")
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.logger = logging.getLogger(__name__)
        self._lock = asyncio.Lock()
        
    def _get_metrics(self, provider: str) -> PerformanceMetrics:
        """プロバイダーごとのメトリクスを取得"""
        if provider not in self.metrics:
            self.metrics[provider] = PerformanceMetrics()
        return self.metrics[provider]
        
    async def record_request(self, provider: str, latency: float,
                           success: bool = True) -> None:
        """リクエストの記録"""
        async with self._lock:
            metrics = self._get_metrics(provider)
            metrics.request_count += 1
            if not success:
                metrics.error_count += 1
            metrics.total_latency += latency
            metrics.max_latency = max(metrics.max_latency, latency)
            metrics.min_latency = min(metrics.min_latency, latency)
            
    def get_provider_stats(self, provider: str) -> Dict[str, Any]:
        """プロバイダーの統計情報を取得"""
        metrics = self._get_metrics(provider)
        uptime = time.time() - metrics.start_time
        requests = metrics.request_count
        
        return {
            "uptime_seconds": uptime,
            "total_requests": requests,
            "error_rate": metrics.error_count / requests if requests > 0 else 0,
            "avg_latency": metrics.total_latency / requests if requests > 0 else 0,
            "max_latency": metrics.max_latency,
            "min_latency": metrics.min_latency if metrics.min_latency != float('inf') else 0,
            "requests_per_second": requests / uptime if uptime > 0 else 0
        }
        
    async def get_system_metrics(self) -> Dict[str, float]:
        """システムメトリクスの取得"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "memory_available_gb": memory.available / (1024 ** 3),
            "disk_free_gb": disk.free / (1024 ** 3)
        }
        
    async def save_metrics(self) -> None:
        """メトリクスの保存"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            metrics_file = self.metrics_dir / f"metrics_{timestamp}.json"
            
            metrics_data = {
                "timestamp": timestamp,
                "providers": {
                    provider: self.get_provider_stats(provider)
                    for provider in self.metrics
                },
                "system": await self.get_system_metrics()
            }
            
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(metrics_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"メトリクス保存エラー: {e}")
            
    async def start_monitoring(self, interval: int = 300) -> None:
        """モニタリングの開始"""
        while True:
            try:
                await self.save_metrics()
                await asyncio.sleep(interval)
            except Exception as e:
                self.logger.error(f"モニタリングエラー: {e}")
=======
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import logging
import psutil
import json
from pathlib import Path

class PerformanceMetrics:
    """パフォーマンスメトリクス"""
    def __init__(self):
        self.start_time: float = time.time()
        self.request_count: int = 0
        self.error_count: int = 0
        self.total_latency: float = 0.0
        self.max_latency: float = 0.0
        self.min_latency: float = float('inf')
        
class PerformanceMonitor:
    """パフォーマンスモニタリングクラス"""
    def __init__(self, metrics_dir: Optional[str] = None):
        self.metrics_dir = Path(metrics_dir) if metrics_dir else Path("metrics")
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.logger = logging.getLogger(__name__)
        self._lock = asyncio.Lock()
        
    def _get_metrics(self, provider: str) -> PerformanceMetrics:
        """プロバイダーごとのメトリクスを取得"""
        if provider not in self.metrics:
            self.metrics[provider] = PerformanceMetrics()
        return self.metrics[provider]
        
    async def record_request(self, provider: str, latency: float,
                           success: bool = True) -> None:
        """リクエストの記録"""
        async with self._lock:
            metrics = self._get_metrics(provider)
            metrics.request_count += 1
            if not success:
                metrics.error_count += 1
            metrics.total_latency += latency
            metrics.max_latency = max(metrics.max_latency, latency)
            metrics.min_latency = min(metrics.min_latency, latency)
            
    def get_provider_stats(self, provider: str) -> Dict[str, Any]:
        """プロバイダーの統計情報を取得"""
        metrics = self._get_metrics(provider)
        uptime = time.time() - metrics.start_time
        requests = metrics.request_count
        
        return {
            "uptime_seconds": uptime,
            "total_requests": requests,
            "error_rate": metrics.error_count / requests if requests > 0 else 0,
            "avg_latency": metrics.total_latency / requests if requests > 0 else 0,
            "max_latency": metrics.max_latency,
            "min_latency": metrics.min_latency if metrics.min_latency != float('inf') else 0,
            "requests_per_second": requests / uptime if uptime > 0 else 0
        }
        
    async def get_system_metrics(self) -> Dict[str, float]:
        """システムメトリクスの取得"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "memory_available_gb": memory.available / (1024 ** 3),
            "disk_free_gb": disk.free / (1024 ** 3)
        }
        
    async def save_metrics(self) -> None:
        """メトリクスの保存"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            metrics_file = self.metrics_dir / f"metrics_{timestamp}.json"
            
            metrics_data = {
                "timestamp": timestamp,
                "providers": {
                    provider: self.get_provider_stats(provider)
                    for provider in self.metrics
                },
                "system": await self.get_system_metrics()
            }
            
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(metrics_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"メトリクス保存エラー: {e}")
            
    async def start_monitoring(self, interval: int = 300) -> None:
        """モニタリングの開始"""
        while True:
            try:
                await self.save_metrics()
                await asyncio.sleep(interval)
            except Exception as e:
                self.logger.error(f"モニタリングエラー: {e}")
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
                await asyncio.sleep(10)  # エラー時は短い間隔で再試行 
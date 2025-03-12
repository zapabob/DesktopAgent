import psutil
import GPUtil
from typing import Dict, Any, List
import logging
from datetime import datetime
import asyncio
from pathlib import Path

class MetricsCollector:
    """メトリクス収集クラス"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def collect_all_metrics(self) -> Dict[str, Any]:
        """全メトリクスの収集"""
        try:
            return {
                "hardware": await self.collect_hardware_metrics(),
                "performance": await self.collect_performance_metrics(),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"メトリクス収集エラー: {e}")
            return {}
            
    async def collect_hardware_metrics(self) -> Dict[str, Any]:
        """ハードウェアメトリクスの収集"""
        try:
            # CPU情報
            cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
            cpu_freq = psutil.cpu_freq()
            
            # メモリ情報
            memory = psutil.virtual_memory()
            
            # GPU情報
            gpu_info = []
            try:
                gpus = GPUtil.getGPUs()
                for gpu in gpus:
                    gpu_info.append({
                        "id": gpu.id,
                        "name": gpu.name,
                        "load": gpu.load * 100,
                        "memory_used": gpu.memoryUsed,
                        "memory_total": gpu.memoryTotal,
                        "temperature": gpu.temperature
                    })
            except Exception as e:
                self.logger.warning(f"GPU情報取得エラー: {e}")
                
            # ディスク情報
            disk = psutil.disk_usage('/')
            
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "frequency": {
                        "current": cpu_freq.current,
                        "min": cpu_freq.min,
                        "max": cpu_freq.max
                    }
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free
                },
                "gpu": gpu_info,
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                }
            }
            
        except Exception as e:
            self.logger.error(f"ハードウェアメトリクス収集エラー: {e}")
            return {}
            
    async def collect_performance_metrics(self) -> Dict[str, Any]:
        """パフォーマンスメトリクスの収集"""
        try:
            # プロセス情報
            process = psutil.Process()
            
            # ネットワーク情報
            network = psutil.net_io_counters()
            
            return {
                "process": {
                    "cpu_percent": process.cpu_percent(),
                    "memory_percent": process.memory_percent(),
                    "threads": process.num_threads(),
                    "handles": process.num_handles() if hasattr(process, 'num_handles') else None
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv,
                    "errin": network.errin,
                    "errout": network.errout,
                    "dropin": network.dropin,
                    "dropout": network.dropout
                }
            }
            
        except Exception as e:
            self.logger.error(f"パフォーマンスメトリクス収集エラー: {e}")
            return {} 
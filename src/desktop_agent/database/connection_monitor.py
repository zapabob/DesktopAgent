<<<<<<< HEAD
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import deque

class ConnectionMonitor:
    """接続プールモニタリングクラス"""
    def __init__(self, pool, history_size: int = 1000):
        self.pool = pool
        self.history_size = history_size
        self.metrics_history = deque(maxlen=history_size)
        self.logger = logging.getLogger(__name__)
        self._lock = asyncio.Lock()
        self._monitoring = False
        
    async def start_monitoring(self, interval: float = 1.0):
        """モニタリングの開始"""
        if self._monitoring:
            return
            
        self._monitoring = True
        while self._monitoring:
            try:
                metrics = await self._collect_metrics()
                async with self._lock:
                    self.metrics_history.append(metrics)
                await asyncio.sleep(interval)
            except Exception as e:
                self.logger.error(f"モニタリングエラー: {e}")
                await asyncio.sleep(1)
                
    def stop_monitoring(self):
        """モニタリングの停止"""
        self._monitoring = False
        
    async def _collect_metrics(self) -> Dict[str, Any]:
        """メトリクスの収集"""
        try:
            stats = self.pool.get_stats()
            return {
                "timestamp": datetime.now().isoformat(),
                "total_connections": stats["total_connections"],
                "active_connections": stats["active_connections"],
                "idle_connections": stats["idle_connections"],
                "connection_usage_percent": (
                    stats["active_connections"] / stats["total_connections"] * 100
                    if stats["total_connections"] > 0 else 0
                )
            }
        except Exception as e:
            self.logger.error(f"メトリクス収集エラー: {e}")
            return {}
            
    async def get_metrics(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """過去N分間のメトリクスを取得"""
        try:
            threshold = datetime.now() - timedelta(minutes=minutes)
            async with self._lock:
                return [
                    m for m in self.metrics_history
                    if datetime.fromisoformat(m["timestamp"]) >= threshold
                ]
        except Exception as e:
            self.logger.error(f"メトリクス取得エラー: {e}")
            return []
            
    async def analyze_usage_patterns(self) -> Dict[str, Any]:
        """使用パターンの分析"""
        try:
            metrics = await self.get_metrics(minutes=60)
            if not metrics:
                return {}
                
            usage_percentages = [m["connection_usage_percent"] for m in metrics]
            return {
                "avg_usage_percent": sum(usage_percentages) / len(usage_percentages),
                "max_usage_percent": max(usage_percentages),
                "min_usage_percent": min(usage_percentages),
                "peak_times": self._find_peak_times(metrics),
                "recommendations": self._generate_recommendations(metrics)
            }
        except Exception as e:
            self.logger.error(f"使用パターン分析エラー: {e}")
            return {}
            
    def _find_peak_times(self, metrics: List[Dict[str, Any]]) -> List[str]:
        """ピーク時間の特定"""
        try:
            peak_threshold = 80  # 80%以上を高負荷とみなす
            peak_times = []
            
            for m in metrics:
                if m["connection_usage_percent"] >= peak_threshold:
                    hour = datetime.fromisoformat(
                        m["timestamp"]
                    ).strftime("%H:00")
                    if hour not in peak_times:
                        peak_times.append(hour)
                        
            return sorted(peak_times)
            
        except Exception as e:
            self.logger.error(f"ピーク時間分析エラー: {e}")
            return []
            
    def _generate_recommendations(self, metrics: List[Dict[str, Any]]) -> List[str]:
        """推奨事項の生成"""
        try:
            recommendations = []
            avg_usage = sum(
                m["connection_usage_percent"] for m in metrics
            ) / len(metrics)
            
            if avg_usage > 80:
                recommendations.append(
                    "接続プールの最大サイズを増やすことを検討してください"
                )
            elif avg_usage < 20:
                recommendations.append(
                    "接続プールの最大サイズを減らすことで、リソースを節約できます"
                )
                
            if any(m["connection_usage_percent"] == 100 for m in metrics):
                recommendations.append(
                    "接続プールが飽和状態に達しています。スケーリングを検討してください"
                )
                
            return recommendations
            
        except Exception as e:
            self.logger.error(f"推奨事項生成エラー: {e}")
            return []
            
    async def export_metrics(self, file_path: str):
        """メトリクスのエクスポート"""
        try:
            import json
            metrics = await self.get_metrics(minutes=60)
            with open(file_path, "w") as f:
                json.dump({
                    "metrics": metrics,
                    "analysis": await self.analyze_usage_patterns()
                }, f, indent=2)
            self.logger.info(f"メトリクスをエクスポートしました: {file_path}")
        except Exception as e:
            self.logger.error(f"メトリクスエクスポートエラー: {e}")
=======
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import deque

class ConnectionMonitor:
    """接続プールモニタリングクラス"""
    def __init__(self, pool, history_size: int = 1000):
        self.pool = pool
        self.history_size = history_size
        self.metrics_history = deque(maxlen=history_size)
        self.logger = logging.getLogger(__name__)
        self._lock = asyncio.Lock()
        self._monitoring = False
        
    async def start_monitoring(self, interval: float = 1.0):
        """モニタリングの開始"""
        if self._monitoring:
            return
            
        self._monitoring = True
        while self._monitoring:
            try:
                metrics = await self._collect_metrics()
                async with self._lock:
                    self.metrics_history.append(metrics)
                await asyncio.sleep(interval)
            except Exception as e:
                self.logger.error(f"モニタリングエラー: {e}")
                await asyncio.sleep(1)
                
    def stop_monitoring(self):
        """モニタリングの停止"""
        self._monitoring = False
        
    async def _collect_metrics(self) -> Dict[str, Any]:
        """メトリクスの収集"""
        try:
            stats = self.pool.get_stats()
            return {
                "timestamp": datetime.now().isoformat(),
                "total_connections": stats["total_connections"],
                "active_connections": stats["active_connections"],
                "idle_connections": stats["idle_connections"],
                "connection_usage_percent": (
                    stats["active_connections"] / stats["total_connections"] * 100
                    if stats["total_connections"] > 0 else 0
                )
            }
        except Exception as e:
            self.logger.error(f"メトリクス収集エラー: {e}")
            return {}
            
    async def get_metrics(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """過去N分間のメトリクスを取得"""
        try:
            threshold = datetime.now() - timedelta(minutes=minutes)
            async with self._lock:
                return [
                    m for m in self.metrics_history
                    if datetime.fromisoformat(m["timestamp"]) >= threshold
                ]
        except Exception as e:
            self.logger.error(f"メトリクス取得エラー: {e}")
            return []
            
    async def analyze_usage_patterns(self) -> Dict[str, Any]:
        """使用パターンの分析"""
        try:
            metrics = await self.get_metrics(minutes=60)
            if not metrics:
                return {}
                
            usage_percentages = [m["connection_usage_percent"] for m in metrics]
            return {
                "avg_usage_percent": sum(usage_percentages) / len(usage_percentages),
                "max_usage_percent": max(usage_percentages),
                "min_usage_percent": min(usage_percentages),
                "peak_times": self._find_peak_times(metrics),
                "recommendations": self._generate_recommendations(metrics)
            }
        except Exception as e:
            self.logger.error(f"使用パターン分析エラー: {e}")
            return {}
            
    def _find_peak_times(self, metrics: List[Dict[str, Any]]) -> List[str]:
        """ピーク時間の特定"""
        try:
            peak_threshold = 80  # 80%以上を高負荷とみなす
            peak_times = []
            
            for m in metrics:
                if m["connection_usage_percent"] >= peak_threshold:
                    hour = datetime.fromisoformat(
                        m["timestamp"]
                    ).strftime("%H:00")
                    if hour not in peak_times:
                        peak_times.append(hour)
                        
            return sorted(peak_times)
            
        except Exception as e:
            self.logger.error(f"ピーク時間分析エラー: {e}")
            return []
            
    def _generate_recommendations(self, metrics: List[Dict[str, Any]]) -> List[str]:
        """推奨事項の生成"""
        try:
            recommendations = []
            avg_usage = sum(
                m["connection_usage_percent"] for m in metrics
            ) / len(metrics)
            
            if avg_usage > 80:
                recommendations.append(
                    "接続プールの最大サイズを増やすことを検討してください"
                )
            elif avg_usage < 20:
                recommendations.append(
                    "接続プールの最大サイズを減らすことで、リソースを節約できます"
                )
                
            if any(m["connection_usage_percent"] == 100 for m in metrics):
                recommendations.append(
                    "接続プールが飽和状態に達しています。スケーリングを検討してください"
                )
                
            return recommendations
            
        except Exception as e:
            self.logger.error(f"推奨事項生成エラー: {e}")
            return []
            
    async def export_metrics(self, file_path: str):
        """メトリクスのエクスポート"""
        try:
            import json
            metrics = await self.get_metrics(minutes=60)
            with open(file_path, "w") as f:
                json.dump({
                    "metrics": metrics,
                    "analysis": await self.analyze_usage_patterns()
                }, f, indent=2)
            self.logger.info(f"メトリクスをエクスポートしました: {file_path}")
        except Exception as e:
            self.logger.error(f"メトリクスエクスポートエラー: {e}")
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
            raise 
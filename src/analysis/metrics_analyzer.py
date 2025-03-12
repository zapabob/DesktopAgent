import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from scipy import stats

class MetricsAnalyzer:
    """メトリクス分析クラス"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def analyze_performance(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """パフォーマンスメトリクスの分析"""
        try:
            results = {}
            
            # レイテンシー分析
            for metric in ["query_latencies", "insert_latencies", "update_latencies"]:
                if metric in metrics and metrics[metric]:
                    results[metric] = self._analyze_latency(metrics[metric])
                    
            # エラー率分析
            if "error_rate" in metrics:
                results["error_analysis"] = self._analyze_error_rate(metrics["error_rate"])
                
            # キャッシュヒット率分析
            if "cache_hit_rate" in metrics:
                results["cache_analysis"] = self._analyze_cache_hit_rate(
                    metrics["cache_hit_rate"]
                )
                
            return results
            
        except Exception as e:
            self.logger.error(f"パフォーマンス分析エラー: {e}")
            raise
            
    def analyze_hardware(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """ハードウェアメトリクスの分析"""
        try:
            results = {}
            
            # CPU/GPU温度分析
            for metric in ["cpu_temperature", "gpu_temperature"]:
                if metric in metrics:
                    results[metric] = self._analyze_temperature(
                        metrics[metric],
                        warning_threshold=80.0,
                        critical_threshold=90.0
                    )
                    
            # メモリ使用率分析
            if "memory_usage" in metrics:
                results["memory_analysis"] = self._analyze_memory_usage(
                    metrics["memory_usage"]
                )
                
            # リソース相関分析
            if all(k in metrics for k in ["cpu_usage", "memory_usage"]):
                results["resource_correlation"] = self._analyze_correlation(
                    metrics["cpu_usage"],
                    metrics["memory_usage"]
                )
                
            return results
            
        except Exception as e:
            self.logger.error(f"ハードウェア分析エラー: {e}")
            raise
            
    def _analyze_latency(self, latencies: List[float]) -> Dict[str, Any]:
        """レイテンシーの統計分析"""
        if not latencies:
            return {}
            
        data = np.array(latencies)
        percentiles = np.percentile(data, [50, 90, 95, 99])
        
        return {
            "mean": float(np.mean(data)),
            "std": float(np.std(data)),
            "min": float(np.min(data)),
            "max": float(np.max(data)),
            "p50": float(percentiles[0]),
            "p90": float(percentiles[1]),
            "p95": float(percentiles[2]),
            "p99": float(percentiles[3]),
            "outliers": self._detect_outliers(data)
        }
        
    def _analyze_error_rate(self, error_rate: float) -> Dict[str, Any]:
        """エラー率の分析"""
        return {
            "current_rate": error_rate,
            "status": "critical" if error_rate > 0.1 else
                     "warning" if error_rate > 0.05 else "normal",
            "recommendation": self._get_error_recommendation(error_rate)
        }
        
    def _analyze_cache_hit_rate(self, hit_rate: float) -> Dict[str, Any]:
        """キャッシュヒット率の分析"""
        return {
            "current_rate": hit_rate,
            "efficiency": "high" if hit_rate > 0.8 else
                         "medium" if hit_rate > 0.5 else "low",
            "recommendation": self._get_cache_recommendation(hit_rate)
        }
        
    def _analyze_temperature(self, temp: float,
                          warning_threshold: float,
                          critical_threshold: float) -> Dict[str, Any]:
        """温度の分析"""
        return {
            "current_temp": temp,
            "status": "critical" if temp >= critical_threshold else
                     "warning" if temp >= warning_threshold else "normal",
            "recommendation": self._get_temperature_recommendation(
                temp, warning_threshold, critical_threshold
            )
        }
        
    def _analyze_memory_usage(self, usage: float) -> Dict[str, Any]:
        """メモリ使用率の分析"""
        return {
            "current_usage": usage,
            "status": "critical" if usage > 90 else
                     "warning" if usage > 80 else "normal",
            "recommendation": self._get_memory_recommendation(usage)
        }
        
    def _analyze_correlation(self, x: List[float], y: List[float]) -> Dict[str, Any]:
        """相関分析"""
        if len(x) != len(y):
            return {}
            
        correlation, p_value = stats.pearsonr(x, y)
        return {
            "correlation": float(correlation),
            "p_value": float(p_value),
            "significance": "high" if p_value < 0.01 else
                          "medium" if p_value < 0.05 else "low"
        }
        
    def _detect_outliers(self, data: np.ndarray) -> Dict[str, Any]:
        """外れ値の検出"""
        q1, q3 = np.percentile(data, [25, 75])
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = data[(data < lower_bound) | (data > upper_bound)]
        
        return {
            "count": len(outliers),
            "values": outliers.tolist() if len(outliers) < 10 else outliers[:10].tolist(),
            "bounds": {
                "lower": float(lower_bound),
                "upper": float(upper_bound)
            }
        }
        
    def _get_error_recommendation(self, error_rate: float) -> str:
        """エラー率に基づく推奨事項"""
        if error_rate > 0.1:
            return "システムの安定性を確認し、エラーログを詳細に分析してください"
        elif error_rate > 0.05:
            return "エラーの傾向を監視し、必要に応じて対策を検討してください"
        return "正常な範囲内です"
        
    def _get_cache_recommendation(self, hit_rate: float) -> str:
        """キャッシュヒット率に基づく推奨事項"""
        if hit_rate < 0.5:
            return "キャッシュ戦略の見直しを検討してください"
        elif hit_rate < 0.8:
            return "キャッシュの最適化の余地があります"
        return "効率的なキャッシュ利用が行われています"
        
    def _get_temperature_recommendation(self, temp: float,
                                    warning_threshold: float,
                                    critical_threshold: float) -> str:
        """温度に基づく推奨事項"""
        if temp >= critical_threshold:
            return "直ちに負荷を下げる必要があります"
        elif temp >= warning_threshold:
            return "冷却システムの状態を確認してください"
        return "正常な温度範囲内です"
        
    def _get_memory_recommendation(self, usage: float) -> str:
        """メモリ使用率に基づく推奨事項"""
        if usage > 90:
            return "メモリリークの可能性を確認し、不要なリソースを解放してください"
        elif usage > 80:
            return "メモリ使用量の監視を強化してください"
        return "適切なメモリ使用率を維持しています" 
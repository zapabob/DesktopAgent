import psutil
import GPUtil
import logging
from typing import Dict, Any, List, Optional
import time
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import os

# 例外クラスの定義
class HardwareMonitorError(Exception):
    """ハードウェアモニタリングに関するエラー"""
    pass

@dataclass
class HardwareMetrics:
    """ハードウェアメトリクス"""
    cpu_temp: float = 0.0
    gpu_temp: float = 0.0
    cpu_usage: float = 0.0
    gpu_usage: float = 0.0
    memory_usage: float = 0.0
    gpu_memory_usage: float = 0.0
    timestamp: datetime = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """メトリクスを辞書形式に変換"""
        return {
            "cpu_temp": self.cpu_temp,
            "gpu_temp": self.gpu_temp,
            "cpu_usage": self.cpu_usage,
            "gpu_usage": self.gpu_usage,
            "memory_usage": self.memory_usage,
            "gpu_memory_usage": self.gpu_memory_usage,
            "timestamp": self.timestamp.isoformat()
        }

class HardwareMonitor:
    """ハードウェアモニタリングクラス"""
    def __init__(self, max_history_size: int = 100):
        self.logger = logging.getLogger(__name__)
        self.metrics_history: List[HardwareMetrics] = []
        self.warning_temp_threshold = 80.0  # 警告温度閾値
        self.critical_temp_threshold = 90.0  # 危険温度閾値
        self.max_history_size = max_history_size
        self.export_directory = Path("monitoring_data")
        
        # エクスポートディレクトリがなければ作成
        if not self.export_directory.exists():
            os.makedirs(self.export_directory, exist_ok=True)
        
    def get_cpu_temperature(self) -> float:
        """CPU温度の取得"""
        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                self.logger.warning("CPU温度センサーが見つかりません")
                return 0.0
            
            # 最も高い温度を返す
            max_temp = 0.0
            for name, entries in temps.items():
                for entry in entries:
                    if entry.current > max_temp:
                        max_temp = entry.current
            return max_temp
            
        except Exception as e:
            self.logger.error(f"CPU温度取得エラー: {e}")
            raise HardwareMonitorError(f"CPU温度の取得に失敗: {e}")
            
    def get_gpu_temperature(self) -> float:
        """GPU温度の取得"""
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                self.logger.warning("利用可能なGPUが見つかりません")
                return 0.0
                
            # 最初のGPUの温度を返す
            return gpus[0].temperature
            
        except Exception as e:
            self.logger.error(f"GPU温度取得エラー: {e}")
            raise HardwareMonitorError(f"GPU温度の取得に失敗: {e}")
            
    def get_gpu_details(self) -> Dict[str, Any]:
        """GPUの詳細情報を取得"""
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                self.logger.warning("利用可能なGPUが見つかりません")
                return {}
            
            gpu = gpus[0]  # 最初のGPUを使用
            
            return {
                "name": gpu.name,
                "driver": gpu.driver,
                "memory_total": gpu.memoryTotal,
                "memory_used": gpu.memoryUsed,
                "memory_free": gpu.memoryFree,
                "temperature": gpu.temperature,
                "load": gpu.load,
                "uuid": gpu.uuid
            }
        except Exception as e:
            self.logger.error(f"GPU詳細情報取得エラー: {e}")
            return {}
            
    def get_metrics(self) -> HardwareMetrics:
        """すべてのハードウェアメトリクスを取得"""
        try:
            # CPU温度
            cpu_temp = self.get_cpu_temperature()
            
            # GPU温度
            gpu_temp = self.get_gpu_temperature()
            
            # CPU使用率
            cpu_usage = self._get_cpu_usage()
            
            # GPU使用率
            gpu_usage, gpu_memory_usage = self._get_gpu_usage()
            
            # メモリ使用率
            memory_usage = self._get_memory_usage()
            
            # 温度警告チェック
            self._check_temperature_warnings(cpu_temp, gpu_temp)
            
            # メトリクスオブジェクト作成
            metrics = HardwareMetrics(
                cpu_temp=cpu_temp,
                gpu_temp=gpu_temp,
                cpu_usage=cpu_usage,
                gpu_usage=gpu_usage,
                memory_usage=memory_usage,
                gpu_memory_usage=gpu_memory_usage,
                timestamp=datetime.now()
            )
            
            # 履歴に追加
            self.metrics_history.append(metrics)
            
            # 履歴サイズの管理
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history.pop(0)
                
            return metrics
            
        except Exception as e:
            self.logger.error(f"メトリクス取得エラー: {e}")
            raise HardwareMonitorError(f"メトリクスの取得に失敗: {e}")
            
    def _get_cpu_usage(self) -> float:
        """CPU使用率の取得"""
        try:
            return psutil.cpu_percent(interval=0.1)
        except Exception as e:
            self.logger.error(f"CPU使用率取得エラー: {e}")
            return 0.0
            
    def _get_gpu_usage(self) -> tuple:
        """GPU使用率とメモリ使用率の取得"""
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                return 0.0, 0.0
                
            gpu = gpus[0]  # 最初のGPUを使用
            return gpu.load * 100, (gpu.memoryUsed / gpu.memoryTotal) * 100
        except Exception as e:
            self.logger.error(f"GPU使用率取得エラー: {e}")
            return 0.0, 0.0
            
    def _get_memory_usage(self) -> float:
        """メモリ使用率の取得"""
        try:
            memory = psutil.virtual_memory()
            return memory.percent
        except Exception as e:
            self.logger.error(f"メモリ使用率取得エラー: {e}")
            return 0.0
            
    def _check_temperature_warnings(self, cpu_temp: float, gpu_temp: float) -> None:
        """温度警告のチェック"""
        # CPU温度チェック
        if cpu_temp >= self.critical_temp_threshold:
            self.logger.critical(f"CPU温度が危険レベルです: {cpu_temp}°C")
        elif cpu_temp >= self.warning_temp_threshold:
            self.logger.warning(f"CPU温度が高温です: {cpu_temp}°C")
            
        # GPU温度チェック
        if gpu_temp >= self.critical_temp_threshold:
            self.logger.critical(f"GPU温度が危険レベルです: {gpu_temp}°C")
        elif gpu_temp >= self.warning_temp_threshold:
            self.logger.warning(f"GPU温度が高温です: {gpu_temp}°C")
            
    def get_temperature_history(self) -> Dict[str, list]:
        """温度履歴を取得"""
        cpu_temps = [m.cpu_temp for m in self.metrics_history]
        gpu_temps = [m.gpu_temp for m in self.metrics_history]
        timestamps = [m.timestamp.strftime("%H:%M:%S") for m in self.metrics_history]
        
        return {
            "timestamps": timestamps,
            "cpu_temps": cpu_temps,
            "gpu_temps": gpu_temps
        }
        
    def get_usage_history(self) -> Dict[str, list]:
        """使用率履歴を取得"""
        cpu_usage = [m.cpu_usage for m in self.metrics_history]
        gpu_usage = [m.gpu_usage for m in self.metrics_history]
        memory_usage = [m.memory_usage for m in self.metrics_history]
        gpu_memory_usage = [m.gpu_memory_usage for m in self.metrics_history]
        timestamps = [m.timestamp.strftime("%H:%M:%S") for m in self.metrics_history]
        
        return {
            "timestamps": timestamps,
            "cpu_usage": cpu_usage,
            "gpu_usage": gpu_usage,
            "memory_usage": memory_usage,
            "gpu_memory_usage": gpu_memory_usage
        }
    
    def export_metrics_to_json(self, filename: Optional[str] = None) -> str:
        """メトリクス履歴をJSONファイルにエクスポート"""
        if not filename:
            filename = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        filepath = self.export_directory / filename
        
        try:
            # メトリクスを辞書リストに変換
            metrics_data = [m.to_dict() for m in self.metrics_history]
            
            # JSON形式で保存
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(metrics_data, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"メトリクスデータをエクスポートしました: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"メトリクスのエクスポートに失敗: {e}")
            raise HardwareMonitorError(f"メトリクスのエクスポートに失敗: {e}")
    
    def clear_history(self) -> None:
        """メトリクス履歴をクリア"""
        self.metrics_history.clear()
        self.logger.info("メトリクス履歴をクリアしました") 
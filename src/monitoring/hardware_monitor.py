<<<<<<< HEAD
import psutil
import GPUtil
import logging
from typing import Dict, Any
import time
from dataclasses import dataclass
from datetime import datetime
from src.exceptions import HardwareMonitorError

@dataclass
class HardwareMetrics:
    """ハードウェアメトリクス"""
    cpu_temp: float = 0.0
    gpu_temp: float = 0.0
    cpu_usage: float = 0.0
    gpu_usage: float = 0.0
    memory_usage: float = 0.0
    timestamp: datetime = datetime.now()

class HardwareMonitor:
    """ハードウェアモニタリングクラス"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics_history = []
        self.warning_temp_threshold = 80.0  # 警告温度閾値
        self.critical_temp_threshold = 90.0  # 危険温度閾値
        
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
                self.logger.warning("GPUが見つかりません")
                return 0.0
            
            # 最も高い温度を返す
            return max(gpu.temperature for gpu in gpus)
            
        except Exception as e:
            self.logger.error(f"GPU温度取得エラー: {e}")
            raise HardwareMonitorError(f"GPU温度の取得に失敗: {e}")
            
    def get_metrics(self) -> HardwareMetrics:
        """ハードウェアメトリクスの取得"""
        try:
            # エラーが発生しても処理を継続
            try:
                cpu_temp = self.get_cpu_temperature()
            except HardwareMonitorError as e:
                self.logger.error(str(e))
                cpu_temp = 0.0
                
            try:
                gpu_temp = self.get_gpu_temperature()
            except HardwareMonitorError as e:
                self.logger.error(str(e))
                gpu_temp = 0.0
            
            # 温度警告のチェック
            self._check_temperature_warnings(cpu_temp, gpu_temp)
            
            metrics = HardwareMetrics(
                cpu_temp=cpu_temp,
                gpu_temp=gpu_temp,
                cpu_usage=self._get_cpu_usage(),
                gpu_usage=self._get_gpu_usage(),
                memory_usage=self._get_memory_usage(),
                timestamp=datetime.now()
            )
            
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > 1000:  # 履歴を1000件に制限
                self.metrics_history.pop(0)
                
            return metrics
            
        except Exception as e:
            self.logger.error(f"メトリクス取得エラー: {e}")
            return HardwareMetrics()
            
    def _get_cpu_usage(self) -> float:
        """CPU使用率の取得"""
        try:
            return psutil.cpu_percent()
        except Exception as e:
            self.logger.error(f"CPU使用率取得エラー: {e}")
            return 0.0
            
    def _get_gpu_usage(self) -> float:
        """GPU使用率の取得"""
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                return 0.0
            return max(gpu.load * 100 for gpu in gpus)
        except Exception as e:
            self.logger.error(f"GPU使用率取得エラー: {e}")
            return 0.0
            
    def _get_memory_usage(self) -> float:
        """メモリ使用率の取得"""
        try:
            return psutil.virtual_memory().percent
        except Exception as e:
            self.logger.error(f"メモリ使用率取得エラー: {e}")
            return 0.0
            
    def _check_temperature_warnings(self, cpu_temp: float, gpu_temp: float) -> None:
        """温度警告のチェック"""
        for device, temp in [("CPU", cpu_temp), ("GPU", gpu_temp)]:
            if temp >= self.critical_temp_threshold:
                self.logger.critical(
                    f"{device}温度が危険値に達しています: {temp}°C"
                )
            elif temp >= self.warning_temp_threshold:
                self.logger.warning(
                    f"{device}温度が警告値を超えています: {temp}°C"
                )
                
    def get_temperature_history(self) -> Dict[str, list]:
        """温度履歴の取得"""
        return {
            "timestamps": [m.timestamp for m in self.metrics_history],
            "cpu_temps": [m.cpu_temp for m in self.metrics_history],
            "gpu_temps": [m.gpu_temp for m in self.metrics_history]
        }
        
    def get_usage_history(self) -> Dict[str, list]:
        """使用率履歴の取得"""
        return {
            "timestamps": [m.timestamp for m in self.metrics_history],
            "cpu_usage": [m.cpu_usage for m in self.metrics_history],
            "gpu_usage": [m.gpu_usage for m in self.metrics_history],
            "memory_usage": [m.memory_usage for m in self.metrics_history]
=======
import psutil
import GPUtil
import logging
from typing import Dict, Any
import time
from dataclasses import dataclass
from datetime import datetime
from src.exceptions import HardwareMonitorError

@dataclass
class HardwareMetrics:
    """ハードウェアメトリクス"""
    cpu_temp: float = 0.0
    gpu_temp: float = 0.0
    cpu_usage: float = 0.0
    gpu_usage: float = 0.0
    memory_usage: float = 0.0
    timestamp: datetime = datetime.now()

class HardwareMonitor:
    """ハードウェアモニタリングクラス"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics_history = []
        self.warning_temp_threshold = 80.0  # 警告温度閾値
        self.critical_temp_threshold = 90.0  # 危険温度閾値
        
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
                self.logger.warning("GPUが見つかりません")
                return 0.0
            
            # 最も高い温度を返す
            return max(gpu.temperature for gpu in gpus)
            
        except Exception as e:
            self.logger.error(f"GPU温度取得エラー: {e}")
            raise HardwareMonitorError(f"GPU温度の取得に失敗: {e}")
            
    def get_metrics(self) -> HardwareMetrics:
        """ハードウェアメトリクスの取得"""
        try:
            # エラーが発生しても処理を継続
            try:
                cpu_temp = self.get_cpu_temperature()
            except HardwareMonitorError as e:
                self.logger.error(str(e))
                cpu_temp = 0.0
                
            try:
                gpu_temp = self.get_gpu_temperature()
            except HardwareMonitorError as e:
                self.logger.error(str(e))
                gpu_temp = 0.0
            
            # 温度警告のチェック
            self._check_temperature_warnings(cpu_temp, gpu_temp)
            
            metrics = HardwareMetrics(
                cpu_temp=cpu_temp,
                gpu_temp=gpu_temp,
                cpu_usage=self._get_cpu_usage(),
                gpu_usage=self._get_gpu_usage(),
                memory_usage=self._get_memory_usage(),
                timestamp=datetime.now()
            )
            
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > 1000:  # 履歴を1000件に制限
                self.metrics_history.pop(0)
                
            return metrics
            
        except Exception as e:
            self.logger.error(f"メトリクス取得エラー: {e}")
            return HardwareMetrics()
            
    def _get_cpu_usage(self) -> float:
        """CPU使用率の取得"""
        try:
            return psutil.cpu_percent()
        except Exception as e:
            self.logger.error(f"CPU使用率取得エラー: {e}")
            return 0.0
            
    def _get_gpu_usage(self) -> float:
        """GPU使用率の取得"""
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                return 0.0
            return max(gpu.load * 100 for gpu in gpus)
        except Exception as e:
            self.logger.error(f"GPU使用率取得エラー: {e}")
            return 0.0
            
    def _get_memory_usage(self) -> float:
        """メモリ使用率の取得"""
        try:
            return psutil.virtual_memory().percent
        except Exception as e:
            self.logger.error(f"メモリ使用率取得エラー: {e}")
            return 0.0
            
    def _check_temperature_warnings(self, cpu_temp: float, gpu_temp: float) -> None:
        """温度警告のチェック"""
        for device, temp in [("CPU", cpu_temp), ("GPU", gpu_temp)]:
            if temp >= self.critical_temp_threshold:
                self.logger.critical(
                    f"{device}温度が危険値に達しています: {temp}°C"
                )
            elif temp >= self.warning_temp_threshold:
                self.logger.warning(
                    f"{device}温度が警告値を超えています: {temp}°C"
                )
                
    def get_temperature_history(self) -> Dict[str, list]:
        """温度履歴の取得"""
        return {
            "timestamps": [m.timestamp for m in self.metrics_history],
            "cpu_temps": [m.cpu_temp for m in self.metrics_history],
            "gpu_temps": [m.gpu_temp for m in self.metrics_history]
        }
        
    def get_usage_history(self) -> Dict[str, list]:
        """使用率履歴の取得"""
        return {
            "timestamps": [m.timestamp for m in self.metrics_history],
            "cpu_usage": [m.cpu_usage for m in self.metrics_history],
            "gpu_usage": [m.gpu_usage for m in self.metrics_history],
            "memory_usage": [m.memory_usage for m in self.metrics_history]
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
        } 
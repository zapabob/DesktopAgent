<<<<<<< HEAD
# -*- coding: utf-8 -*-
"""Hardware monitoring module."""

import psutil
import GPUtil
from typing import Dict, Any

class HardwareMonitor:
    """ハードウェアモニタリングクラス"""
    def __init__(self):
        self.last_metrics = {}
        
    def get_metrics(self) -> Dict[str, Any]:
        """システムメトリクスの取得"""
        try:
            # CPU情報
            cpu_metrics = {
                'cpu_usage': psutil.cpu_percent(interval=1),
                'cpu_freq': psutil.cpu_freq().current if psutil.cpu_freq() else 0,
                'cpu_count': psutil.cpu_count()
            }
            
            # CPU温度の取得（オプション）
            try:
                cpu_temp = self._get_cpu_temperature()
                if cpu_temp > 0:
                    cpu_metrics['cpu_temp'] = cpu_temp
            except:
                cpu_metrics['cpu_temp'] = 0
            
            # メモリ情報
            memory = psutil.virtual_memory()
            memory_metrics = {
                'memory_total': memory.total,
                'memory_available': memory.available,
                'memory_usage': memory.percent
            }
            
            # GPU情報（オプション）
            try:
                gpu_metrics = self._get_gpu_metrics()
            except:
                gpu_metrics = {
                    'gpu_usage': 0,
                    'gpu_memory_usage': 0,
                    'gpu_temperature': 0,
                    'gpu_memory_total': 0,
                    'gpu_memory_used': 0
                }
            
            # ディスク情報
            disk = psutil.disk_usage('/')
            disk_metrics = {
                'disk_total': disk.total,
                'disk_used': disk.used,
                'disk_free': disk.free,
                'disk_percent': disk.percent
            }
            
            # ネットワーク情報
            network = psutil.net_io_counters()
            network_metrics = {
                'net_bytes_sent': network.bytes_sent,
                'net_bytes_recv': network.bytes_recv,
                'net_packets_sent': network.packets_sent,
                'net_packets_recv': network.packets_recv
            }
            
            metrics = {
                **cpu_metrics,
                **memory_metrics,
                **gpu_metrics,
                **disk_metrics,
                **network_metrics
            }
            
            self.last_metrics = metrics
            return metrics
            
        except Exception as e:
            self.logger.error(f"メトリクス取得エラー: {e}")
            # 最後の有効なメトリクスを返すか、デフォルト値を設定
            return self.last_metrics or {
                'cpu_usage': 0,
                'memory_usage': 0,
                'gpu_usage': 0,
                'cpu_temp': 0,
                'gpu_temperature': 0
            }
            
    def _get_cpu_temperature(self) -> float:
        """CPU温度の取得"""
        try:
            # Windowsの場合
            import wmi
            w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            temperature_infos = w.Sensor()
            for sensor in temperature_infos:
                if sensor.SensorType == 'Temperature' and 'CPU' in sensor.Name:
                    return float(sensor.Value)
        except:
            pass
            
        try:
            # Linuxの場合
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = float(f.read()) / 1000.0
                return temp
        except:
            pass
            
        return 0.0
        
    def _get_gpu_metrics(self) -> Dict[str, Any]:
        """GPU情報の取得"""
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # 最初のGPUの情報を使用
                return {
                    'gpu_usage': gpu.load * 100,
                    'gpu_memory_usage': gpu.memoryUtil * 100,
                    'gpu_temperature': gpu.temperature,
                    'gpu_memory_total': gpu.memoryTotal,
                    'gpu_memory_used': gpu.memoryUsed
                }
        except:
            pass
            
        return {
            'gpu_usage': 0,
            'gpu_memory_usage': 0,
            'gpu_temperature': 0,
            'gpu_memory_total': 0,
            'gpu_memory_used': 0
=======
# -*- coding: utf-8 -*-
"""Hardware monitoring module."""

import psutil
import GPUtil
from typing import Dict, Any

class HardwareMonitor:
    """ハードウェアモニタリングクラス"""
    def __init__(self):
        self.last_metrics = {}
        
    def get_metrics(self) -> Dict[str, Any]:
        """システムメトリクスの取得"""
        try:
            # CPU情報
            cpu_metrics = {
                'cpu_usage': psutil.cpu_percent(interval=1),
                'cpu_freq': psutil.cpu_freq().current if psutil.cpu_freq() else 0,
                'cpu_count': psutil.cpu_count()
            }
            
            # CPU温度の取得（オプション）
            try:
                cpu_temp = self._get_cpu_temperature()
                if cpu_temp > 0:
                    cpu_metrics['cpu_temp'] = cpu_temp
            except:
                cpu_metrics['cpu_temp'] = 0
            
            # メモリ情報
            memory = psutil.virtual_memory()
            memory_metrics = {
                'memory_total': memory.total,
                'memory_available': memory.available,
                'memory_usage': memory.percent
            }
            
            # GPU情報（オプション）
            try:
                gpu_metrics = self._get_gpu_metrics()
            except:
                gpu_metrics = {
                    'gpu_usage': 0,
                    'gpu_memory_usage': 0,
                    'gpu_temperature': 0,
                    'gpu_memory_total': 0,
                    'gpu_memory_used': 0
                }
            
            # ディスク情報
            disk = psutil.disk_usage('/')
            disk_metrics = {
                'disk_total': disk.total,
                'disk_used': disk.used,
                'disk_free': disk.free,
                'disk_percent': disk.percent
            }
            
            # ネットワーク情報
            network = psutil.net_io_counters()
            network_metrics = {
                'net_bytes_sent': network.bytes_sent,
                'net_bytes_recv': network.bytes_recv,
                'net_packets_sent': network.packets_sent,
                'net_packets_recv': network.packets_recv
            }
            
            metrics = {
                **cpu_metrics,
                **memory_metrics,
                **gpu_metrics,
                **disk_metrics,
                **network_metrics
            }
            
            self.last_metrics = metrics
            return metrics
            
        except Exception as e:
            self.logger.error(f"メトリクス取得エラー: {e}")
            # 最後の有効なメトリクスを返すか、デフォルト値を設定
            return self.last_metrics or {
                'cpu_usage': 0,
                'memory_usage': 0,
                'gpu_usage': 0,
                'cpu_temp': 0,
                'gpu_temperature': 0
            }
            
    def _get_cpu_temperature(self) -> float:
        """CPU温度の取得"""
        try:
            # Windowsの場合
            import wmi
            w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            temperature_infos = w.Sensor()
            for sensor in temperature_infos:
                if sensor.SensorType == 'Temperature' and 'CPU' in sensor.Name:
                    return float(sensor.Value)
        except:
            pass
            
        try:
            # Linuxの場合
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = float(f.read()) / 1000.0
                return temp
        except:
            pass
            
        return 0.0
        
    def _get_gpu_metrics(self) -> Dict[str, Any]:
        """GPU情報の取得"""
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # 最初のGPUの情報を使用
                return {
                    'gpu_usage': gpu.load * 100,
                    'gpu_memory_usage': gpu.memoryUtil * 100,
                    'gpu_temperature': gpu.temperature,
                    'gpu_memory_total': gpu.memoryTotal,
                    'gpu_memory_used': gpu.memoryUsed
                }
        except:
            pass
            
        return {
            'gpu_usage': 0,
            'gpu_memory_usage': 0,
            'gpu_temperature': 0,
            'gpu_memory_total': 0,
            'gpu_memory_used': 0
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
        } 
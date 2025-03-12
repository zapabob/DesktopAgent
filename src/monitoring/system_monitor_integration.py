import logging
from typing import Dict, Any, List, Optional
import time
import threading
import os
from pathlib import Path
import json
from datetime import datetime, timedelta

from .hardware_monitor import HardwareMonitor, HardwareMetrics
from .metrics_exporter import MetricsExporter
from .alert_manager import AlertManager

class SystemMonitorIntegration:
    """システムモニタリング統合クラス
    
    ハードウェアモニターとメトリクスエクスポーターを統合し、
    システムモニタリングの全体フローを管理します。
    """
    
    def __init__(self, monitoring_interval: int = 5, 
                 export_interval: int = 3600,
                 max_history_size: int = 500,
                 export_dir: str = "monitoring_data"):
        """初期化
        
        Args:
            monitoring_interval: モニタリング間隔（秒）
            export_interval: エクスポート間隔（秒）
            max_history_size: 履歴の最大保持サイズ
            export_dir: データエクスポート先ディレクトリ
        """
        self.logger = logging.getLogger(__name__)
        
        # 各コンポーネントの初期化
        self.hardware_monitor = HardwareMonitor(max_history_size=max_history_size)
        self.metrics_exporter = MetricsExporter(export_dir=export_dir)
        self.alert_manager = AlertManager()
        
        # モニタリング設定
        self.monitoring_interval = monitoring_interval
        self.export_interval = export_interval
        self.max_history_size = max_history_size
        
        # 監視スレッド
        self._monitoring_running = False
        self._monitoring_thread = None
        
        # 前回のエクスポート時刻
        self.last_export_time = datetime.now()
        
        # 初期化ログ
        self.logger.info(f"システムモニタリング統合を初期化しました（監視間隔: {monitoring_interval}秒, エクスポート間隔: {export_interval}秒）")
    
    def start_monitoring(self) -> None:
        """モニタリングの開始"""
        if self._monitoring_running:
            self.logger.warning("モニタリングはすでに実行中です")
            return
            
        self._monitoring_running = True
        
        def monitoring_job():
            """モニタリングジョブのメイン処理"""
            self.logger.info("システムモニタリングを開始しました")
            
            alerts_buffer = []
            
            while self._monitoring_running:
                try:
                    # ハードウェアメトリクスの取得
                    metrics = self.hardware_monitor.get_metrics()
                    
                    # アラートチェック
                    alerts = self._check_for_alerts(metrics)
                    if alerts:
                        alerts_buffer.extend(alerts)
                        
                        # アラートが蓄積されたらエクスポート
                        if len(alerts_buffer) >= 10:
                            self.metrics_exporter.export_alert_history(
                                alerts_buffer, 
                                f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                            )
                            alerts_buffer = []
                    
                    # 定期的なエクスポート
                    now = datetime.now()
                    if (now - self.last_export_time).total_seconds() >= self.export_interval:
                        self._export_metrics()
                        self.last_export_time = now
                        
                except Exception as e:
                    self.logger.error(f"モニタリング中にエラーが発生しました: {e}")
                
                # 次の監視まで待機
                time.sleep(self.monitoring_interval)
            
            # 残りのアラートをエクスポート
            if alerts_buffer:
                try:
                    self.metrics_exporter.export_alert_history(
                        alerts_buffer, 
                        f"alerts_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    )
                except Exception as e:
                    self.logger.error(f"最終アラートエクスポート中にエラーが発生しました: {e}")
            
            self.logger.info("システムモニタリングを停止しました")
                
        # バックグラウンドスレッドで監視ジョブを実行
        self._monitoring_thread = threading.Thread(target=monitoring_job, daemon=True)
        self._monitoring_thread.start()
        
    def stop_monitoring(self) -> None:
        """モニタリングの停止"""
        if not self._monitoring_running:
            self.logger.warning("モニタリングは実行されていません")
            return
            
        self._monitoring_running = False
        if self._monitoring_thread:
            # スレッドが終了するのを待機（最大10秒）
            self._monitoring_thread.join(10.0)
            self._monitoring_thread = None
            
        # 最終的なメトリクスをエクスポート
        self._export_metrics(is_final=True)
        
        self.logger.info("システムモニタリングを停止しました")
    
    def _check_for_alerts(self, metrics: HardwareMetrics) -> List[Dict[str, Any]]:
        """メトリクスからアラートを検出
        
        Args:
            metrics: 検査するハードウェアメトリクス
            
        Returns:
            検出されたアラートのリスト
        """
        alerts = []
        
        # CPU温度アラート
        if metrics.cpu_temp >= 85:
            alerts.append(self.alert_manager.create_alert(
                alert_type="temperature",
                message=f"CPU温度が危険レベルに達しています: {metrics.cpu_temp:.1f}°C",
                severity="critical",
                value=metrics.cpu_temp,
                threshold=85
            ))
        elif metrics.cpu_temp >= 75:
            alerts.append(self.alert_manager.create_alert(
                alert_type="temperature",
                message=f"CPU温度が高温です: {metrics.cpu_temp:.1f}°C",
                severity="warning",
                value=metrics.cpu_temp,
                threshold=75
            ))
        
        # GPU温度アラート
        if metrics.gpu_temp >= 85:
            alerts.append(self.alert_manager.create_alert(
                alert_type="temperature",
                message=f"GPU温度が危険レベルに達しています: {metrics.gpu_temp:.1f}°C",
                severity="critical",
                value=metrics.gpu_temp,
                threshold=85
            ))
        elif metrics.gpu_temp >= 75:
            alerts.append(self.alert_manager.create_alert(
                alert_type="temperature",
                message=f"GPU温度が高温です: {metrics.gpu_temp:.1f}°C",
                severity="warning",
                value=metrics.gpu_temp,
                threshold=75
            ))
        
        # CPU使用率アラート
        if metrics.cpu_usage >= 90:
            alerts.append(self.alert_manager.create_alert(
                alert_type="usage",
                message=f"CPU使用率が非常に高くなっています: {metrics.cpu_usage:.1f}%",
                severity="warning",
                value=metrics.cpu_usage,
                threshold=90
            ))
        
        # メモリ使用率アラート
        if metrics.memory_usage >= 95:
            alerts.append(self.alert_manager.create_alert(
                alert_type="memory",
                message=f"メモリ使用率が危険レベルに達しています: {metrics.memory_usage:.1f}%",
                severity="critical",
                value=metrics.memory_usage,
                threshold=95
            ))
        elif metrics.memory_usage >= 85:
            alerts.append(self.alert_manager.create_alert(
                alert_type="memory",
                message=f"メモリ使用率が高くなっています: {metrics.memory_usage:.1f}%",
                severity="warning",
                value=metrics.memory_usage,
                threshold=85
            ))
            
        return alerts
    
    def _export_metrics(self, is_final: bool = False) -> None:
        """メトリクスのエクスポート処理
        
        Args:
            is_final: 最終エクスポートかどうか
        """
        try:
            # メトリクス履歴の取得
            temp_history = self.hardware_monitor.get_temperature_history()
            usage_history = self.hardware_monitor.get_usage_history()
            
            # 履歴データをマージ
            merged_history = []
            for i in range(len(self.hardware_monitor.metrics_history)):
                metrics = self.hardware_monitor.metrics_history[i]
                merged_history.append(metrics.to_dict())
            
            # CSVエクスポート
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            prefix = "final_" if is_final else ""
            
            if merged_history:
                # メトリクスデータCSV
                self.metrics_exporter.export_history_to_csv(
                    merged_history, 
                    f"{prefix}metrics_history_{timestamp}.csv"
                )
                
                # JSONエクスポート
                self.metrics_exporter.export_to_json(
                    {"temperature": temp_history, "usage": usage_history},
                    f"{prefix}metrics_summary_{timestamp}.json"
                )
                
                # 視覚化
                self.metrics_exporter.visualize_hardware_metrics(
                    merged_history,
                    f"{prefix}hardware_metrics_{timestamp}.png"
                )
                
            self.logger.info(f"メトリクスデータをエクスポートしました (final={is_final})")
            
        except Exception as e:
            self.logger.error(f"メトリクスエクスポート中にエラーが発生しました: {e}")
    
    def get_current_metrics(self) -> HardwareMetrics:
        """現在のメトリクスを取得
        
        Returns:
            現在のハードウェアメトリクス
        """
        return self.hardware_monitor.get_metrics()
    
    def get_metrics_history(self) -> List[Dict[str, Any]]:
        """メトリクス履歴を取得
        
        Returns:
            メトリクス履歴のリスト
        """
        return [m.to_dict() for m in self.hardware_monitor.metrics_history]
    
    def get_gpu_details(self) -> Dict[str, Any]:
        """GPUの詳細情報を取得
        
        Returns:
            GPU情報の辞書
        """
        return self.hardware_monitor.get_gpu_details()
    
    def export_current_metrics(self, format: str = 'json') -> str:
        """現在のメトリクスをエクスポート
        
        Args:
            format: エクスポート形式 ('json'または'csv')
            
        Returns:
            エクスポートされたファイルのパス
        """
        metrics = self.hardware_monitor.get_metrics()
        
        if format.lower() == 'json':
            return self.metrics_exporter.export_to_json(metrics.to_dict())
        else:
            return self.metrics_exporter.export_to_csv(metrics.to_dict())
    
    def clear_metrics_history(self) -> None:
        """メトリクス履歴のクリア"""
        self.hardware_monitor.clear_history()
        self.logger.info("メトリクス履歴をクリアしました")
    
    def __del__(self):
        """デストラクタ"""
        if self._monitoring_running:
            self.stop_monitoring() 
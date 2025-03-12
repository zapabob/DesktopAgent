import asyncio
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from src.monitoring.metrics_exporter import MetricsExporter

class AutoExport:
    """メトリクス自動エクスポートクラス"""
    def __init__(self, vector_store, export_dir: str = "auto_exports",
                export_interval_hours: int = 1,
                retention_days: int = 7):
        self.vector_store = vector_store
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.export_interval = timedelta(hours=export_interval_hours)
        self.retention_period = timedelta(days=retention_days)
        self.logger = logging.getLogger(__name__)
        self.last_export = None
        self.export_task = None
        self.exporter = MetricsExporter(export_dir)
        
    async def start(self):
        """エクスポートタスクの開始"""
        self.export_task = asyncio.create_task(self._export_loop())
        
    async def stop(self):
        """エクスポートタスクの停止"""
        if self.export_task:
            self.export_task.cancel()
            try:
                await self.export_task
            except asyncio.CancelledError:
                pass
                
    async def _export_loop(self):
        """エクスポートループ"""
        while True:
            try:
                await self._check_and_export()
                await self._cleanup_old_exports()
                await asyncio.sleep(300)  # 5分ごとにチェック
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"エクスポートループエラー: {e}")
                await asyncio.sleep(300)
                
    async def _check_and_export(self):
        """エクスポートの必要性チェックと実行"""
        now = datetime.now()
        
        # 最初のエクスポートまたは指定時間経過後
        if not self.last_export or \
           now - self.last_export > self.export_interval:
            try:
                await self._perform_export()
                self.last_export = now
            except Exception as e:
                self.logger.error(f"エクスポート実行エラー: {e}")
                
    async def _perform_export(self):
        """エクスポートの実行"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # ハードウェアメトリクスのエクスポート
            hw_metrics = await self.vector_store.get_hardware_metrics()
            await self.exporter.async_export_to_json(
                hw_metrics,
                f"hardware_metrics_{timestamp}.json"
            )
            
            # パフォーマンスメトリクスのエクスポート
            perf_metrics = await self.vector_store.get_metrics()
            await self.exporter.async_export_to_json(
                perf_metrics,
                f"performance_metrics_{timestamp}.json"
            )
            
            # アラート履歴のエクスポート
            alerts = await self.vector_store.alert_manager.get_alert_history()
            await self.exporter.async_export_alert_history(
                alerts,
                f"alerts_{timestamp}.csv"
            )
            
            self.logger.info(f"メトリクスを自動エクスポート: {timestamp}")
            
        except Exception as e:
            self.logger.error(f"エクスポート作成エラー: {e}")
            raise
            
    async def _cleanup_old_exports(self):
        """古いエクスポートファイルの削除"""
        try:
            now = datetime.now()
            for file_path in self.export_dir.glob("*"):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if now - file_time > self.retention_period:
                        file_path.unlink()
                        self.logger.info(f"古いエクスポートを削除: {file_path}")
                        
        except Exception as e:
            self.logger.error(f"エクスポートクリーンアップエラー: {e}")
            
    async def get_export_info(self) -> Dict[str, Any]:
        """エクスポート情報の取得"""
        return {
            "last_export": self.last_export.isoformat() if self.last_export else None,
            "export_interval_hours": self.export_interval.total_seconds() / 3600,
            "retention_days": self.retention_period.days,
            "export_dir": str(self.export_dir)
        }
        
    async def export_now(self) -> Dict[str, str]:
        """即時エクスポートの実行"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result = {}
            
            # ハードウェアメトリクス
            hw_file = await self.exporter.async_export_to_json(
                await self.vector_store.get_hardware_metrics(),
                f"hardware_metrics_{timestamp}.json"
            )
            result["hardware"] = hw_file
            
            # パフォーマンスメトリクス
            perf_file = await self.exporter.async_export_to_json(
                await self.vector_store.get_metrics(),
                f"performance_metrics_{timestamp}.json"
            )
            result["performance"] = perf_file
            
            # アラート履歴
            alert_file = await self.exporter.async_export_alert_history(
                await self.vector_store.alert_manager.get_alert_history(),
                f"alerts_{timestamp}.csv"
            )
            result["alerts"] = alert_file
            
            self.last_export = datetime.now()
            return result
            
        except Exception as e:
            self.logger.error(f"即時エクスポートエラー: {e}")
            raise 
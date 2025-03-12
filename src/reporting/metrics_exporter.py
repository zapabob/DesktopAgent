<<<<<<< HEAD
import asyncio
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, Any, List, Optional

class MetricsExporter:
    """メトリクスエクスポート管理クラス"""
    def __init__(self,
                export_dir: str = "exports",
                interval_hours: int = 1):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.interval = timedelta(hours=interval_hours)
        self.last_export = None
        self.running = False
        self.logger = logging.getLogger(__name__)
        
    async def start(self):
        """エクスポートタスクの開始"""
        if self.running:
            return
            
        self.running = True
        while self.running:
            try:
                if self._should_export():
                    await self._perform_export()
                await asyncio.sleep(60)
            except Exception as e:
                self.logger.error(f"エクスポートエラー: {e}")
                
    def stop(self):
        """エクスポートタスクの停止"""
        self.running = False
        
    def _should_export(self) -> bool:
        """エクスポートが必要かどうかを判断"""
        if not self.last_export:
            return True
        return datetime.now() - self.last_export >= self.interval
        
    async def _perform_export(self):
        """エクスポートの実行"""
        try:
            timestamp = datetime.now()
            metrics = await self._collect_metrics()
            
            # JSONエクスポート
            json_path = self.export_dir / f"metrics_{timestamp:%Y%m%d_%H%M%S}.json"
            with open(json_path, "w") as f:
                json.dump({
                    "timestamp": timestamp.isoformat(),
                    "metrics": metrics
                }, f, indent=2)
                
            # CSVエクスポート
            csv_path = self.export_dir / f"metrics_{timestamp:%Y%m%d_%H%M%S}.csv"
            self._export_to_csv(metrics, csv_path)
            
            self.last_export = timestamp
            self.logger.info(f"メトリクスエクスポート完了: {json_path}, {csv_path}")
            
        except Exception as e:
            self.logger.error(f"エクスポート実行エラー: {e}")
            raise
            
    async def _collect_metrics(self) -> Dict[str, Any]:
        """メトリクスの収集"""
        # TODO: 実際のメトリクス収集ロジックを実装
        return {}
        
    def _export_to_csv(self, metrics: Dict[str, Any], path: Path):
        """メトリクスをCSV形式でエクスポート"""
        try:
            # メトリクスをフラット化
            flat_metrics = self._flatten_metrics(metrics)
            
            # CSVファイルに書き込み
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["metric", "value", "timestamp"])
                for key, value in flat_metrics.items():
                    writer.writerow([key, value, datetime.now().isoformat()])
                    
        except Exception as e:
            self.logger.error(f"CSVエクスポートエラー: {e}")
            raise
            
    def _flatten_metrics(self, metrics: Dict[str, Any],
                       parent_key: str = "") -> Dict[str, Any]:
        """階層構造のメトリクスをフラット化"""
        items = []
        for key, value in metrics.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            
            if isinstance(value, dict):
                items.extend(
                    self._flatten_metrics(value, new_key).items()
                )
            else:
                items.append((new_key, value))
                
=======
import asyncio
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, Any, List, Optional

class MetricsExporter:
    """メトリクスエクスポート管理クラス"""
    def __init__(self,
                export_dir: str = "exports",
                interval_hours: int = 1):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.interval = timedelta(hours=interval_hours)
        self.last_export = None
        self.running = False
        self.logger = logging.getLogger(__name__)
        
    async def start(self):
        """エクスポートタスクの開始"""
        if self.running:
            return
            
        self.running = True
        while self.running:
            try:
                if self._should_export():
                    await self._perform_export()
                await asyncio.sleep(60)
            except Exception as e:
                self.logger.error(f"エクスポートエラー: {e}")
                
    def stop(self):
        """エクスポートタスクの停止"""
        self.running = False
        
    def _should_export(self) -> bool:
        """エクスポートが必要かどうかを判断"""
        if not self.last_export:
            return True
        return datetime.now() - self.last_export >= self.interval
        
    async def _perform_export(self):
        """エクスポートの実行"""
        try:
            timestamp = datetime.now()
            metrics = await self._collect_metrics()
            
            # JSONエクスポート
            json_path = self.export_dir / f"metrics_{timestamp:%Y%m%d_%H%M%S}.json"
            with open(json_path, "w") as f:
                json.dump({
                    "timestamp": timestamp.isoformat(),
                    "metrics": metrics
                }, f, indent=2)
                
            # CSVエクスポート
            csv_path = self.export_dir / f"metrics_{timestamp:%Y%m%d_%H%M%S}.csv"
            self._export_to_csv(metrics, csv_path)
            
            self.last_export = timestamp
            self.logger.info(f"メトリクスエクスポート完了: {json_path}, {csv_path}")
            
        except Exception as e:
            self.logger.error(f"エクスポート実行エラー: {e}")
            raise
            
    async def _collect_metrics(self) -> Dict[str, Any]:
        """メトリクスの収集"""
        # TODO: 実際のメトリクス収集ロジックを実装
        return {}
        
    def _export_to_csv(self, metrics: Dict[str, Any], path: Path):
        """メトリクスをCSV形式でエクスポート"""
        try:
            # メトリクスをフラット化
            flat_metrics = self._flatten_metrics(metrics)
            
            # CSVファイルに書き込み
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["metric", "value", "timestamp"])
                for key, value in flat_metrics.items():
                    writer.writerow([key, value, datetime.now().isoformat()])
                    
        except Exception as e:
            self.logger.error(f"CSVエクスポートエラー: {e}")
            raise
            
    def _flatten_metrics(self, metrics: Dict[str, Any],
                       parent_key: str = "") -> Dict[str, Any]:
        """階層構造のメトリクスをフラット化"""
        items = []
        for key, value in metrics.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            
            if isinstance(value, dict):
                items.extend(
                    self._flatten_metrics(value, new_key).items()
                )
            else:
                items.append((new_key, value))
                
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
        return dict(items) 
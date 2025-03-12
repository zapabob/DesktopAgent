<<<<<<< HEAD
import pandas as pd
from typing import Dict, Any, List
import json
from pathlib import Path
import csv
from datetime import datetime
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

class MetricsExporter:
    """メトリクスエクスポートクラス"""
    def __init__(self, export_dir: str = "metrics_export"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    def export_to_csv(self, metrics: Dict[str, Any], file_name: str = None) -> str:
        """CSVフォーマットでエクスポート"""
        try:
            if file_name is None:
                file_name = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
            file_path = self.export_dir / file_name
            
            # メトリクスをフラット化
            flat_metrics = self._flatten_metrics(metrics)
            
            # DataFrameに変換してCSV出力
            df = pd.DataFrame([flat_metrics])
            df.to_csv(file_path, index=False)
            
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"CSVエクスポートエラー: {e}")
            raise
            
    def export_to_json(self, metrics: Dict[str, Any], file_name: str = None) -> str:
        """JSONフォーマットでエクスポート"""
        try:
            if file_name is None:
                file_name = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
            file_path = self.export_dir / file_name
            
            with open(file_path, "w") as f:
                json.dump(metrics, f, indent=2, default=str)
                
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"JSONエクスポートエラー: {e}")
            raise
            
    def export_history_to_csv(self, history: List[Dict[str, Any]], file_name: str = None) -> str:
        """履歴データをCSVフォーマットでエクスポート"""
        try:
            if file_name is None:
                file_name = f"history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
            file_path = self.export_dir / file_name
            
            # 履歴データをフラット化
            flat_history = [self._flatten_metrics(m) for m in history]
            
            # DataFrameに変換してCSV出力
            df = pd.DataFrame(flat_history)
            df.to_csv(file_path, index=False)
            
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"履歴CSVエクスポートエラー: {e}")
            raise
            
    def _flatten_metrics(self, metrics: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
        """メトリクスの階層構造をフラット化"""
        items = []
        for k, v in metrics.items():
            new_key = f"{parent_key}_{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(self._flatten_metrics(v, new_key).items())
            elif isinstance(v, list):
                # リストの場合は統計値を計算
                if all(isinstance(x, (int, float)) for x in v):
                    items.extend([
                        (f"{new_key}_mean", sum(v) / len(v) if v else 0),
                        (f"{new_key}_max", max(v) if v else 0),
                        (f"{new_key}_min", min(v) if v else 0)
                    ])
                else:
                    items.append((new_key, str(v)))
            else:
                items.append((new_key, v))
                
        return dict(items)
        
    def export_alert_history(self, alerts: List[Dict[str, Any]], file_name: str = None) -> str:
        """アラート履歴のエクスポート"""
        try:
            if file_name is None:
                file_name = f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
            file_path = self.export_dir / file_name
            
            # 必要なフィールドを抽出
            alert_data = []
            for alert in alerts:
                alert_data.append({
                    "timestamp": alert["timestamp"],
                    "type": alert["type"],
                    "severity": alert["severity"],
                    "message": alert["message"]
                })
                
            # DataFrameに変換してCSV出力
            df = pd.DataFrame(alert_data)
            df.to_csv(file_path, index=False)
            
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"アラート履歴エクスポートエラー: {e}")
            raise
            
    def export_optimization_history(self, history: Dict[str, Any], file_name: str = None) -> str:
        """最適化履歴のエクスポート"""
        try:
            if file_name is None:
                file_name = f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
            file_path = self.export_dir / file_name
            
            with open(file_path, "w") as f:
                json.dump(history, f, indent=2, default=str)
                
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"最適化履歴エクスポートエラー: {e}")
            raise
        
    async def async_export_to_csv(self, metrics: Dict[str, Any], file_name: str = None) -> str:
        """CSVフォーマットで非同期エクスポート"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.export_to_csv,
            metrics,
            file_name
        )
        
    async def async_export_to_json(self, metrics: Dict[str, Any], file_name: str = None) -> str:
        """JSONフォーマットで非同期エクスポート"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.export_to_json,
            metrics,
            file_name
        )
        
    async def async_export_history_to_csv(self, history: List[Dict[str, Any]], file_name: str = None) -> str:
        """履歴データを非同期でCSVエクスポート"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.export_history_to_csv,
            history,
            file_name
        )
        
    async def async_export_alert_history(self, alerts: List[Dict[str, Any]], file_name: str = None) -> str:
        """アラート履歴を非同期でエクスポート"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.export_alert_history,
            alerts,
            file_name
        )
        
    async def async_export_optimization_history(self, history: Dict[str, Any], file_name: str = None) -> str:
        """最適化履歴を非同期でエクスポート"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.export_optimization_history,
            history,
            file_name
        )
        
    def __del__(self):
        """デストラクタ"""
=======
import pandas as pd
from typing import Dict, Any, List
import json
from pathlib import Path
import csv
from datetime import datetime
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

class MetricsExporter:
    """メトリクスエクスポートクラス"""
    def __init__(self, export_dir: str = "metrics_export"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    def export_to_csv(self, metrics: Dict[str, Any], file_name: str = None) -> str:
        """CSVフォーマットでエクスポート"""
        try:
            if file_name is None:
                file_name = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
            file_path = self.export_dir / file_name
            
            # メトリクスをフラット化
            flat_metrics = self._flatten_metrics(metrics)
            
            # DataFrameに変換してCSV出力
            df = pd.DataFrame([flat_metrics])
            df.to_csv(file_path, index=False)
            
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"CSVエクスポートエラー: {e}")
            raise
            
    def export_to_json(self, metrics: Dict[str, Any], file_name: str = None) -> str:
        """JSONフォーマットでエクスポート"""
        try:
            if file_name is None:
                file_name = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
            file_path = self.export_dir / file_name
            
            with open(file_path, "w") as f:
                json.dump(metrics, f, indent=2, default=str)
                
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"JSONエクスポートエラー: {e}")
            raise
            
    def export_history_to_csv(self, history: List[Dict[str, Any]], file_name: str = None) -> str:
        """履歴データをCSVフォーマットでエクスポート"""
        try:
            if file_name is None:
                file_name = f"history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
            file_path = self.export_dir / file_name
            
            # 履歴データをフラット化
            flat_history = [self._flatten_metrics(m) for m in history]
            
            # DataFrameに変換してCSV出力
            df = pd.DataFrame(flat_history)
            df.to_csv(file_path, index=False)
            
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"履歴CSVエクスポートエラー: {e}")
            raise
            
    def _flatten_metrics(self, metrics: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
        """メトリクスの階層構造をフラット化"""
        items = []
        for k, v in metrics.items():
            new_key = f"{parent_key}_{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(self._flatten_metrics(v, new_key).items())
            elif isinstance(v, list):
                # リストの場合は統計値を計算
                if all(isinstance(x, (int, float)) for x in v):
                    items.extend([
                        (f"{new_key}_mean", sum(v) / len(v) if v else 0),
                        (f"{new_key}_max", max(v) if v else 0),
                        (f"{new_key}_min", min(v) if v else 0)
                    ])
                else:
                    items.append((new_key, str(v)))
            else:
                items.append((new_key, v))
                
        return dict(items)
        
    def export_alert_history(self, alerts: List[Dict[str, Any]], file_name: str = None) -> str:
        """アラート履歴のエクスポート"""
        try:
            if file_name is None:
                file_name = f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
            file_path = self.export_dir / file_name
            
            # 必要なフィールドを抽出
            alert_data = []
            for alert in alerts:
                alert_data.append({
                    "timestamp": alert["timestamp"],
                    "type": alert["type"],
                    "severity": alert["severity"],
                    "message": alert["message"]
                })
                
            # DataFrameに変換してCSV出力
            df = pd.DataFrame(alert_data)
            df.to_csv(file_path, index=False)
            
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"アラート履歴エクスポートエラー: {e}")
            raise
            
    def export_optimization_history(self, history: Dict[str, Any], file_name: str = None) -> str:
        """最適化履歴のエクスポート"""
        try:
            if file_name is None:
                file_name = f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
            file_path = self.export_dir / file_name
            
            with open(file_path, "w") as f:
                json.dump(history, f, indent=2, default=str)
                
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"最適化履歴エクスポートエラー: {e}")
            raise
        
    async def async_export_to_csv(self, metrics: Dict[str, Any], file_name: str = None) -> str:
        """CSVフォーマットで非同期エクスポート"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.export_to_csv,
            metrics,
            file_name
        )
        
    async def async_export_to_json(self, metrics: Dict[str, Any], file_name: str = None) -> str:
        """JSONフォーマットで非同期エクスポート"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.export_to_json,
            metrics,
            file_name
        )
        
    async def async_export_history_to_csv(self, history: List[Dict[str, Any]], file_name: str = None) -> str:
        """履歴データを非同期でCSVエクスポート"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.export_history_to_csv,
            history,
            file_name
        )
        
    async def async_export_alert_history(self, alerts: List[Dict[str, Any]], file_name: str = None) -> str:
        """アラート履歴を非同期でエクスポート"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.export_alert_history,
            alerts,
            file_name
        )
        
    async def async_export_optimization_history(self, history: Dict[str, Any], file_name: str = None) -> str:
        """最適化履歴を非同期でエクスポート"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.export_optimization_history,
            history,
            file_name
        )
        
    def __del__(self):
        """デストラクタ"""
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
        self.executor.shutdown(wait=False) 
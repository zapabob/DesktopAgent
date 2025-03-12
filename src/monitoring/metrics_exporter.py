import pandas as pd
from typing import Dict, Any, List, Optional, Union, Callable
import json
from pathlib import Path
import csv
from datetime import datetime, timedelta
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import seaborn as sns
import os
import time
import threading
from dataclasses import asdict

class MetricsExporter:
    """メトリクスデータをさまざまな形式でエクスポートするクラス"""
    
    def __init__(self, export_dir: str = "metrics_export"):
        """初期化
        
        Args:
            export_dir: エクスポート先ディレクトリ
        """
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        # 視覚化エクスポート用ディレクトリ
        self.visualizations_dir = self.export_dir / "visualizations"
        self.visualizations_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # 定期的なエクスポートのスケジュールフラグ
        self._scheduled_export_running = False
        self._scheduled_export_thread = None
        
    def export_to_csv(self, metrics: Dict[str, Any], file_name: Optional[str] = None) -> str:
        """メトリクスをCSVファイルとしてエクスポート
        
        Args:
            metrics: エクスポートするメトリクスデータ
            file_name: 出力ファイル名（省略時は自動生成）
            
        Returns:
            エクスポート先のファイルパス
        """
        try:
            if file_name is None:
                file_name = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
            file_path = self.export_dir / file_name
            
            # メトリクスをフラット化
            flat_metrics = self._flatten_metrics(metrics)
            
            # DataFrameに変換してCSV出力
            df = pd.DataFrame([flat_metrics])
            df.to_csv(file_path, index=False)
            
            self.logger.info(f"メトリクスをCSVファイルにエクスポートしました: {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"CSVエクスポートエラー: {e}")
            raise
            
    def export_to_json(self, metrics: Dict[str, Any], file_name: Optional[str] = None) -> str:
        """メトリクスをJSONファイルとしてエクスポート
        
        Args:
            metrics: エクスポートするメトリクスデータ
            file_name: 出力ファイル名（省略時は自動生成）
            
        Returns:
            エクスポート先のファイルパス
        """
        try:
            if file_name is None:
                file_name = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
            file_path = self.export_dir / file_name
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"メトリクスをJSONファイルにエクスポートしました: {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"JSONエクスポートエラー: {e}")
            raise
            
    def export_history_to_csv(self, history: List[Dict[str, Any]], file_name: Optional[str] = None) -> str:
        """メトリクス履歴をCSVファイルとしてエクスポート
        
        Args:
            history: エクスポートする履歴データ
            file_name: 出力ファイル名（省略時は自動生成）
            
        Returns:
            エクスポート先のファイルパス
        """
        try:
            if file_name is None:
                file_name = f"metrics_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
            file_path = self.export_dir / file_name
            
            # DataFrameに変換してCSV出力
            df = pd.DataFrame([self._flatten_metrics(item) for item in history])
            df.to_csv(file_path, index=False)
            
            self.logger.info(f"メトリクス履歴をCSVファイルにエクスポートしました: {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"履歴CSVエクスポートエラー: {e}")
            raise
            
    def _flatten_metrics(self, metrics: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
        """ネストされたメトリクスをフラット化
        
        Args:
            metrics: フラット化するメトリクスデータ
            parent_key: 親キー（再帰呼び出し用）
            
        Returns:
            フラット化されたメトリクスデータ
        """
        items = {}
        for k, v in metrics.items():
            new_key = f"{parent_key}_{k}" if parent_key else k
            
            if isinstance(v, dict):
                # 再帰的にフラット化
                items.update(self._flatten_metrics(v, new_key))
            else:
                items[new_key] = v
                
        return items
    
    def export_alert_history(self, alerts: List[Dict[str, Any]], file_name: Optional[str] = None) -> str:
        """アラート履歴をCSVファイルとしてエクスポート
        
        Args:
            alerts: エクスポートするアラートデータ
            file_name: 出力ファイル名（省略時は自動生成）
            
        Returns:
            エクスポート先のファイルパス
        """
        try:
            if file_name is None:
                file_name = f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
            file_path = self.export_dir / file_name
            
            # アラートデータをDataFrameに変換
            if alerts:
                df = pd.DataFrame(alerts)
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    
                df.to_csv(file_path, index=False)
            else:
                # 空のファイルを作成
                with open(file_path, 'w') as f:
                    f.write("timestamp,alert_type,message,severity,value,threshold\n")
                    
            self.logger.info(f"アラート履歴をCSVファイルにエクスポートしました: {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"アラート履歴エクスポートエラー: {e}")
            raise
    
    def export_optimization_history(self, history: Dict[str, Any], file_name: Optional[str] = None) -> str:
        """最適化履歴をCSVファイルとしてエクスポート
        
        Args:
            history: エクスポートする最適化履歴データ
            file_name: 出力ファイル名（省略時は自動生成）
            
        Returns:
            エクスポート先のファイルパス
        """
        try:
            if file_name is None:
                file_name = f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
            file_path = self.export_dir / file_name
            
            # DataFrameに変換
            flattened_data = []
            for timestamp, data in history.items():
                data["timestamp"] = timestamp
                flattened_data.append(data)
                
            df = pd.DataFrame(flattened_data)
            df.to_csv(file_path, index=False)
            
            self.logger.info(f"最適化履歴をCSVファイルにエクスポートしました: {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"最適化履歴エクスポートエラー: {e}")
            raise
    
    def visualize_hardware_metrics(self, metrics_history: List[Dict[str, Any]],
                                  file_name: Optional[str] = None) -> str:
        """ハードウェアメトリクスの視覚化
        
        Args:
            metrics_history: 視覚化するメトリクス履歴
            file_name: 出力ファイル名（省略時は自動生成）
            
        Returns:
            視覚化ファイルのパス
        """
        try:
            if not metrics_history:
                self.logger.warning("視覚化するメトリクスデータがありません")
                return ""
                
            if file_name is None:
                file_name = f"hardware_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                
            file_path = self.visualizations_dir / file_name
            
            # DataFrameに変換
            df = pd.DataFrame(metrics_history)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            
            # プロットの設定
            sns.set_theme(style="darkgrid")
            fig, axes = plt.subplots(3, 1, figsize=(12, 15), sharex=True)
            
            # CPU・GPU温度のプロット
            if 'cpu_temp' in df.columns and 'gpu_temp' in df.columns:
                df[['cpu_temp', 'gpu_temp']].plot(ax=axes[0], marker='o', alpha=0.7)
                axes[0].set_title('CPU・GPU温度')
                axes[0].set_ylabel('温度 (°C)')
                axes[0].grid(True)
            
            # CPU・GPU使用率のプロット
            if 'cpu_usage' in df.columns and 'gpu_usage' in df.columns:
                df[['cpu_usage', 'gpu_usage']].plot(ax=axes[1], marker='o', alpha=0.7)
                axes[1].set_title('CPU・GPU使用率')
                axes[1].set_ylabel('使用率 (%)')
                axes[1].grid(True)
            
            # メモリ使用率のプロット
            if 'memory_usage' in df.columns and 'gpu_memory_usage' in df.columns:
                df[['memory_usage', 'gpu_memory_usage']].plot(ax=axes[2], marker='o', alpha=0.7)
                axes[2].set_title('メモリ使用率')
                axes[2].set_ylabel('使用率 (%)')
                axes[2].grid(True)
                axes[2].set_xlabel('時間')
            
            plt.tight_layout()
            plt.savefig(file_path)
            plt.close(fig)
            
            self.logger.info(f"ハードウェアメトリクスを視覚化しました: {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"メトリクス視覚化エラー: {e}")
            raise
    
    def start_scheduled_export(self, 
                               data_provider: Callable[[], Union[Dict[str, Any], List[Dict[str, Any]]]],
                               interval_seconds: int = 3600,
                               export_format: str = 'json',
                               visualize: bool = True) -> None:
        """定期的なエクスポートを開始
        
        Args:
            data_provider: データを提供する関数
            interval_seconds: エクスポート間隔（秒）
            export_format: エクスポート形式（'json'または'csv'）
            visualize: 視覚化を行うかどうか
        """
        if self._scheduled_export_running:
            self.logger.warning("定期的なエクスポートはすでに実行中です")
            return
            
        self._scheduled_export_running = True
        
        def export_job():
            while self._scheduled_export_running:
                try:
                    # データの取得
                    data = data_provider()
                    
                    # データのエクスポート
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    if export_format == 'json':
                        if isinstance(data, list):
                            self.export_history_to_csv(data, f"scheduled_metrics_{timestamp}.csv")
                        else:
                            self.export_to_json(data, f"scheduled_metrics_{timestamp}.json")
                    else:
                        if isinstance(data, list):
                            self.export_history_to_csv(data, f"scheduled_metrics_{timestamp}.csv")
                        else:
                            self.export_to_csv(data, f"scheduled_metrics_{timestamp}.csv")
                    
                    # 視覚化が有効で、データがリスト形式の場合
                    if visualize and isinstance(data, list):
                        self.visualize_hardware_metrics(data, f"scheduled_visualization_{timestamp}.png")
                        
                except Exception as e:
                    self.logger.error(f"定期的なエクスポート中にエラーが発生しました: {e}")
                
                # 次のエクスポートまで待機
                time.sleep(interval_seconds)
                
        # バックグラウンドスレッドでエクスポートジョブを実行
        self._scheduled_export_thread = threading.Thread(target=export_job, daemon=True)
        self._scheduled_export_thread.start()
        
        self.logger.info(f"定期的なエクスポートを開始しました（間隔: {interval_seconds}秒）")
    
    def stop_scheduled_export(self) -> None:
        """定期的なエクスポートを停止"""
        if not self._scheduled_export_running:
            self.logger.warning("定期的なエクスポートは実行されていません")
            return
            
        self._scheduled_export_running = False
        if self._scheduled_export_thread:
            # スレッドが終了するのを待機（最大5秒）
            self._scheduled_export_thread.join(5.0)
            self._scheduled_export_thread = None
            
        self.logger.info("定期的なエクスポートを停止しました")
    
    # 非同期メソッド
    async def async_export_to_csv(self, metrics: Dict[str, Any], file_name: Optional[str] = None) -> str:
        """非同期でCSVエクスポートを実行"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.export_to_csv, metrics, file_name)
        
    async def async_export_to_json(self, metrics: Dict[str, Any], file_name: Optional[str] = None) -> str:
        """非同期でJSONエクスポートを実行"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.export_to_json, metrics, file_name)
        
    async def async_export_history_to_csv(self, history: List[Dict[str, Any]], file_name: Optional[str] = None) -> str:
        """非同期で履歴CSVエクスポートを実行"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.export_history_to_csv, history, file_name)
        
    async def async_export_alert_history(self, alerts: List[Dict[str, Any]], file_name: Optional[str] = None) -> str:
        """非同期でアラート履歴エクスポートを実行"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.export_alert_history, alerts, file_name)
        
    async def async_export_optimization_history(self, history: Dict[str, Any], file_name: Optional[str] = None) -> str:
        """非同期で最適化履歴エクスポートを実行"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.export_optimization_history, history, file_name)
        
    async def async_visualize_hardware_metrics(self, metrics_history: List[Dict[str, Any]], file_name: Optional[str] = None) -> str:
        """非同期でハードウェアメトリクス視覚化を実行"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.visualize_hardware_metrics, metrics_history, file_name)
    
    def __del__(self):
        """デストラクタ"""
        # 定期的なエクスポートを停止
        if self._scheduled_export_running:
            self.stop_scheduled_export()
            
        # エグゼキューターを終了
        if hasattr(self, 'executor') and self.executor:
            self.executor.shutdown(wait=False) 
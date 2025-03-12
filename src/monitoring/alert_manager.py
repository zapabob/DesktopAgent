import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from dataclasses import dataclass

@dataclass
class AlertConfig:
    """アラート設定"""
    cpu_temp_threshold: float = 80.0
    gpu_temp_threshold: float = 80.0
    memory_usage_threshold: float = 90.0
    error_rate_threshold: float = 0.1
    latency_threshold: float = 1.0
    email_recipients: List[str] = None
    smtp_config: Dict[str, str] = None

@dataclass
class Alert:
    """アラート情報"""
    type: str
    message: str
    severity: str
    timestamp: datetime
    metrics: Dict[str, Any]

class AlertManager:
    """アラート管理クラス"""
    def __init__(self, config: AlertConfig, alert_history_dir: str = "alert_history"):
        self.config = config
        self.history_dir = Path(alert_history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.active_alerts: Dict[str, Alert] = {}
        
    async def check_hardware_metrics(self, metrics: Dict[str, Any]) -> List[Alert]:
        """ハードウェアメトリクスのチェック"""
        alerts = []
        
        # CPU温度チェック
        if metrics["cpu_temperature"] >= self.config.cpu_temp_threshold:
            alert = Alert(
                type="cpu_temperature",
                message=f"CPU温度が閾値を超えています: {metrics['cpu_temperature']}°C",
                severity="critical",
                timestamp=datetime.now(),
                metrics=metrics
            )
            alerts.append(alert)
            
        # GPU温度チェック
        if metrics["gpu_temperature"] >= self.config.gpu_temp_threshold:
            alert = Alert(
                type="gpu_temperature",
                message=f"GPU温度が閾値を超えています: {metrics['gpu_temperature']}°C",
                severity="critical",
                timestamp=datetime.now(),
                metrics=metrics
            )
            alerts.append(alert)
            
        # メモリ使用率チェック
        if metrics["memory_usage"] >= self.config.memory_usage_threshold:
            alert = Alert(
                type="memory_usage",
                message=f"メモリ使用率が閾値を超えています: {metrics['memory_usage']}%",
                severity="warning",
                timestamp=datetime.now(),
                metrics=metrics
            )
            alerts.append(alert)
            
        return alerts
        
    async def check_performance_metrics(self, metrics: Dict[str, Any]) -> List[Alert]:
        """パフォーマンスメトリクスのチェック"""
        alerts = []
        
        # エラー率チェック
        if metrics["error_rate"] >= self.config.error_rate_threshold:
            alert = Alert(
                type="error_rate",
                message=f"エラー率が閾値を超えています: {metrics['error_rate']*100}%",
                severity="critical",
                timestamp=datetime.now(),
                metrics=metrics
            )
            alerts.append(alert)
            
        # レイテンシーチェック
        avg_query_latency = metrics.get("avg_query_latency", 0)
        if avg_query_latency >= self.config.latency_threshold:
            alert = Alert(
                type="high_latency",
                message=f"クエリレイテンシーが閾値を超えています: {avg_query_latency}秒",
                severity="warning",
                timestamp=datetime.now(),
                metrics=metrics
            )
            alerts.append(alert)
            
        return alerts
        
    async def process_alerts(self, alerts: List[Alert]) -> None:
        """アラートの処理"""
        for alert in alerts:
            # アクティブアラートの更新
            alert_key = f"{alert.type}_{alert.severity}"
            self.active_alerts[alert_key] = alert
            
            # アラートの保存
            await self._save_alert(alert)
            
            # 通知の送信
            if self.config.email_recipients:
                await self._send_email_notification(alert)
                
    async def _save_alert(self, alert: Alert) -> None:
        """アラートの保存"""
        try:
            timestamp = alert.timestamp.strftime("%Y%m%d_%H%M%S")
            alert_data = {
                "type": alert.type,
                "message": alert.message,
                "severity": alert.severity,
                "timestamp": alert.timestamp.isoformat(),
                "metrics": alert.metrics
            }
            
            file_path = self.history_dir / f"alert_{timestamp}.json"
            with open(file_path, "w") as f:
                json.dump(alert_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"アラート保存エラー: {e}")
            
    async def _send_email_notification(self, alert: Alert) -> None:
        """メール通知の送信"""
        if not self.config.smtp_config:
            return
            
        try:
            msg = MIMEMultipart()
            msg["Subject"] = f"[{alert.severity.upper()}] {alert.type}"
            msg["From"] = self.config.smtp_config["sender"]
            msg["To"] = ", ".join(self.config.email_recipients)
            
            body = f"""
            アラート通知:
            
            種類: {alert.type}
            重要度: {alert.severity}
            メッセージ: {alert.message}
            発生時刻: {alert.timestamp.isoformat()}
            
            メトリクス:
            {json.dumps(alert.metrics, indent=2)}
            """
            
            msg.attach(MIMEText(body, "plain"))
            
            with smtplib.SMTP(
                self.config.smtp_config["host"],
                self.config.smtp_config["port"]
            ) as server:
                if self.config.smtp_config.get("use_tls"):
                    server.starttls()
                if "username" in self.config.smtp_config:
                    server.login(
                        self.config.smtp_config["username"],
                        self.config.smtp_config["password"]
                    )
                server.send_message(msg)
                
        except Exception as e:
            self.logger.error(f"メール通知送信エラー: {e}")
            
    def get_active_alerts(self) -> List[Alert]:
        """アクティブなアラートの取得"""
        return list(self.active_alerts.values())
        
    async def clear_alert(self, alert_type: str, severity: str) -> None:
        """アラートのクリア"""
        alert_key = f"{alert_type}_{severity}"
        if alert_key in self.active_alerts:
            del self.active_alerts[alert_key]
            
    async def get_alert_history(self,
                             start_time: Optional[datetime] = None,
                             end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """アラート履歴の取得"""
        try:
            alerts = []
            for file_path in self.history_dir.glob("alert_*.json"):
                with open(file_path) as f:
                    alert_data = json.load(f)
                    alert_time = datetime.fromisoformat(alert_data["timestamp"])
                    
                    if start_time and alert_time < start_time:
                        continue
                    if end_time and alert_time > end_time:
                        continue
                        
                    alerts.append(alert_data)
                    
            return sorted(alerts, key=lambda x: x["timestamp"], reverse=True)
            
        except Exception as e:
            self.logger.error(f"アラート履歴取得エラー: {e}")
            return [] 
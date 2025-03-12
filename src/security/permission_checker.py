<<<<<<< HEAD
import sqlite3
import threading
import asyncio
import time
import logging
import psutil
from typing import Dict, Any, Optional, List
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from desktop_agent.agent import BaseChildAgent
from desktop_agent.exceptions import ConfigError, DatabaseError, ValidationError

class NetworkMonitorAgent(BaseChildAgent):
    """統合型ネットワークセキュリティ監視エージェント"""

    def __init__(self, agent_id: str, parent_agent, config: Dict[str, Any]):
        super().__init__(agent_id, parent_agent, config)
        self._validate_config(config)
        
        self.network_history = {}
        self.active_connections = set()
        self.security_thresholds = config['security_thresholds']
        self.db_path = config['security_db_path']
        self.logger = logging.getLogger(f"NetworkMonitor-{agent_id}")
        
        self._initialize_security_database()
        self.llm_chain = self._initialize_langchain(config)
        self.connection_lock = threading.Lock()

    def _validate_config(self, config: Dict[str, Any]):
        """設定のバリデーション"""
        required_keys = ['security_thresholds', 'security_db_path']
        missing = [key for key in required_keys if key not in config]
        
        if missing:
            raise ConfigError(
                "必須設定が不足しています",
                missing_keys=missing
            )
            
        thresholds = config['security_thresholds']
        if not 0.1 <= thresholds.get('traffic_spike', 0) <= 10.0:
            raise ConfigError("無効なトラフィック閾値範囲")

    def _initialize_security_database(self):
        """セキュアなデータベース初期化"""
        try:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS security_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        event_type TEXT NOT NULL,
                        severity TEXT CHECK(severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
                        details TEXT,
                        source_ip TEXT,
                        destination_ip TEXT
                    )
                ''')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON security_events(timestamp)')
                conn.commit()
        except sqlite3.Error as e:
            self.logger.critical(f"データベース初期化失敗: {e}")
            raise DatabaseError("データベース初期化に失敗しました") from e

    def _initialize_langchain(self, config: Dict[str, Any]) -> Optional[LLMChain]:
        """LangChainの安全な初期化"""
        try:
            from langchain.llms import HuggingFaceHub
            model = HuggingFaceHub(
                repo_id=config.get('llm_model', 'google/flan-t5-base'),
                model_kwargs={'temperature':0.5, 'max_length':512}
            )
            return LLMChain(
                llm=model,
                prompt=PromptTemplate.from_template('''
                    ネットワークイベント分析:
                    {events}
                    異常パターンと推奨対策:
                ''')
            )
        except ImportError:
            self.logger.warning("LangChainが利用できません")
            return None
        except Exception as e:
            self.logger.error(f"AIモデル初期化エラー: {e}")
            return None

    async def log_security_event(self, event_data: Dict[str, Any]):
        """セキュアなイベントロギング"""
        required_fields = ['event_type', 'severity', 'details']
        if any(field not in event_data for field in required_fields):
            raise ValidationError("必須フィールドが不足しています")
        
        if len(event_data['details']) > 1000:
            raise ValidationError("詳細フィールドが長すぎます")

        query = '''
            INSERT INTO security_events 
            (timestamp, event_type, severity, details, source_ip, destination_ip)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        params = (
            time.time(),
            event_data['event_type'],
            event_data['severity'],
            event_data['details'],
            event_data.get('source_ip', ''),
            event_data.get('destination_ip', '')
        )

        try:
            with self.connection_lock:
                with sqlite3.connect(self.db_path, timeout=10) as conn:
                    conn.execute(query, params)
                    conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"イベント記録失敗: {e}")
            raise DatabaseError("データベース書き込みエラー") from e

    async def analyze_traffic(self) -> Dict[str, Any]:
        """リアルタイムトラフィック分析"""
        try:
            io_data = await asyncio.get_event_loop().run_in_executor(
                None, psutil.net_io_counters
            )
            analysis = {
                'timestamp': time.time(),
                'bytes_sent': io_data.bytes_sent,
                'bytes_recv': io_data.bytes_recv,
                'packet_loss': io_data.dropin + io_data.dropout,
                'security_alerts': []
            }
            
            if self.llm_chain:
                historical_data = await self._get_historical_data()
                analysis['ai_analysis'] = await self.llm_chain.arun(
                    events=str(historical_data)
                )
            
            return analysis
        except psutil.Error as e:
            self.logger.error(f"ネットワークデータ取得エラー: {e}")
            raise

    async def _get_historical_data(self, hours: int = 24) -> List[Dict]:
        """過去データの安全な取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT * FROM security_events
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                ''', (time.time() - hours * 3600,))
                return [dict(row) for row in cursor]
        except sqlite3.Error as e:
            self.logger.error(f"履歴データ取得失敗: {e}")
            raise DatabaseError("データ取得エラー") from e

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """タスク処理のエントリポイント"""
        try:
            if 'action' not in task:
                raise ValidationError("アクションタイプが指定されていません")
                
            action = task['action']
            
            if action == 'monitor':
                return await self.analyze_traffic()
            elif action == 'log_event':
                return await self.log_security_event(task['data'])
            elif action == 'get_logs':
                return await self._get_historical_data()
            else:
                raise ValidationError("無効なアクションタイプ")
                
        except ValidationError as e:
            self.logger.warning(f"検証エラー: {e}")
            return {'status': 'error', 'message': str(e)}
        except DatabaseError as e:
            self.logger.error(f"データベースエラー: {e}")
            return {'status': 'error', 'message': 'データベース操作に失敗しました'}
        except Exception as e:
            self.logger.critical(f"予期せぬエラー: {e}")
            return {'status': 'error', 'message': '内部エラーが発生しました'}

=======
import sqlite3
import threading
import asyncio
import time
import logging
import psutil
from typing import Dict, Any, Optional, List
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from desktop_agent.agent import BaseChildAgent
from desktop_agent.exceptions import ConfigError, DatabaseError, ValidationError

class NetworkMonitorAgent(BaseChildAgent):
    """統合型ネットワークセキュリティ監視エージェント"""

    def __init__(self, agent_id: str, parent_agent, config: Dict[str, Any]):
        super().__init__(agent_id, parent_agent, config)
        self._validate_config(config)
        
        self.network_history = {}
        self.active_connections = set()
        self.security_thresholds = config['security_thresholds']
        self.db_path = config['security_db_path']
        self.logger = logging.getLogger(f"NetworkMonitor-{agent_id}")
        
        self._initialize_security_database()
        self.llm_chain = self._initialize_langchain(config)
        self.connection_lock = threading.Lock()

    def _validate_config(self, config: Dict[str, Any]):
        """設定のバリデーション"""
        required_keys = ['security_thresholds', 'security_db_path']
        missing = [key for key in required_keys if key not in config]
        
        if missing:
            raise ConfigError(
                "必須設定が不足しています",
                missing_keys=missing
            )
            
        thresholds = config['security_thresholds']
        if not 0.1 <= thresholds.get('traffic_spike', 0) <= 10.0:
            raise ConfigError("無効なトラフィック閾値範囲")

    def _initialize_security_database(self):
        """セキュアなデータベース初期化"""
        try:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS security_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        event_type TEXT NOT NULL,
                        severity TEXT CHECK(severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
                        details TEXT,
                        source_ip TEXT,
                        destination_ip TEXT
                    )
                ''')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON security_events(timestamp)')
                conn.commit()
        except sqlite3.Error as e:
            self.logger.critical(f"データベース初期化失敗: {e}")
            raise DatabaseError("データベース初期化に失敗しました") from e

    def _initialize_langchain(self, config: Dict[str, Any]) -> Optional[LLMChain]:
        """LangChainの安全な初期化"""
        try:
            from langchain.llms import HuggingFaceHub
            model = HuggingFaceHub(
                repo_id=config.get('llm_model', 'google/flan-t5-base'),
                model_kwargs={'temperature':0.5, 'max_length':512}
            )
            return LLMChain(
                llm=model,
                prompt=PromptTemplate.from_template('''
                    ネットワークイベント分析:
                    {events}
                    異常パターンと推奨対策:
                ''')
            )
        except ImportError:
            self.logger.warning("LangChainが利用できません")
            return None
        except Exception as e:
            self.logger.error(f"AIモデル初期化エラー: {e}")
            return None

    async def log_security_event(self, event_data: Dict[str, Any]):
        """セキュアなイベントロギング"""
        required_fields = ['event_type', 'severity', 'details']
        if any(field not in event_data for field in required_fields):
            raise ValidationError("必須フィールドが不足しています")
        
        if len(event_data['details']) > 1000:
            raise ValidationError("詳細フィールドが長すぎます")

        query = '''
            INSERT INTO security_events 
            (timestamp, event_type, severity, details, source_ip, destination_ip)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        params = (
            time.time(),
            event_data['event_type'],
            event_data['severity'],
            event_data['details'],
            event_data.get('source_ip', ''),
            event_data.get('destination_ip', '')
        )

        try:
            with self.connection_lock:
                with sqlite3.connect(self.db_path, timeout=10) as conn:
                    conn.execute(query, params)
                    conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"イベント記録失敗: {e}")
            raise DatabaseError("データベース書き込みエラー") from e

    async def analyze_traffic(self) -> Dict[str, Any]:
        """リアルタイムトラフィック分析"""
        try:
            io_data = await asyncio.get_event_loop().run_in_executor(
                None, psutil.net_io_counters
            )
            analysis = {
                'timestamp': time.time(),
                'bytes_sent': io_data.bytes_sent,
                'bytes_recv': io_data.bytes_recv,
                'packet_loss': io_data.dropin + io_data.dropout,
                'security_alerts': []
            }
            
            if self.llm_chain:
                historical_data = await self._get_historical_data()
                analysis['ai_analysis'] = await self.llm_chain.arun(
                    events=str(historical_data)
                )
            
            return analysis
        except psutil.Error as e:
            self.logger.error(f"ネットワークデータ取得エラー: {e}")
            raise

    async def _get_historical_data(self, hours: int = 24) -> List[Dict]:
        """過去データの安全な取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT * FROM security_events
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                ''', (time.time() - hours * 3600,))
                return [dict(row) for row in cursor]
        except sqlite3.Error as e:
            self.logger.error(f"履歴データ取得失敗: {e}")
            raise DatabaseError("データ取得エラー") from e

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """タスク処理のエントリポイント"""
        try:
            if 'action' not in task:
                raise ValidationError("アクションタイプが指定されていません")
                
            action = task['action']
            
            if action == 'monitor':
                return await self.analyze_traffic()
            elif action == 'log_event':
                return await self.log_security_event(task['data'])
            elif action == 'get_logs':
                return await self._get_historical_data()
            else:
                raise ValidationError("無効なアクションタイプ")
                
        except ValidationError as e:
            self.logger.warning(f"検証エラー: {e}")
            return {'status': 'error', 'message': str(e)}
        except DatabaseError as e:
            self.logger.error(f"データベースエラー: {e}")
            return {'status': 'error', 'message': 'データベース操作に失敗しました'}
        except Exception as e:
            self.logger.critical(f"予期せぬエラー: {e}")
            return {'status': 'error', 'message': '内部エラーが発生しました'}

>>>>>>> 42de7d643d987d98855d441372a3931e7de31809

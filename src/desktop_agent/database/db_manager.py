<<<<<<< HEAD
# -*- coding: utf-8 -*-
"""Database manager module."""

import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path: str = "desktop_agent.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """データベースとテーブルの初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # エージェントログテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    action TEXT,
                    timestamp TEXT,
                    extra_data TEXT
                )
            """)
            
            # 学習データテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS training_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_type TEXT,
                    content TEXT,
                    embedding TEXT,
                    created_at TEXT
                )
            """)
            
            # エージェント間通信テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_communications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id TEXT,
                    receiver_id TEXT,
                    message_type TEXT,
                    content TEXT,
                    timestamp TEXT,
                    status TEXT
                )
            """)
            
            # AIモデルメトリクステーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_model_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT,
                    response_time REAL,
                    success_rate REAL,
                    cost REAL,
                    timestamp TEXT
                )
            """)
            
            conn.commit()
    
    def log_agent_action(self, agent_id: str, action: str, meta_data: Dict[str, Any]):
        """エージェントアクションのログ記録"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO agent_logs (agent_id, action, timestamp, extra_data) VALUES (?, ?, ?, ?)",
                (agent_id, action, datetime.utcnow().isoformat(), json.dumps(meta_data))
            )
            conn.commit()
    
    def save_training_data(self, data_type: str, content: Dict[str, Any], embedding: List[float]):
        """学習データの保存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO training_data (data_type, content, embedding, created_at) VALUES (?, ?, ?, ?)",
                (data_type, json.dumps(content), json.dumps(embedding), datetime.utcnow().isoformat())
            )
            conn.commit()
    
    def save_communication(self, sender_id: str, receiver_id: str, 
                         message_type: str, content: Dict[str, Any]):
        """エージェント間通信の保存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO agent_communications 
                   (sender_id, receiver_id, message_type, content, timestamp, status) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (sender_id, receiver_id, message_type, json.dumps(content),
                 datetime.utcnow().isoformat(), 'pending')
            )
            conn.commit()
    
    def save_model_metrics(self, model_name: str, response_time: float,
                         success_rate: float, cost: float):
        """AIモデルメトリクスの保存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO ai_model_metrics 
                   (model_name, response_time, success_rate, cost, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (model_name, response_time, success_rate, cost,
                 datetime.utcnow().isoformat())
            )
            conn.commit()
    
    def get_training_data(self, data_type: str = None) -> List[Dict[str, Any]]:
        """学習データの取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if data_type:
                cursor.execute(
                    "SELECT * FROM training_data WHERE data_type = ?",
                    (data_type,)
                )
            else:
                cursor.execute("SELECT * FROM training_data")
            
            columns = [description[0] for description in cursor.description]
            results = []
            for row in cursor.fetchall():
                data = dict(zip(columns, row))
                data['content'] = json.loads(data['content'])
                data['embedding'] = json.loads(data['embedding'])
                results.append(data)
            
            return results
    
    def get_pending_communications(self, receiver_id: str) -> List[Dict[str, Any]]:
        """保留中の通信の取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM agent_communications 
                   WHERE receiver_id = ? AND status = 'pending'""",
                (receiver_id,)
            )
            
            columns = [description[0] for description in cursor.description]
            results = []
            for row in cursor.fetchall():
                data = dict(zip(columns, row))
                data['content'] = json.loads(data['content'])
                results.append(data)
            
            return results
    
    def update_communication_status(self, message_id: int, status: str):
        """通信ステータスの更新"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE agent_communications SET status = ? WHERE id = ?",
                (status, message_id)
            )
=======
# -*- coding: utf-8 -*-
"""Database manager module."""

import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path: str = "desktop_agent.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """データベースとテーブルの初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # エージェントログテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    action TEXT,
                    timestamp TEXT,
                    extra_data TEXT
                )
            """)
            
            # 学習データテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS training_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_type TEXT,
                    content TEXT,
                    embedding TEXT,
                    created_at TEXT
                )
            """)
            
            # エージェント間通信テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_communications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id TEXT,
                    receiver_id TEXT,
                    message_type TEXT,
                    content TEXT,
                    timestamp TEXT,
                    status TEXT
                )
            """)
            
            # AIモデルメトリクステーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_model_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT,
                    response_time REAL,
                    success_rate REAL,
                    cost REAL,
                    timestamp TEXT
                )
            """)
            
            conn.commit()
    
    def log_agent_action(self, agent_id: str, action: str, meta_data: Dict[str, Any]):
        """エージェントアクションのログ記録"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO agent_logs (agent_id, action, timestamp, extra_data) VALUES (?, ?, ?, ?)",
                (agent_id, action, datetime.utcnow().isoformat(), json.dumps(meta_data))
            )
            conn.commit()
    
    def save_training_data(self, data_type: str, content: Dict[str, Any], embedding: List[float]):
        """学習データの保存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO training_data (data_type, content, embedding, created_at) VALUES (?, ?, ?, ?)",
                (data_type, json.dumps(content), json.dumps(embedding), datetime.utcnow().isoformat())
            )
            conn.commit()
    
    def save_communication(self, sender_id: str, receiver_id: str, 
                         message_type: str, content: Dict[str, Any]):
        """エージェント間通信の保存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO agent_communications 
                   (sender_id, receiver_id, message_type, content, timestamp, status) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (sender_id, receiver_id, message_type, json.dumps(content),
                 datetime.utcnow().isoformat(), 'pending')
            )
            conn.commit()
    
    def save_model_metrics(self, model_name: str, response_time: float,
                         success_rate: float, cost: float):
        """AIモデルメトリクスの保存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO ai_model_metrics 
                   (model_name, response_time, success_rate, cost, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (model_name, response_time, success_rate, cost,
                 datetime.utcnow().isoformat())
            )
            conn.commit()
    
    def get_training_data(self, data_type: str = None) -> List[Dict[str, Any]]:
        """学習データの取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if data_type:
                cursor.execute(
                    "SELECT * FROM training_data WHERE data_type = ?",
                    (data_type,)
                )
            else:
                cursor.execute("SELECT * FROM training_data")
            
            columns = [description[0] for description in cursor.description]
            results = []
            for row in cursor.fetchall():
                data = dict(zip(columns, row))
                data['content'] = json.loads(data['content'])
                data['embedding'] = json.loads(data['embedding'])
                results.append(data)
            
            return results
    
    def get_pending_communications(self, receiver_id: str) -> List[Dict[str, Any]]:
        """保留中の通信の取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM agent_communications 
                   WHERE receiver_id = ? AND status = 'pending'""",
                (receiver_id,)
            )
            
            columns = [description[0] for description in cursor.description]
            results = []
            for row in cursor.fetchall():
                data = dict(zip(columns, row))
                data['content'] = json.loads(data['content'])
                results.append(data)
            
            return results
    
    def update_communication_status(self, message_id: int, status: str):
        """通信ステータスの更新"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE agent_communications SET status = ? WHERE id = ?",
                (status, message_id)
            )
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
            conn.commit() 
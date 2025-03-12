<<<<<<< HEAD
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

class OperationAnalyzer:
    def __init__(self, db_path):
        self.db_path = db_path
        
    def get_connection(self):
        return sqlite3.connect(str(self.db_path))
    
    def analyze_operation_history(self, days=7):
        """直近の操作履歴を分析"""
        conn = self.get_connection()
        try:
            query = '''
            SELECT 
                date(timestamp) as date,
                operation_type,
                count(*) as count,
                sum(case when status = 'SUCCESS' then 1 else 0 end) as success_count,
                sum(case when status = 'FAILURE' then 1 else 0 end) as failure_count
            FROM operation_history
            WHERE timestamp >= date('now', ?)
            GROUP BY date(timestamp), operation_type
            ORDER BY date(timestamp) DESC
            '''
            
            return pd.read_sql_query(query, conn, params=(f'-{days} days',))
        finally:
            conn.close()
    
    def analyze_system_performance(self, hours=24):
        """システムパフォーマンスの分析"""
        conn = self.get_connection()
        try:
            query = '''
            SELECT 
                strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                avg(cpu_usage) as avg_cpu,
                avg(memory_usage) as avg_memory,
                count(distinct active_window) as unique_windows
            FROM system_state
            WHERE timestamp >= datetime('now', ?)
            GROUP BY strftime('%Y-%m-%d %H:00:00', timestamp)
            ORDER BY hour DESC
            '''
            
            return pd.read_sql_query(query, conn, params=(f'-{hours} hours',))
        finally:
=======
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

class OperationAnalyzer:
    def __init__(self, db_path):
        self.db_path = db_path
        
    def get_connection(self):
        return sqlite3.connect(str(self.db_path))
    
    def analyze_operation_history(self, days=7):
        """直近の操作履歴を分析"""
        conn = self.get_connection()
        try:
            query = '''
            SELECT 
                date(timestamp) as date,
                operation_type,
                count(*) as count,
                sum(case when status = 'SUCCESS' then 1 else 0 end) as success_count,
                sum(case when status = 'FAILURE' then 1 else 0 end) as failure_count
            FROM operation_history
            WHERE timestamp >= date('now', ?)
            GROUP BY date(timestamp), operation_type
            ORDER BY date(timestamp) DESC
            '''
            
            return pd.read_sql_query(query, conn, params=(f'-{days} days',))
        finally:
            conn.close()
    
    def analyze_system_performance(self, hours=24):
        """システムパフォーマンスの分析"""
        conn = self.get_connection()
        try:
            query = '''
            SELECT 
                strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                avg(cpu_usage) as avg_cpu,
                avg(memory_usage) as avg_memory,
                count(distinct active_window) as unique_windows
            FROM system_state
            WHERE timestamp >= datetime('now', ?)
            GROUP BY strftime('%Y-%m-%d %H:00:00', timestamp)
            ORDER BY hour DESC
            '''
            
            return pd.read_sql_query(query, conn, params=(f'-{hours} hours',))
        finally:
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
            conn.close() 
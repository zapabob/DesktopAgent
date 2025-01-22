import os
import json
import time
import requests
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
from datetime import datetime
import urllib.parse
import re
from llm_service import LLMServiceFactory
from config import Config
import logging
from pathlib import Path
from ai_orchestration.core.desktop_controller import DesktopController
from ai_orchestration.core.edge_controller import EdgeController
from ai_orchestration.core.llm_service import LLMService

class AutonomousAgent:
    """自律型AIエージェント"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.desktop = DesktopController()
        self.browser = EdgeController()
        self.llm = LLMService()
        
        # 状態管理
        self.is_active = False
        self.current_task = None
        self.task_history = []
        
        # メトリクスの初期化
        self.metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_execution_time": 0.0,
            "average_response_time": 0.0
        }
        
        self.history_path = Config.get_history_path()
        self.max_history_size = Config.MAX_HISTORY_SIZE
        self.debug = Config.DEBUG_MODE
        self.load_history()
        
    def load_history(self):
        """実行履歴を読み込み"""
        if os.path.exists(self.history_path):
            with open(self.history_path, 'r', encoding='utf-8') as f:
                self.history = json.load(f)
                # 履歴サイズの制限
                if len(self.history) > self.max_history_size:
                    self.history = self.history[-self.max_history_size:]
        else:
            self.history = []
            
    def save_history(self):
        """実行履歴を保存"""
        # 履歴サイズの制限
        if len(self.history) > self.max_history_size:
            self.history = self.history[-self.max_history_size:]
            
        with open(self.history_path, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
            
    def add_to_history(self, task: str, action: str, result: str):
        """履歴に追加"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'task': task,
            'action': action,
            'result': result
        }
        
        if self.debug:
            print(f"履歴に追加:\n{json.dumps(entry, ensure_ascii=False, indent=2)}\n")
            
        self.history.append(entry)
        self.save_history()

    def create_file(self, file_path: str, content: str) -> bool:
        """ファイルを作成"""
        try:
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
                
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            self.add_to_history("create_file", file_path, f"エラー: {str(e)}")
            return False
            
    def read_file(self, file_path: str) -> Optional[str]:
        """ファイルを読み込み"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.add_to_history("read_file", file_path, f"エラー: {str(e)}")
            return None
            
    def search_web(self, query: str, num_results: int = 5) -> List[Dict]:
        """Web検索を実行"""
        try:
            # Google Custom Search APIを使用
            search_url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': os.getenv('GOOGLE_API_KEY'),
                'cx': os.getenv('GOOGLE_CSE_ID'),
                'q': query,
                'num': num_results
            }
            
            response = requests.get(search_url, params=params)
            results = response.json()
            
            search_results = []
            for item in results.get('items', []):
                search_results.append({
                    'title': item.get('title'),
                    'link': item.get('link'),
                    'snippet': item.get('snippet')
                })
                
            self.add_to_history("search_web", query, f"結果: {len(search_results)}件")
            return search_results
        except Exception as e:
            self.add_to_history("search_web", query, f"エラー: {str(e)}")
            return []
            
    def scrape_webpage(self, url: str) -> Optional[Dict]:
        """Webページをスクレイピング"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # メタデータの抽出
            title = soup.title.string if soup.title else ''
            description = soup.find('meta', {'name': 'description'})
            description = description['content'] if description else ''
            
            # 本文の抽出
            content = ' '.join([p.text for p in soup.find_all('p')])
            
            result = {
                'url': url,
                'title': title,
                'description': description,
                'content': content
            }
            
            self.add_to_history("scrape_webpage", url, "成功")
            return result
        except Exception as e:
            self.add_to_history("scrape_webpage", url, f"エラー: {str(e)}")
            return None
            
    def start(self):
        """エージェントを起動"""
        try:
            self.logger.info("エージェントを起動します")
            self.desktop.start()
            self.browser.initialize()
            self.is_active = True
            return True
        except Exception as e:
            self.logger.error(f"起動エラー: {e}")
            return False
            
    def stop(self):
        """エージェントを停止"""
        try:
            self.logger.info("エージェントを停止します")
            self.desktop.stop()
            self.browser.cleanup()
            self.is_active = False
            return True
        except Exception as e:
            self.logger.error(f"停止エラー: {e}")
            return False
            
    def execute_task(self, task: Dict[str, Any]) -> bool:
        """タスクを実行"""
        if not self.is_active:
            self.logger.error("エージェントが起動していません")
            return False
            
        try:
            self.current_task = task
            task_type = task.get("type")
            
            if task_type == "browser_search":
                return self._execute_browser_search(task)
            elif task_type == "desktop_action":
                return self._execute_desktop_action(task)
            elif task_type == "code_assistance":
                return self._execute_code_assistance(task)
            else:
                self.logger.error(f"未知のタスクタイプ: {task_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"タスク実行エラー: {e}")
            return False
        finally:
            self.task_history.append(self.current_task)
            self.current_task = None
            
    def _execute_browser_search(self, task: Dict[str, Any]) -> bool:
        """ブラウザ検索タスクを実行"""
        query = task.get("query")
        site = task.get("site")
        
        results = self.browser.search_documentation(query, site)
        task["results"] = results
        return bool(results)
        
    def _execute_desktop_action(self, task: Dict[str, Any]) -> bool:
        """デスクトップ操作タスクを実行"""
        action = task.get("action")
        params = task.get("params", {})
        
        if action == "move_mouse":
            return self.desktop.move_mouse(**params)
        elif action == "type_text":
            return self.desktop.type_text(**params)
        elif action == "press_key":
            return self.desktop.press_key(**params)
        elif action == "take_screenshot":
            return bool(self.desktop.take_screenshot(**params))
        else:
            self.logger.error(f"未知のデスクトップアクション: {action}")
            return False
            
    def _execute_code_assistance(self, task: Dict[str, Any]) -> bool:
        """コード支援タスクを実行"""
        assistance_type = task.get("assistance_type")
        
        if assistance_type == "review":
            return self.desktop.request_code_review(task.get("file_path"))
        elif assistance_type == "completion":
            return self.desktop.assist_coding(task.get("code_context"))
        else:
            self.logger.error(f"未知のコード支援タイプ: {assistance_type}")
            return False
    
    def _update_metrics(self, success: bool, execution_time: float):
        """メトリクスの更新"""
        if success:
            self.metrics["tasks_completed"] += 1
        else:
            self.metrics["tasks_failed"] += 1
        
        self.metrics["total_execution_time"] += execution_time
        total_tasks = self.metrics["tasks_completed"] + self.metrics["tasks_failed"]
        
        if total_tasks > 0:
            self.metrics["average_response_time"] = (
                self.metrics["total_execution_time"] / total_tasks
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """メトリクスの取得"""
        return self.metrics.copy()
    
    def save_state(self, file_path: str) -> bool:
        """状態の保存"""
        try:
            state = {
                "is_active": self.is_active,
                "metrics": self.metrics,
                "task_history": self.task_history
            }
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"状態の保存に失敗: {e}")
            return False
    
    def load_state(self, file_path: str) -> bool:
        """状態の読み込み"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            
            self.is_active = state["is_active"]
            self.metrics = state["metrics"]
            self.task_history = state["task_history"]
            
            return True
            
        except Exception as e:
            self.logger.error(f"状態の読み込みに失敗: {e}")
            return False

    def suggest_improvements(self) -> List[str]:
        """改善案を提案"""
        return self.llm.suggest_improvements(self.history) 
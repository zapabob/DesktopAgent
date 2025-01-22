from typing import Optional, List, Dict, Any
import logging
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import json
import time
import re

class EdgeController:
    """Edgeブラウザを制御するクラス"""
    
    def __init__(self):
        self.logger = logging.getLogger("EdgeController")
        self._setup_logging()
        
        self.driver = None
        self.wait_timeout = 10
        self.search_history = []
        self.code_snippets = []
        
    def _setup_logging(self):
        """ロギングの設定"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        fh = logging.FileHandler(
            log_dir / f"edge_{datetime.now().strftime('%Y%m%d')}.log",
            encoding='utf-8'
        )
        fh.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.setLevel(logging.DEBUG)
    
    def initialize(self):
        """ブラウザを初期化"""
        try:
            options = Options()
            options.add_argument("--headless")  # ヘッドレスモード
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            self.driver = webdriver.Edge(options=options)
            self.driver.implicitly_wait(self.wait_timeout)
            self.logger.info("ブラウザを初期化しました")
            return True
        except Exception as e:
            self.logger.error(f"ブラウザの初期化に失敗: {e}")
            return False
    
    def cleanup(self):
        """ブラウザをクリーンアップ"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("ブラウザをクリーンアップしました")
            except Exception as e:
                self.logger.error(f"ブラウザのクリーンアップに失敗: {e}")
    
    def navigate(self, url: str) -> bool:
        """指定URLに移動"""
        try:
            self.driver.get(url)
            self.logger.info(f"ページに移動: {url}")
            return True
        except Exception as e:
            self.logger.error(f"ページ移動に失敗: {e}")
            return False
    
    def search_documentation(self, query: str, site: str = None) -> List[Dict]:
        """ドキュメントを検索"""
        try:
            # 検索URLの構築
            if site:
                search_url = f"https://www.google.com/search?q=site:{site}+{query}"
            else:
                search_url = f"https://www.google.com/search?q={query}+documentation"
            
            self.navigate(search_url)
            
            # 検索結果を取得
            results = []
            elements = self.driver.find_elements(By.CSS_SELECTOR, "div.g")
            
            for element in elements[:5]:  # 上位5件を取得
                try:
                    title = element.find_element(By.CSS_SELECTOR, "h3").text
                    link = element.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                    snippet = element.find_element(By.CSS_SELECTOR, "div.VwiC3b").text
                    
                    results.append({
                        "title": title,
                        "url": link,
                        "snippet": snippet
                    })
                except Exception:
                    continue
            
            # 検索履歴を更新
            self.search_history.append({
                "query": query,
                "site": site,
                "timestamp": datetime.now().isoformat(),
                "results": results
            })
            
            return results
        
        except Exception as e:
            self.logger.error(f"ドキュメント検索に失敗: {e}")
            return []
    
    def extract_code_snippets(self, url: str) -> List[Dict]:
        """コードスニペットを抽出"""
        try:
            self.navigate(url)
            
            # コードブロックを探す
            code_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                "pre, code, .highlight"
            )
            
            snippets = []
            for element in code_elements:
                code = element.text.strip()
                if code:
                    # 言語を推定
                    lang = self._detect_language(code)
                    
                    snippets.append({
                        "code": code,
                        "language": lang,
                        "source_url": url,
                        "timestamp": datetime.now().isoformat()
                    })
            
            # スニペット履歴を更新
            self.code_snippets.extend(snippets)
            
            return snippets
        
        except Exception as e:
            self.logger.error(f"コードスニペットの抽出に失敗: {e}")
            return []
    
    def _detect_language(self, code: str) -> str:
        """コードの言語を推定"""
        # 簡易的な言語判定
        if re.search(r"import\s+[a-zA-Z_][a-zA-Z0-9_]*(\s*,\s*[a-zA-Z_][a-zA-Z0-9_]*)*", code):
            return "python"
        elif re.search(r"function\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\(", code):
            return "javascript"
        elif re.search(r"public\s+class\s+[a-zA-Z_][a-zA-Z0-9_]*", code):
            return "java"
        else:
            return "unknown"
    
    def search_api_reference(self, package: str, function: str = None) -> Dict:
        """APIリファレンスを検索"""
        try:
            # パッケージのドキュメントサイトを特定
            doc_sites = {
                "numpy": "numpy.org",
                "pandas": "pandas.pydata.org",
                "tensorflow": "tensorflow.org",
                "pytorch": "pytorch.org",
                "selenium": "selenium.dev"
            }
            
            site = doc_sites.get(package.lower())
            if not site:
                return {}
            
            # 検索クエリを構築
            query = package
            if function:
                query += f" {function} API reference"
            
            results = self.search_documentation(query, site)
            if results:
                # 最も関連性の高い結果を返す
                return results[0]
            
            return {}
            
        except Exception as e:
            self.logger.error(f"APIリファレンス検索に失敗: {e}")
            return {}
    
    def get_search_history(self) -> List[Dict]:
        """検索履歴を取得"""
        return self.search_history
    
    def get_code_snippets(self, language: str = None) -> List[Dict]:
        """コードスニペットを取得"""
        if language:
            return [s for s in self.code_snippets if s["language"] == language]
        return self.code_snippets
    
    def clear_history(self):
        """履歴をクリア"""
        self.search_history.clear()
        self.code_snippets.clear()
        self.logger.info("履歴をクリアしました") 
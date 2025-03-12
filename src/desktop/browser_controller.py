"""
ブラウザ操作を制御するモジュール。
複数のブラウザを起動し、操作するための機能を提供します。
"""

import os
import subprocess
import logging
import yaml
import webbrowser
import urllib.parse
import time
from pathlib import Path
from typing import Dict, Optional, List, Union

logger = logging.getLogger(__name__)

class BrowserController:
    """ブラウザの起動と操作を担当するクラス"""
    
    def __init__(self, config_path: str = None):
        """
        ブラウザコントローラの初期化
        
        Args:
            config_path: 設定ファイルのパス。指定がない場合はデフォルトを使用
        """
        self.browsers = {}
        self.default_browser = None
        self.config_path = config_path or Path(__file__).resolve().parents[2] / 'config.yaml'
        self.load_browser_config()
        logger.info("ブラウザコントローラが初期化されました")
    
    def load_browser_config(self) -> None:
        """設定ファイルからブラウザ情報を読み込む"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if 'browser_paths' in config:
                self.browsers = config['browser_paths']
                # デフォルトブラウザを設定（最初のブラウザ）
                if self.browsers:
                    self.default_browser = list(self.browsers.keys())[0]
                    logger.info(f"デフォルトブラウザを設定しました: {self.default_browser}")
            else:
                logger.warning("設定ファイルにブラウザの設定がありません")
        except Exception as e:
            logger.error(f"ブラウザ設定の読み込みに失敗しました: {str(e)}")
    
    def open_browser(self, url: str, browser_name: str = None) -> bool:
        """
        指定されたURLをブラウザで開く
        
        Args:
            url: 開くURL
            browser_name: 使用するブラウザ名。指定がない場合はデフォルトブラウザを使用
            
        Returns:
            bool: 成功したかどうか
        """
        # ブラウザが指定されていない場合はデフォルトを使用
        browser_to_use = browser_name or self.default_browser
        
        if not browser_to_use or browser_to_use not in self.browsers:
            logger.warning(f"指定されたブラウザ '{browser_to_use}' は設定されていません。システムのデフォルトブラウザを使用します。")
            try:
                webbrowser.open(url)
                logger.info(f"システムのデフォルトブラウザでURLを開きました: {url}")
                return True
            except Exception as e:
                logger.error(f"デフォルトブラウザでURLを開けませんでした: {str(e)}")
                return False
        
        # 設定されたブラウザのパスを使用
        browser_path = self.browsers[browser_to_use]
        if not os.path.exists(browser_path):
            logger.error(f"ブラウザが見つかりません: {browser_path}")
            return False
        
        try:
            subprocess.Popen([browser_path, url])
            logger.info(f"ブラウザ '{browser_to_use}' でURLを開きました: {url}")
            return True
        except Exception as e:
            logger.error(f"ブラウザでURLを開けませんでした: {str(e)}")
            return False
    
    def search_on_youtube(self, query: str, browser_name: str = None) -> bool:
        """
        YouTubeで検索を実行
        
        Args:
            query: 検索クエリ
            browser_name: 使用するブラウザ名
            
        Returns:
            bool: 成功したかどうか
        """
        encoded_query = urllib.parse.quote(query)
        youtube_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        logger.info(f"YouTubeで検索します: '{query}'")
        return self.open_browser(youtube_url, browser_name)
    
    def search_on_google(self, query: str, browser_name: str = None) -> bool:
        """
        Googleで検索を実行
        
        Args:
            query: 検索クエリ
            browser_name: 使用するブラウザ名
            
        Returns:
            bool: 成功したかどうか
        """
        encoded_query = urllib.parse.quote(query)
        google_url = f"https://www.google.com/search?q={encoded_query}"
        logger.info(f"Googleで検索します: '{query}'")
        return self.open_browser(google_url, browser_name)
    
    def open_gmail(self, browser_name: str = None) -> bool:
        """
        Gmailを開く
        
        Args:
            browser_name: 使用するブラウザ名
            
        Returns:
            bool: 成功したかどうか
        """
        return self.open_browser("https://mail.google.com", browser_name)
    
    def open_calendar(self, browser_name: str = None) -> bool:
        """
        Googleカレンダーを開く
        
        Args:
            browser_name: 使用するブラウザ名
            
        Returns:
            bool: 成功したかどうか
        """
        return self.open_browser("https://calendar.google.com", browser_name)
    
    def play_youtube_video(self, video_query: str, browser_name: str = None) -> bool:
        """
        YouTubeで動画を検索して再生
        より正確には検索結果ページを開く
        
        Args:
            video_query: 動画のクエリ
            browser_name: 使用するブラウザ名
            
        Returns:
            bool: 成功したかどうか
        """
        return self.search_on_youtube(video_query, browser_name)
    
    def get_available_browsers(self) -> List[str]:
        """
        利用可能なブラウザのリストを取得
        
        Returns:
            List[str]: ブラウザのリスト
        """
        return list(self.browsers.keys())
    
    def set_default_browser(self, browser_name: str) -> bool:
        """
        デフォルトブラウザを設定
        
        Args:
            browser_name: ブラウザ名
            
        Returns:
            bool: 成功したかどうか
        """
        if browser_name in self.browsers:
            self.default_browser = browser_name
            logger.info(f"デフォルトブラウザを設定しました: {browser_name}")
            return True
        else:
            logger.warning(f"指定されたブラウザ '{browser_name}' は設定されていません")
            return False 
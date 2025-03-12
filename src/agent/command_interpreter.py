import re
from typing import Dict, Any, Tuple, Optional, List
import logging
import pyautogui
import keyboard
import time
import cv2 
import subprocess
import threading
import os
import asyncio
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from langchain_core.language_models.base import BaseLanguageModel
from dotenv import load_dotenv
from langchain_openai import OpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

# 好みのLLMをインポート

# 環境変数の読み込み
load_dotenv()

# browser_useのインポートを試行
try:
    from browser_use import Browser
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    logging.getLogger(__name__).warning("browser_useパッケージがインポートできません。一部の機能が制限されます。")

from .keyboard_monitor import KeyboardMonitor
from src.desktop.browser_controller import BrowserController

class CommandInterpreter:
    def __init__(self, llm: Optional[BaseLanguageModel] = None):
        self.logger = logging.getLogger(__name__)
        self.keyboard_monitor = KeyboardMonitor()
        self.command_buffer = []
        self.is_recording = False
        
        # 従来のブラウザコントローラー（後方互換性用）
        self.browser_controller = BrowserController()
        
        # 新しいbrowser_useのブラウザインスタンス
        self.browser = None
        self.browser_loop = None
        self.agent_executor = None
        
        # もしLLMが提供されていれば、langchainエージェントを初期化
        if llm is not None:
            self.setup_langchain_agent(llm)
        
        # コマンドパターンを定義
        self.command_patterns = [
            # ブラウザ関連コマンド
            (r'(ブラウザ|browser)(\s*で|\s*を)?(.+)(を)?(開く|開いて|見る|表示)', self._open_browser),
            (r'(youtube|ユーチューブ)(\s*で|\s*を)?(.+)(を)?(検索|見る|開く|再生)', self._search_youtube),
            (r'(youtube|ユーチューブ)(を)?(開く|開いて|見る|表示)', self._open_youtube),
            (r'(google|グーグル)(\s*で|\s*を)?(.+)(を)?(検索|調べる)', self._search_google),
            (r'(gmail|メール)(を)?(開く|開いて|見る|表示)', self._open_gmail),
            (r'(カレンダー|calendar)(を)?(開く|開いて|見る|表示)', self._open_calendar),
            
            # 高度なブラウザ操作コマンド
            (r'(ブラウザ|browser)(を|で)?要素(.+)(を)?(クリック|押す|タップ)', self._click_element),
            (r'(ブラウザ|browser)(を|で)?スクリーンショット(を)?(撮る|撮影|取る)', self._take_screenshot),
            (r'(llm|LLM|AI)(に|で|を使って)(ブラウザ|browser)(を)?(操作|コントロール)', self._control_with_llm),
            
            # システム関連コマンド
            (r'(音量|ボリューム)(を)?(上げる|アップ|大きく)', self._volume_up),
            (r'(音量|ボリューム)(を)?(下げる|ダウン|小さく)', self._volume_down),
            (r'(音|サウンド)(を)?(ミュート|消す)', self._mute),
        ]

    def setup_langchain_agent(self, llm: BaseLanguageModel):
        """
        LangChainのAgentを設定する
        
        Args:
            llm: 使用するLLM（OpenAI, Anthropic, など）
        """
        if not BROWSER_USE_AVAILABLE:
            self.logger.error("browser_useが利用できないため、LangChainエージェントは初期化できません")
            return False
            
        # ブラウザの初期化
        self.initialize_browser()
        if self.browser is None:
            self.logger.error("ブラウザの初期化に失敗したため、LangChainエージェントは初期化できません")
            return False
            
        # ブラウザ操作ツールの作成
        tools = [
            Tool(
                name="Navigate",
                func=self._tool_navigate,
                description="Webサイトを開きます。URLを入力してください。"
            ),
            Tool(
                name="Click",
                func=self._tool_click,
                description="ページ上の要素をクリックします。セレクタやテキストを入力してください。"
            ),
            Tool(
                name="Type",
                func=self._tool_type,
                description="テキストを入力します。セレクタと入力するテキストを指定してください。書式: 'セレクタ:::テキスト'"
            ),
            Tool(
                name="Screenshot",
                func=self._tool_screenshot,
                description="現在のページのスクリーンショットを撮影します。"
            ),
            Tool(
                name="GetText",
                func=self._tool_get_text,
                description="ページから要素のテキストを取得します。セレクタを入力してください。"
            ),
            Tool(
                name="ExecuteJS",
                func=self._tool_execute_js,
                description="JavaScriptコードを実行します。実行するコードを入力してください。"
            )
        ]
        
        # プロンプトテンプレートの作成
        prompt = PromptTemplate.from_template(
            """あなたはブラウザを操作するAIアシスタントです。
            与えられたタスクをブラウザの操作で完了させてください。
            
            以下のツールが利用可能です:
            {tools}
            
            タスク: {input}
            
            必要に応じてツールを使用し、タスクを完了させてください。
            ユーザーが理解できるように、各ステップで何をしているかを日本語で説明してください。
            
            {agent_scratchpad}
            """
        )
        
        # エージェントの作成
        agent = create_react_agent(llm, tools, prompt)
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=agent, 
            tools=tools, 
            verbose=True,
            handle_parsing_errors=True
        )
        
        self.logger.info("LangChainエージェントを初期化しました")
        return True
        
    # LangChain用のツール関数
    def _tool_navigate(self, url: str) -> str:
        """URLに移動するツール"""
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
            
        success = self._run_browser_async(self.browser.navigate(url))
        if success:
            return f"成功: {url} に移動しました"
        return f"失敗: {url} に移動できませんでした"
        
    def _tool_click(self, selector: str) -> str:
        """要素をクリックするツール"""
        # セレクタの前処理
        if not selector.startswith(('#', '.', '[', '/')):
            # 単純なテキストの場合は、テキストを含む要素を探す
            selector = f"//*[contains(text(), '{selector}')]"
            
        success = self._run_browser_async(self.browser.click(selector))
        if success:
            return f"成功: '{selector}' をクリックしました"
        return f"失敗: '{selector}' をクリックできませんでした"
        
    def _tool_type(self, selector_and_text: str) -> str:
        """テキストを入力するツール"""
        try:
            selector, text = selector_and_text.split(":::", 1)
            selector = selector.strip()
            text = text.strip()
            
            # セレクタの前処理
            if not selector.startswith(('#', '.', '[', '/')):
                selector = f"//*[contains(text(), '{selector}')]"
                
            success = self._run_browser_async(self.browser.type(selector, text))
            if success:
                return f"成功: '{selector}' に '{text}' を入力しました"
            return f"失敗: '{selector}' にテキストを入力できませんでした"
        except ValueError:
            return "エラー: 入力形式が不正です。'セレクタ:::テキスト' の形式で入力してください"
            
    def _tool_screenshot(self) -> str:
        """スクリーンショットを撮るツール"""
        now = time.strftime("%Y%m%d_%H%M%S")
        screenshot_dir = os.path.join(os.path.expanduser("~"), "Documents", "DesktopAgent", "Screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        screenshot_path = os.path.join(screenshot_dir, f"screenshot_{now}.png")
        
        success = self._run_browser_async(self.browser.screenshot(screenshot_path))
        if success:
            return f"成功: スクリーンショットを '{screenshot_path}' に保存しました"
        return "失敗: スクリーンショットを撮影できませんでした"
        
    def _tool_get_text(self, selector: str) -> str:
        """要素のテキストを取得するツール"""
        # セレクタの前処理
        if not selector.startswith(('#', '.', '[', '/')):
            selector = f"//*[contains(text(), '{selector}')]"
            
        result = self._run_browser_async(self.browser.get_text(selector))
        if result:
            return f"取得したテキスト: {result}"
        return f"失敗: '{selector}' からテキストを取得できませんでした"
    
    def _tool_execute_js(self, code: str) -> str:
        """JavaScriptを実行するツール"""
        result = self._run_browser_async(self.browser.evaluate(code))
        return f"JavaScriptの実行結果: {result}"
        
    def _control_with_llm(self, match, command_text: str) -> Tuple[bool, str]:
        """LLMを使ってブラウザを操作するコマンドを処理"""
        if self.agent_executor is None:
            return False, "LLMエージェントが初期化されていません。先にLLMを設定してください。"
            
        # ユーザー入力を取得するためのプロンプト
        user_input = input("ブラウザで何をしますか？ > ")
        
        try:
            # LLMエージェントにタスクを実行させる
            result = self.agent_executor.invoke({"input": user_input})
            output = result.get("output", "タスクを完了しました")
            return True, f"LLMによるブラウザ操作の結果: {output}"
        except Exception as e:
            self.logger.error(f"LLMブラウザ操作エラー: {e}")
            return False, f"LLMによるブラウザ操作中にエラーが発生しました: {str(e)}"

    def interpret(self, command: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        コマンドを解釈して、コマンドタイプとパラメータを返す
        
        Args:
            command (str): 解釈するコマンド文字列
            
        Returns:
            Optional[Tuple[str, Dict[str, Any]]]: コマンドタイプとパラメータのタプル、
            または解釈できない場合はNone
        """
        for pattern, handler in self.command_patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                try:
                    if hasattr(handler, '__code__') and handler.__code__.co_argcount == 2:
                        # 引数が2つ(self, match)のパターン
                        return handler(match)
                    else:
                        # 引数が3つ(self, match, command_text)のパターン
                        success, message = handler(match, command)
                        if success:
                            # パースの成功・失敗によって処理を分ける
                            command_type = handler.__name__.lstrip('_')
                            params = {'message': message}
                            if 'browser' in command_type:
                                params['url'] = match.group(3).strip() if len(match.groups()) >= 3 else ''
                            elif 'youtube' in command_type or 'google' in command_type:
                                params['query'] = match.group(3).strip() if len(match.groups()) >= 3 else ''
                            return command_type, params
                except Exception as e:
                    self.logger.error(f"コマンド解釈エラー: {e}")
                    return None
        
        # LLMエージェントが設定されている場合、認識できないコマンドをLLMに渡す
        if self.agent_executor is not None:
            try:
                result = self.agent_executor.invoke({"input": command})
                output = result.get("output", "タスクを完了しました")
                return "llm_browser_control", {"message": output}
            except Exception as e:
                self.logger.error(f"LLM解釈エラー: {e}")
                # エラーが発生しても通常の解釈フローに戻る
        
        # デフォルトのコマンド解釈ロジック
        # ブラウザコマンド
        if re.search(r'(edge|chrome|firefox|ブラウザ)\s+(https?://.+)', command, re.IGNORECASE):
            match = re.search(r'(edge|chrome|firefox|ブラウザ)\s+(https?://.+)', command, re.IGNORECASE)
            browser = match.group(1).lower()
            url = match.group(2).strip()
            return 'browser', {'browser': browser, 'url': url}
            
        # 最小化コマンド
        if re.search(r'(.+)を?(最小化|最小化して)', command):
            match = re.search(r'(.+)を?(最小化|最小化して)', command)
            window = match.group(1).strip()
            return 'minimize', {'window': window}
            
        # アプリケーション起動コマンド
        if re.search(r'(.+)を?(起動|開いて|実行して)', command):
            match = re.search(r'(.+)を?(起動|開いて|実行して)', command)
            app = match.group(1).strip()
            return 'launch', {'app': app}
            
        return None

    def start_monitoring(self):
        """キーボードの監視を開始"""
        self.keyboard_monitor.start(self._on_key_press)

    def stop_monitoring(self):
        """キーボードの監視を停止"""
        self.keyboard_monitor.stop()

    def _on_key_press(self, key: str):
        """キー入力時のコールバック"""
        if self.is_recording:
            self.command_buffer.append(key)

    def start_recording(self):
        """コマンドの記録を開始"""
        self.is_recording = True
        self.command_buffer.clear()

    def stop_recording(self) -> str:
        """コマンドの記録を停止し、記録されたコマンドを返す"""
        self.is_recording = False
        command = ''.join(self.command_buffer)
        self.command_buffer.clear()
        return command

    def initialize_browser(self):
        """browser_useのブラウザを初期化"""
        if not BROWSER_USE_AVAILABLE:
            self.logger.warning("browser_useが利用できないため、従来のブラウザコントローラーを使用します")
            return False
            
        if self.browser is None:
            # 新しいイベントループの作成
            if self.browser_loop is None:
                self.browser_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.browser_loop)
            
            async def init_browser_async():
                try:
                    # Browserインスタンスを作成
                    self.browser = Browser()
                    self.logger.info("browser_useブラウザインスタンスを初期化しました")
                    return True
                except Exception as e:
                    self.logger.error(f"browser_useブラウザの初期化に失敗しました: {e}")
                    return False
            
            # 非同期で初期化を実行
            if threading.current_thread() is threading.main_thread():
                return self.browser_loop.run_until_complete(init_browser_async())
            else:
                # 別スレッドから呼ばれた場合は結果を受け取る
                result = [False]
                def run_async():
                    result[0] = self.browser_loop.run_until_complete(init_browser_async())
                
                thread = threading.Thread(target=run_async)
                thread.start()
                thread.join()
                return result[0]
        
        return self.browser is not None

    def parse_command(self, command_text: str) -> Tuple[bool, str]:
        """
        テキストコマンドを解析して適切な関数を呼び出す
        
        Args:
            command_text: コマンドテキスト
            
        Returns:
            Tuple[bool, str]: (成功したかどうか, 結果または詳細メッセージ)
        """
        for pattern, handler in self.command_patterns:
            match = re.search(pattern, command_text, re.IGNORECASE)
            if match:
                self.logger.info(f"コマンドマッチ: '{command_text}' -> {pattern}")
                try:
                    # handler関数のパラメータ数を確認
                    if hasattr(handler, '__code__') and handler.__code__.co_argcount == 3:
                        # 引数が3つ(self, match, command_text)のパターン
                        result = handler(match, command_text)
                        return result
                    else:
                        # 引数が2つ(self, match)のパターン - 互換性のため
                        command_type, params = handler(match)
                        return True, f"{command_type}コマンドを実行: {params}"
                except Exception as e:
                    self.logger.error(f"コマンド実行エラー: {e}")
                    return False, f"コマンド実行中にエラーが発生しました: {str(e)}"
        
        self.logger.warning(f"認識できないコマンド: '{command_text}'")
        return False, f"コマンド '{command_text}' を認識できませんでした"
    
    def execute_command(self, command: str) -> bool:
        """コマンドを実行"""
        self.logger.info(f"コマンド実行開始: {command}")
        success, message = self.parse_command(command)
        self.logger.info(f"コマンド実行結果: {success}, {message}")
        return success
    
    def _run_browser_async(self, coro):
        """browser_useの非同期関数を実行するヘルパーメソッド"""
        if not BROWSER_USE_AVAILABLE:
            self.logger.warning("browser_useが利用できないため、従来のコントローラーを使用します")
            return False
            
        browser_initialized = self.initialize_browser()
        if not browser_initialized or self.browser is None:
            self.logger.error("ブラウザが初期化されていません")
            return False
        
        # 実行するコルーチン
        async def run_and_return():
            try:
                return await coro
            except Exception as e:
                self.logger.error(f"ブラウザ操作エラー: {e}")
                return False
        
        # メインスレッドかどうかで実行方法を変える
        if threading.current_thread() is threading.main_thread():
            return self.browser_loop.run_until_complete(run_and_return())
        else:
            # 別スレッドの場合は結果を受け取るための仕組みを作る
            result = [None]
            def run_async():
                result[0] = self.browser_loop.run_until_complete(run_and_return())
            
            thread = threading.Thread(target=run_async)
            thread.start()
            thread.join()
            return result[0]
    
    # ブラウザ関連ハンドラ (browser_useを使用)
    def _open_browser(self, match, command_text: str) -> Tuple[bool, str]:
        """ブラウザを開くコマンドを処理 (browser_useを使用)"""
        url = match.group(3).strip()
        # URLにスキームがない場合は追加
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        try:
            # browser_useを使用
            success = self._run_browser_async(self.browser.navigate(url))
            if success:
                message = f"ブラウザで {url} を開きました"
                return True, message
            
            # browser_useが失敗した場合、従来のコントローラーを使用
            self.logger.info("browser_useによる操作が失敗しました。従来のコントローラーを使用します。")
            success = self.browser_controller.open_browser(url)
            message = f"ブラウザで {url} を開き" + ("ました" if success else "ませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"ブラウザ操作エラー: {e}")
            return False, f"ブラウザ操作中にエラーが発生しました: {str(e)}"
    
    def _open_youtube(self, match, command_text: str) -> Tuple[bool, str]:
        """YouTubeを開くコマンドを処理 (browser_useを使用)"""
        try:
            # browser_useを使用
            success = self._run_browser_async(self.browser.navigate("https://www.youtube.com"))
            if success:
                message = "YouTubeを開きました"
                return True, message
            
            # 失敗した場合は従来のコントローラーを使用
            self.logger.info("browser_useによる操作が失敗しました。従来のコントローラーを使用します。")
            success = self.browser_controller.open_browser("https://www.youtube.com")
            message = "YouTubeを開き" + ("ました" if success else "ませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"YouTube表示エラー: {e}")
            return False, f"YouTubeを開く際にエラーが発生しました: {str(e)}"
    
    def _search_youtube(self, match, command_text: str) -> Tuple[bool, str]:
        """YouTubeで検索するコマンドを処理 (browser_useを使用)"""
        query = match.group(3).strip()
        
        try:
            # browser_useを使用して検索
            search_function = self.browser.search_youtube if hasattr(self.browser, 'search_youtube') else self.browser.youtube
            success = self._run_browser_async(search_function(query))
            if success:
                message = f"YouTubeで '{query}' を検索しました"
                return True, message
                
            # 失敗した場合は従来のコントローラーを使用
            self.logger.info("browser_useによる操作が失敗しました。従来のコントローラーを使用します。")
            success = self.browser_controller.search_on_youtube(query)
            message = f"YouTubeで '{query}' を検索し" + ("ました" if success else "ませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"YouTube検索エラー: {e}")
            return False, f"YouTube検索中にエラーが発生しました: {str(e)}"
    
    def _search_google(self, match, command_text: str) -> Tuple[bool, str]:
        """Googleで検索するコマンドを処理 (browser_useを使用)"""
        query = match.group(3).strip()
        
        try:
            # browser_useを使用して検索
            search_function = self.browser.search_google if hasattr(self.browser, 'search_google') else self.browser.google
            success = self._run_browser_async(search_function(query))
            if success:
                message = f"Googleで '{query}' を検索しました"
                return True, message
                
            # 失敗した場合は従来のコントローラーを使用
            self.logger.info("browser_useによる操作が失敗しました。従来のコントローラーを使用します。")
            success = self.browser_controller.search_on_google(query)
            message = f"Googleで '{query}' を検索し" + ("ました" if success else "ませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"Google検索エラー: {e}")
            return False, f"Google検索中にエラーが発生しました: {str(e)}"
    
    def _open_gmail(self, match, command_text: str) -> Tuple[bool, str]:
        """Gmailを開くコマンドを処理 (browser_useを使用)"""
        try:
            # browser_useを使用
            success = self._run_browser_async(self.browser.navigate("https://mail.google.com"))
            if success:
                message = "Gmailを開きました"
                return True, message
                
            # 失敗した場合は従来のコントローラーを使用
            self.logger.info("browser_useによる操作が失敗しました。従来のコントローラーを使用します。")
            success = self.browser_controller.open_gmail()
            message = "Gmailを開き" + ("ました" if success else "ませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"Gmail操作エラー: {e}")
            return False, f"Gmail操作中にエラーが発生しました: {str(e)}"
    
    def _open_calendar(self, match, command_text: str) -> Tuple[bool, str]:
        """カレンダーを開くコマンドを処理 (browser_useを使用)"""
        try:
            # browser_useを使用
            success = self._run_browser_async(self.browser.navigate("https://calendar.google.com"))
            if success:
                message = "カレンダーを開きました"
                return True, message
                
            # 失敗した場合は従来のコントローラーを使用
            self.logger.info("browser_useによる操作が失敗しました。従来のコントローラーを使用します。")
            success = self.browser_controller.open_calendar()
            message = "カレンダーを開き" + ("ました" if success else "ませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"カレンダー操作エラー: {e}")
            return False, f"カレンダー操作中にエラーが発生しました: {str(e)}"
    
    # 高度なブラウザ操作コマンド (browser_useでのみ実装)
    def _click_element(self, match, command_text: str) -> Tuple[bool, str]:
        """要素をクリックするコマンドを処理"""
        selector = match.group(3).strip()
        
        try:
            # セレクタの前処理
            if not selector.startswith(('#', '.', '[', '/')):
                # 単純なテキストの場合は、テキストを含む要素を探す
                selector = f"//*[contains(text(), '{selector}')]"
            
            # browser_useを使用して要素をクリック
            success = self._run_browser_async(self.browser.click(selector))
            message = f"要素 '{selector}' を" + ("クリックしました" if success else "クリックできませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"要素クリックエラー: {e}")
            return False, f"要素クリック中にエラーが発生しました: {str(e)}"
    
    def _take_screenshot(self, match, command_text: str) -> Tuple[bool, str]:
        """スクリーンショットを撮るコマンドを処理"""
        try:
            # スクリーンショットの保存先
            now = time.strftime("%Y%m%d_%H%M%S")
            screenshot_dir = os.path.join(os.path.expanduser("~"), "Documents", "DesktopAgent", "Screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshot_dir, f"screenshot_{now}.png")
            
            # browser_useを使用してスクリーンショット撮影
            success = self._run_browser_async(self.browser.screenshot(screenshot_path))
            message = f"スクリーンショットを" + (f"{screenshot_path}に保存しました" if success else "保存できませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"スクリーンショットエラー: {e}")
            return False, f"スクリーンショット撮影中にエラーが発生しました: {str(e)}"
    
    # システム関連ハンドラ
    def _volume_up(self, match, command_text: str) -> Tuple[bool, str]:
        """音量を上げるコマンドを処理"""
        try:
            # 音量を上げる（Windows）
            for _ in range(5):  # 5段階上げる
                pyautogui.press('volumeup')
            return True, "音量を上げました"
        except Exception as e:
            self.logger.error(f"音量調整エラー: {e}")
            return False, f"音量を上げられませんでした: {str(e)}"
    
    def _volume_down(self, match, command_text: str) -> Tuple[bool, str]:
        """音量を下げるコマンドを処理"""
        try:
            # 音量を下げる（Windows）
            for _ in range(5):  # 5段階下げる
                pyautogui.press('volumedown')
            return True, "音量を下げました"
        except Exception as e:
            self.logger.error(f"音量調整エラー: {e}")
            return False, f"音量を下げられませんでした: {str(e)}"
    
    def _mute(self, match, command_text: str) -> Tuple[bool, str]:
        """ミュートするコマンドを処理"""
        try:
            # ミュート（Windows）
            pyautogui.press('volumemute')
            return True, "ミュートしました"
        except Exception as e:
            self.logger.error(f"ミュートエラー: {e}")
            return False, f"ミュートできませんでした: {str(e)}"
    
    def get_available_browsers(self) -> List[str]:
        """利用可能なブラウザのリストを取得"""
        return self.browser_controller.get_available_browsers()

    def close_browser(self):
        """browser_useのブラウザを閉じる"""
        if self.browser is not None:
            try:
                # 非同期関数を同期的に実行
                if self.browser_loop:
                    self.browser_loop.run_until_complete(self.browser.close())
                self.logger.info("browser_useブラウザインスタンスを閉じました")
            except Exception as e:
                self.logger.error(f"ブラウザを閉じる際にエラーが発生しました: {e}")
            finally:
                self.browser = None
                
        if self.browser_loop is not None:
            try:
                self.browser_loop.close()
            except Exception:
                pass
            finally:
                self.browser_loop = None


# 使用例：
"""
# --------------------------------------------
# LangChainとbrowser-useを組み合わせた使用例
# --------------------------------------------

# OpenAIモデルを使用する場合
from langchain_openai import OpenAI
from src.agent.command_interpreter import CommandInterpreter

# API keyは環境変数OPENAI_API_KEYから取得
llm = OpenAI(temperature=0)

# CommandInterpreterを初期化し、LLMを設定
interpreter = CommandInterpreter(llm)

# 通常のコマンド実行
interpreter.execute_command("YouTubeを開いて")

# LLMによるブラウザ操作（より複雑なタスクも可能）
interpreter.execute_command("AIにブラウザを操作してもらう")

# ----------------------
# 他のLLMを使用する例
# ----------------------

# Anthropicモデルを使用する場合
from langchain_anthropic import ChatAnthropic

anthropic_llm = ChatAnthropic(model="claude-3-opus-20240229")
interpreter = CommandInterpreter(anthropic_llm)

# GoogleのGeminiモデルを使用する場合
from langchain_google_genai import ChatGoogleGenerativeAI

gemini_llm = ChatGoogleGenerativeAI(model="gemini-pro")
interpreter = CommandInterpreter(gemini_llm)

# LLMとブラウザ操作を統合したアプリケーション例
# ユーザーの自然言語指示をブラウザ操作に変換
def run_browser_with_llm(user_instruction):
    # LLMでブラウザを操作
    result = interpreter.agent_executor.invoke({"input": user_instruction})
    return result["output"]

# 使用例
result = run_browser_with_llm("GoogleでPythonの最新バージョンを検索して、公式サイトを開いてください")
print(result)
"""

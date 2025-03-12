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
            # ブラウザ名 + サイト名/URL形式のコマンド（例：edge youtube）
            (r'^(edge|chrome|firefox|brave|opera)\s+(youtube|google|gmail|calendar|maps|drive)$', self._browser_site),
            (r'^(edge|chrome|firefox|brave|opera)\s+(https?://.+)$', self._browser_url),
            
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
        try:
            from langchain.agents import Tool, AgentExecutor, create_react_agent
            from langchain_core.prompts import PromptTemplate
            
            # ブラウザ操作用のツールを定義
            tools = [
                Tool(
                    name="navigate",
                    func=self._tool_navigate,
                    description="ブラウザで指定されたURLに移動します。URLを引数として渡してください。"
                ),
                Tool(
                    name="click",
                    func=self._tool_click,
                    description="ブラウザ上の要素をクリックします。CSSセレクタかXPathを引数として渡してください。"
                ),
                Tool(
                    name="type",
                    func=self._tool_type,
                    description="ブラウザ上の入力欄にテキストを入力します。'セレクタ, テキスト'の形式で引数を渡してください。"
                ),
                Tool(
                    name="screenshot",
                    func=self._tool_screenshot,
                    description="現在のページのスクリーンショットを撮り、保存します。引数は不要です。"
                ),
                Tool(
                    name="get_text",
                    func=self._tool_get_text,
                    description="指定した要素のテキストを取得します。CSSセレクタかXPathを引数として渡してください。"
                ),
                Tool(
                    name="execute_js",
                    func=self._tool_execute_js,
                    description="JavaScriptコードをブラウザ上で実行します。JavaScriptコードを引数として渡してください。"
                ),
            ]
            
            # プロンプトテンプレート
            template = """あなたはブラウザを操作するAIアシスタントです。
            ユーザーの要望に応じて、提供されたツールを使用してブラウザを操作します。
            
            使用可能なツール:
            {tools}
            
            以下は実行すべきタスクです:
            {input}
            
            このタスクを完了するために必要なステップを考えてください。
            ブラウザの状態を追跡し、それに応じて適切なツールを呼び出してください。
            
            思考: タスクを分解し、ステップバイステップでどのように進めるか考えてください
            行動: 使用するツール名と引数
            観察: ツールの出力
            ... (思考/行動/観察を繰り返す)
            
            タスクが完了したら、最終的な結果を報告してください。"""
            
            # プロンプトを作成
            prompt = PromptTemplate.from_template(template)
            
            # REACTエージェントを作成
            agent = create_react_agent(llm, tools, prompt)
            
            # エージェント実行環境を構築
            self.agent_executor = AgentExecutor.from_agent_and_tools(
                agent=agent,
                tools=tools,
                verbose=True,
                handle_parsing_errors=True
            )
            
            self.logger.info("LangChainエージェントを初期化しました")
            return True
        except Exception as e:
            self.logger.error(f"LangChainエージェント初期化エラー: {e}")
            return False
            
    # LLMエージェント用のツール関数
    def _tool_navigate(self, url: str) -> str:
        """ブラウザでURLに移動するツール"""
        if self.browser is None:
            self.initialize_browser()
            if self.browser is None:
                return "ブラウザを初期化できませんでした"
        
        try:
            # URLにスキームがない場合は追加
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
                
            # browser_methodsを使用
            if hasattr(self, 'browser_methods') and 'navigate' in self.browser_methods:
                success = self._run_browser_async(self.browser_methods['navigate'](url))
            else:
                # 互換性維持のため直接呼び出し
                success = self._run_browser_async(self.browser.navigate(url))
                
            if success:
                return f"URLに移動しました: {url}"
            else:
                return f"URLへの移動に失敗しました: {url}"
        except Exception as e:
            self.logger.error(f"ブラウザ移動エラー: {e}")
            return f"エラーが発生しました: {str(e)}"
    
    def _tool_click(self, selector: str) -> str:
        """ブラウザで要素をクリックするツール"""
        if self.browser is None:
            self.initialize_browser()
            if self.browser is None:
                return "ブラウザを初期化できませんでした"
        
        try:
            # セレクタの前処理
            if not selector.startswith(('#', '.', '[', '/')):
                # 単純なテキストの場合は、テキストを含む要素を探す
                selector = f"//*[contains(text(), '{selector}')]"
            
            # browser_methodsを使用
            if hasattr(self, 'browser_methods') and 'click' in self.browser_methods and self.browser_methods['click'] is not None:
                success = self._run_browser_async(self.browser_methods['click'](selector))
            else:
                # 互換性維持のため直接呼び出し
                success = self._run_browser_async(self.browser.click(selector))
                
            if success:
                return f"要素をクリックしました: {selector}"
            else:
                return f"要素のクリックに失敗しました: {selector}"
        except Exception as e:
            self.logger.error(f"要素クリックエラー: {e}")
            return f"エラーが発生しました: {str(e)}"
        
    def _tool_type(self, selector_and_text: str) -> str:
        """テキストを入力するツール"""
        if self.browser is None:
            self.initialize_browser()
            if self.browser is None:
                return "ブラウザを初期化できませんでした"
                
        try:
            # 入力データの分割
            parts = selector_and_text.split(',', 1)
            if len(parts) != 2:
                return "無効な入力形式です。'セレクタ, テキスト'の形式で入力してください"
                
            selector = parts[0].strip()
            text = parts[1].strip()
            
            # browser_methodsを使用
            if hasattr(self, 'browser_methods') and 'type' in self.browser_methods and self.browser_methods['type'] is not None:
                success = self._run_browser_async(self.browser_methods['type'](selector, text))
            else:
                # 互換性維持のため直接呼び出し
                success = self._run_browser_async(self.browser.type(selector, text))
                
            if success:
                return f"テキストを入力しました: セレクタ '{selector}', テキスト '{text}'"
            else:
                return f"テキスト入力に失敗しました: セレクタ '{selector}'"
        except Exception as e:
            self.logger.error(f"テキスト入力エラー: {e}")
            return f"エラーが発生しました: {str(e)}"
    
    def _tool_screenshot(self) -> str:
        """スクリーンショットを撮るツール"""
        if self.browser is None:
            self.initialize_browser()
            if self.browser is None:
                return "ブラウザを初期化できませんでした"
        
        try:
            # スクリーンショットの保存先
            now = time.strftime("%Y%m%d_%H%M%S")
            screenshot_dir = os.path.join(os.path.expanduser("~"), "Documents", "DesktopAgent", "Screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshot_dir, f"screenshot_{now}.png")
            
            # browser_methodsを使用
            if hasattr(self, 'browser_methods') and 'screenshot' in self.browser_methods and self.browser_methods['screenshot'] is not None:
                success = self._run_browser_async(self.browser_methods['screenshot'](screenshot_path))
            else:
                # 互換性維持のため直接呼び出し
                success = self._run_browser_async(self.browser.screenshot(screenshot_path))
                
            if success:
                return f"スクリーンショットを保存しました: {screenshot_path}"
            else:
                return "スクリーンショットの保存に失敗しました"
        except Exception as e:
            self.logger.error(f"スクリーンショットエラー: {e}")
            return f"エラーが発生しました: {str(e)}"
    
    def _tool_get_text(self, selector: str) -> str:
        """要素のテキストを取得するツール"""
        if self.browser is None:
            self.initialize_browser()
            if self.browser is None:
                return "ブラウザを初期化できませんでした"
        
        try:
            # browser_methodsを使用
            if hasattr(self, 'browser_methods') and 'get_text' in self.browser_methods and self.browser_methods['get_text'] is not None:
                text = self._run_browser_async(self.browser_methods['get_text'](selector))
            else:
                # 互換性維持のため直接呼び出し
                text = self._run_browser_async(self.browser.get_text(selector))
                
            if text:
                return f"取得したテキスト: {text}"
            else:
                return f"テキストを取得できませんでした: セレクタ '{selector}'"
        except Exception as e:
            self.logger.error(f"テキスト取得エラー: {e}")
            return f"エラーが発生しました: {str(e)}"
    
    def _tool_execute_js(self, code: str) -> str:
        """JavaScriptを実行するツール"""
        if self.browser is None:
            self.initialize_browser()
            if self.browser is None:
                return "ブラウザを初期化できませんでした"
        
        try:
            # browser_methodsを使用
            if hasattr(self, 'browser_methods') and 'evaluate' in self.browser_methods and self.browser_methods['evaluate'] is not None:
                result = self._run_browser_async(self.browser_methods['evaluate'](code))
            else:
                # 互換性維持のため直接呼び出し
                result = self._run_browser_async(self.browser.evaluate(code))
                
            if result is not None:
                return f"JavaScriptの実行結果: {result}"
            else:
                return "JavaScriptを実行しました"
        except Exception as e:
            self.logger.error(f"JavaScript実行エラー: {e}")
            return f"エラーが発生しました: {str(e)}"
        
    def _control_with_llm(self, match, command_text: str) -> Tuple[bool, str]:
        """LLMを使ってブラウザを操作するコマンドを処理"""
        if self.agent_executor is None:
            return False, "LLMエージェントが初期化されていません。先にLLMを設定してください。"
            
        # browser_useが初期化されていない場合は初期化を試みる
        if self.browser is None:
            browser_initialized = self.initialize_browser()
            if not browser_initialized:
                return False, "ブラウザが初期化されていないため、LLMによるブラウザ操作ができません。"
            
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
            
        try:
            if self.browser is None:
                # 新しいイベントループの作成
                if self.browser_loop is None:
                    self.browser_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self.browser_loop)
                
                async def init_browser_async():
                    try:
                        # Browserインスタンスを作成
                        self.browser = Browser()
                        # APIメソッドの存在を確認
                        self.browser_methods = {}
                        # navigate/open/gotoメソッドのいずれかを使用
                        if hasattr(self.browser, 'navigate'):
                            self.browser_methods['navigate'] = self.browser.navigate
                        elif hasattr(self.browser, 'open'):
                            self.browser_methods['navigate'] = self.browser.open
                        elif hasattr(self.browser, 'goto'):
                            self.browser_methods['navigate'] = self.browser.goto
                        else:
                            self.browser_methods['navigate'] = lambda url: self.browser._page.goto(url)
                            
                        # YouTubeメソッド
                        if hasattr(self.browser, 'youtube'):
                            self.browser_methods['youtube'] = self.browser.youtube
                        elif hasattr(self.browser, 'search_youtube'):
                            self.browser_methods['youtube'] = self.browser.search_youtube
                        
                        # Googleメソッド
                        if hasattr(self.browser, 'google'):
                            self.browser_methods['google'] = self.browser.google
                        elif hasattr(self.browser, 'search_google'):
                            self.browser_methods['google'] = self.browser.search_google
                            
                        # その他のメソッド
                        self.browser_methods['click'] = getattr(self.browser, 'click', None)
                        self.browser_methods['type'] = getattr(self.browser, 'type', None)
                        self.browser_methods['screenshot'] = getattr(self.browser, 'screenshot', None)
                        self.browser_methods['get_text'] = getattr(self.browser, 'get_text', None)
                        self.browser_methods['evaluate'] = getattr(self.browser, 'evaluate', None)
                        
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
        except Exception as e:
            self.logger.error(f"ブラウザ初期化中に予期せぬエラーが発生しました: {e}")
            return False

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
            
        if self.browser is None:
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
        try:
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
        except Exception as e:
            self.logger.error(f"ブラウザ非同期実行中にエラーが発生しました: {e}")
            return False
    
    # ブラウザ関連ハンドラ (browser_useを使用)
    def _open_browser(self, match, command_text: str) -> Tuple[bool, str]:
        """ブラウザを開くコマンドを処理 (browser_useを使用)"""
        url = match.group(3).strip()
        # URLにスキームがない場合は追加
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        try:
            # browser_useを使用
            if self.browser is not None and 'navigate' in self.browser_methods:
                success = self._run_browser_async(self.browser_methods['navigate'](url))
                if success:
                    message = f"ブラウザで {url} を開きました"
                    return True, message
            
            # ブラウザがNoneまたは失敗した場合、従来のコントローラーを使用
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
            if self.browser is not None and 'navigate' in self.browser_methods:
                success = self._run_browser_async(self.browser_methods['navigate']("https://www.youtube.com"))
                if success:
                    message = "YouTubeを開きました"
                    return True, message
            
            # ブラウザがNoneまたは失敗した場合は従来のコントローラーを使用
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
            if self.browser is not None and hasattr(self, 'browser_methods') and 'youtube' in self.browser_methods:
                success = self._run_browser_async(self.browser_methods['youtube'](query))
                if success:
                    message = f"YouTubeで '{query}' を検索しました"
                    return True, message
                
            # ブラウザがNoneまたは失敗した場合は従来のコントローラーを使用
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
            if self.browser is not None and hasattr(self, 'browser_methods') and 'google' in self.browser_methods:
                success = self._run_browser_async(self.browser_methods['google'](query))
                if success:
                    message = f"Googleで '{query}' を検索しました"
                    return True, message
                
            # ブラウザがNoneまたは失敗した場合は従来のコントローラーを使用
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
            if self.browser is not None and hasattr(self, 'browser_methods') and 'navigate' in self.browser_methods:
                success = self._run_browser_async(self.browser_methods['navigate']("https://mail.google.com"))
                if success:
                    message = "Gmailを開きました"
                    return True, message
                
            # ブラウザがNoneまたは失敗した場合は従来のコントローラーを使用
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
            if self.browser is not None and hasattr(self, 'browser_methods') and 'navigate' in self.browser_methods:
                success = self._run_browser_async(self.browser_methods['navigate']("https://calendar.google.com"))
                if success:
                    message = "カレンダーを開きました"
                    return True, message
                
            # ブラウザがNoneまたは失敗した場合は従来のコントローラーを使用
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
            # browser_useが初期化されていない場合は初期化を試みる
            if self.browser is None:
                self.initialize_browser()
                
            if self.browser is None:
                return False, "ブラウザが初期化されていないため、要素をクリックできません。"
                
            # セレクタの前処理
            if not selector.startswith(('#', '.', '[', '/')):
                # 単純なテキストの場合は、テキストを含む要素を探す
                selector = f"//*[contains(text(), '{selector}')]"
            
            # browser_useを使用して要素をクリック
            if hasattr(self, 'browser_methods') and 'click' in self.browser_methods and self.browser_methods['click'] is not None:
                success = self._run_browser_async(self.browser_methods['click'](selector))
            else:
                # 互換性のためにブラウザの直接メソッドを試みる
                success = self._run_browser_async(self.browser.click(selector))
                
            message = f"要素 '{selector}' を" + ("クリックしました" if success else "クリックできませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"要素クリックエラー: {e}")
            return False, f"要素クリック中にエラーが発生しました: {str(e)}"
    
    def _take_screenshot(self, match, command_text: str) -> Tuple[bool, str]:
        """スクリーンショットを撮るコマンドを処理"""
        try:
            # browser_useが初期化されていない場合は初期化を試みる
            if self.browser is None:
                self.initialize_browser()
                
            if self.browser is None:
                return False, "ブラウザが初期化されていないため、スクリーンショットを撮影できません。"
                
            # スクリーンショットの保存先
            now = time.strftime("%Y%m%d_%H%M%S")
            screenshot_dir = os.path.join(os.path.expanduser("~"), "Documents", "DesktopAgent", "Screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshot_dir, f"screenshot_{now}.png")
            
            # browser_useを使用してスクリーンショット撮影
            if hasattr(self, 'browser_methods') and 'screenshot' in self.browser_methods and self.browser_methods['screenshot'] is not None:
                success = self._run_browser_async(self.browser_methods['screenshot'](screenshot_path))
            else:
                # 互換性のためにブラウザの直接メソッドを試みる
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

    # 新しいコマンドハンドラー
    def _browser_site(self, match, command_text: str) -> Tuple[bool, str]:
        """ブラウザ名 + サイト名形式のコマンドを処理"""
        browser_name = match.group(1).lower()
        site_name = match.group(2).lower()
        
        # サイト名に基づいてURLを決定
        site_urls = {
            'youtube': 'https://www.youtube.com',
            'google': 'https://www.google.com',
            'gmail': 'https://mail.google.com',
            'calendar': 'https://calendar.google.com',
            'maps': 'https://maps.google.com',
            'drive': 'https://drive.google.com'
        }
        
        url = site_urls.get(site_name)
        if not url:
            return False, f"認識できないサイト名です: {site_name}"
            
        try:
            # ブラウザを開く
            if self.browser is not None and 'navigate' in self.browser_methods:
                success = self._run_browser_async(self.browser_methods['navigate'](url))
                if success:
                    message = f"{browser_name}で{site_name}を開きました"
                    return True, message
            
            # ブラウザがNoneまたは失敗した場合、従来のコントローラーを使用
            self.logger.info("browser_useによる操作が失敗しました。従来のコントローラーを使用します。")
            success = self.browser_controller.open_browser(url, browser=browser_name)
            message = f"{browser_name}で{site_name}を開き" + ("ました" if success else "ませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"ブラウザ操作エラー: {e}")
            return False, f"ブラウザ操作中にエラーが発生しました: {str(e)}"
            
    def _browser_url(self, match, command_text: str) -> Tuple[bool, str]:
        """ブラウザ名 + URL形式のコマンドを処理"""
        browser_name = match.group(1).lower()
        url = match.group(2).strip()
        
        # URLにスキームがない場合は追加
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
            
        try:
            # ブラウザを開く
            if self.browser is not None and 'navigate' in self.browser_methods:
                success = self._run_browser_async(self.browser_methods['navigate'](url))
                if success:
                    message = f"{browser_name}で{url}を開きました"
                    return True, message
            
            # ブラウザがNoneまたは失敗した場合、従来のコントローラーを使用
            self.logger.info("browser_useによる操作が失敗しました。従来のコントローラーを使用します。")
            success = self.browser_controller.open_browser(url, browser=browser_name)
            message = f"{browser_name}で{url}を開き" + ("ました" if success else "ませんでした")
            return success, message
        except Exception as e:
            self.logger.error(f"ブラウザ操作エラー: {e}")
            return False, f"ブラウザ操作中にエラーが発生しました: {str(e)}"


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

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
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

# MCPアダプタのインポート
try:
    from mcp.mcp_adapter import MCPAdapter
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    
# 環境変数の読み込み
load_dotenv()

# ロギングの設定
logger = logging.getLogger(__name__)

class CommandInterpreter:
    """
    ユーザーのコマンドを解釈して実行するクラス
    """
    
    def __init__(self, llm: Optional[BaseLanguageModel] = None):
        """
        CommandInterpreterを初期化します。
        
        Args:
            llm (Optional[BaseLanguageModel]): 使用する言語モデル
        """
        self.llm = llm
        self.agent_executor = None
        
        # ブラウザの初期化状態
        self.browser = None
        self.browser_initialized = False
        
        # MCPサーバーの設定
        self.use_mcp = os.environ.get("USE_MCP", "false").lower() == "true"
        self.mcp_adapter = None
        if self.use_mcp and MCP_AVAILABLE:
            try:
                self.mcp_adapter = MCPAdapter()
                logger.info("MCPアダプタを初期化しました")
            except Exception as e:
                logger.error(f"MCPアダプタの初期化に失敗しました: {e}")
                self.mcp_adapter = None
        
        # ブラウザメソッド辞書
        self.browser_methods = {}
        
        # キー操作の監視フラグ
        self.monitoring = False
        self.monitor_thread = None
        
        # 録画関連の変数
        self.recording = False
        self.recorded_keys = []
        
        # LangChainエージェントの設定
        if llm:
            self.setup_langchain_agent(llm)
    
    def setup_langchain_agent(self, llm: BaseLanguageModel):
        """
        LangChainエージェントを設定します。
        
        Args:
            llm (BaseLanguageModel): 使用する言語モデル
        """
        self.llm = llm
        
        # モデルの設定
        gemini_pro = os.environ.get("GOOGLE_API_KEY", "gemini-pro")
        gpt_4omini = os.environ.get("OPENAI_API_KEY", "gpt-4omini")
        claude_sonnet = os.environ.get("ANTHROPIC_API_KEY", "claude-sonnet")
        
        default_model = gemini_pro
        fallback_model = [claude_sonnet, gpt_4omini]  # リストとして定義
        
        def get_model(model_name: str) -> BaseLanguageModel:
            try:
                if model_name == "gemini-pro":
                    return ChatGoogleGenerativeAI(model_name="gemini-2.0-flash", google_api_key=os.environ.get("GOOGLE_API_KEY"))
                elif model_name == "gpt-4omini":
                    return ChatOpenAI(model="gpt-4omini", api_key=os.environ.get("OPENAI_API_KEY"))
                elif model_name == "claude-sonnet":
                    return ChatAnthropic(model="claude-3-5-sonnet-2024 ", api_key=os.environ.get("ANTHROPIC_API_KEY"))
                else:
                    logger.warning(f"不明なモデル名: {model_name}、代替モデルを使用します")
                    # fallback_modelを使用
                    for fallback in fallback_model:
                        try:
                            return get_model(fallback)
                        except Exception as e:
                            logger.warning(f"代替モデル {fallback} の初期化に失敗しました: {e}")
                    raise ValueError(f"利用可能なモデルがありません")
            except Exception as e:
                logger.error(f"モデル初期化エラー: {e}")
                raise
        
        # モデルの設定
        self.llm = get_model(default_model)
        
        # ツールの定義
        tools = [
            Tool(
                name="navigate",
                func=lambda url: self.llm.invoke(self._tool_navigate(url)),
                description="Webブラウザで指定されたURLに移動します。URLのみを引数として受け取ります。"
            ),
            Tool(
                name="click",
                func=lambda selector: self.llm.invoke(self._tool_click(selector)),
                description="指定されたセレクタの要素をクリックします。CSSセレクタのみを引数として受け取ります。"
            ),
            Tool(
                name="type",
                func=lambda selector_and_text: self.llm.invoke(self._tool_type(selector_and_text)),
                description="指定されたセレクタの要素にテキストを入力します。'selector:::text'の形式で引数を受け取ります。"
            ),
            Tool(
                name="screenshot",
                func=lambda: self.llm.invoke(self._tool_screenshot()),
                description="現在のページのスクリーンショットを撮影します。引数は必要ありません。"
            ),
            Tool(
                name="get_text",
                func=lambda selector: self.llm.invoke(self._tool_get_text(selector)),
                description="指定されたセレクタの要素のテキストを取得します。CSSセレクタのみを引数として受け取ります。"
            ),
            Tool(
                name="execute_js",
                func=lambda code: self.llm.invoke(self._tool_execute_js(code)),
                description="ブラウザでJavaScriptコードを実行します。JavaScriptコードのみを引数として受け取ります。"
            )
        ]
        
        # プロンプトテンプレートの定義
        
        template = {
            "system_prompt": """あなたはブラウザを操作するAIアシスタントです。
与えられたタスクを実行するために、指定されたツールを使用してください。

ツール:
{tools}

タスク: {input}

以下の形式で考えを段階的に示してください:
思考: タスクを達成するために何をすべきか考えます。
行動: ツール名と入力値
観察: ツールの出力
... (必要に応じて「思考」、「行動」、「観察」を繰り返します)
答え: タスクの最終結果

思考:"""
        }
        
        prompt = PromptTemplate.from_template(template)
        
        # エージェントの作成
        agent = create_react_agent(self.llm, tools, prompt)
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=10,
            early_stopping_method="generate",
            handle_parsing_errors=True
        )
        
        logger.info("LangChainエージェントを設定しました")
    
    def _tool_navigate(self, url: str) -> str:
        """
        指定したURLに移動します。
        
        Args:
            url (str): 移動先のURL
            
        Returns:
            str: 操作結果のメッセージ
        """
        if not self.browser_initialized:
            self.initialize_browser()
            if not self.browser_initialized:
                return "ブラウザが初期化されていません。"
        
        try:
            if self.use_mcp and self.mcp_adapter:
                # MCPを使用してナビゲーション
                result = self.mcp_adapter.run_async(self.mcp_adapter.navigate(url))
                if result.get("status") == "success":
                    return f"URLに移動しました: {url}"
                else:
                    return f"URLへの移動に失敗しました: {url} - {result.get('message', '不明なエラー')}"
            elif 'navigate' in self.browser_methods and self.browser_methods['navigate']:
                # ブラウザ直接操作
                self._run_browser_async(self.browser_methods['navigate'](url))
                return f"URLに移動しました: {url}"
            else:
                return "ナビゲーション機能が利用できません。"
        except Exception as e:
            logger.error(f"ナビゲーションエラー: {e}")
            return f"エラー: {str(e)}"
    
    def _tool_click(self, selector: str) -> str:
        """
        指定したセレクタの要素をクリックします。
        
        Args:
            selector (str): クリックする要素のセレクタ
            
        Returns:
            str: 操作結果のメッセージ
        """
        if not self.browser_initialized:
            self.initialize_browser()
            if not self.browser_initialized:
                return "ブラウザが初期化されていません。"
        
        try:
            if self.use_mcp and self.mcp_adapter:
                # MCPを使用してクリック
                result = self.mcp_adapter.run_async(self.mcp_adapter.click(selector))
                if result.get("status") == "success":
                    return f"要素をクリックしました: {selector}"
                else:
                    return f"要素のクリックに失敗しました: {selector} - {result.get('message', '不明なエラー')}"
            elif 'click' in self.browser_methods and self.browser_methods['click']:
                # ブラウザ直接操作
                self._run_browser_async(self.browser_methods['click'](selector))
                return f"要素をクリックしました: {selector}"
            else:
                return "クリック機能が利用できません。"
        except Exception as e:
            logger.error(f"クリックエラー: {e}")
            return f"エラー: {str(e)}"
    
    def _tool_type(self, selector_and_text: str) -> str:
        """
        指定したセレクタの要素にテキストを入力します。
        
        Args:
            selector_and_text (str): 'selector:::text'の形式
            
        Returns:
            str: 操作結果のメッセージ
        """
        if not self.browser_initialized:
            self.initialize_browser()
            if not self.browser_initialized:
                return "ブラウザが初期化されていません。"
        
        # selector:::textの形式をパース
        parts = selector_and_text.split(":::", 1)
        if len(parts) != 2:
            return "入力形式が不正です。'selector:::text'の形式で指定してください。"
        
        selector, text = parts
        
        try:
            if self.use_mcp and self.mcp_adapter:
                # MCPを使用してテキスト入力
                result = self.mcp_adapter.run_async(self.mcp_adapter.type_text(selector, text))
                if result.get("status") == "success":
                    return f"テキストを入力しました: {selector} -> {text}"
                else:
                    return f"テキスト入力に失敗しました: {selector} - {result.get('message', '不明なエラー')}"
            elif 'type' in self.browser_methods and self.browser_methods['type']:
                # ブラウザ直接操作
                self._run_browser_async(self.browser_methods['type'](selector, text))
                return f"テキストを入力しました: {selector} -> {text}"
            else:
                return "テキスト入力機能が利用できません。"
        except Exception as e:
            logger.error(f"テキスト入力エラー: {e}")
            return f"エラー: {str(e)}"
    
    def _tool_screenshot(self) -> str:
        """
        スクリーンショットを撮影します。
        
        Returns:
            str: 操作結果のメッセージ
        """
        if not self.browser_initialized:
            self.initialize_browser()
            if not self.browser_initialized:
                return "ブラウザが初期化されていません。"
        
        try:
            screenshot_path = f"screenshot_{int(time.time())}.png"
            
            if self.use_mcp and self.mcp_adapter:
                # MCPを使用してスクリーンショット撮影
                result = self.mcp_adapter.run_async(self.mcp_adapter.screenshot(screenshot_path))
                if result.get("status") == "success":
                    return f"スクリーンショットを撮影しました: {result.get('result', {}).get('path', screenshot_path)}"
                else:
                    return f"スクリーンショット撮影に失敗しました: {result.get('message', '不明なエラー')}"
            elif 'screenshot' in self.browser_methods and self.browser_methods['screenshot']:
                # ブラウザ直接操作
                self._run_browser_async(self.browser_methods['screenshot'](screenshot_path))
                return f"スクリーンショットを撮影しました: {screenshot_path}"
            else:
                return "スクリーンショット機能が利用できません。"
        except Exception as e:
            logger.error(f"スクリーンショットエラー: {e}")
            return f"エラー: {str(e)}"
    
    def _tool_get_text(self, selector: str) -> str:
        """
        指定したセレクタの要素のテキストを取得します。
        
        Args:
            selector (str): テキストを取得する要素のセレクタ
            
        Returns:
            str: 取得したテキスト
        """
        if not self.browser_initialized:
            self.initialize_browser()
            if not self.browser_initialized:
                return "ブラウザが初期化されていません。"
        
        try:
            if self.use_mcp and self.mcp_adapter:
                # MCPを使用してテキスト取得
                result = self.mcp_adapter.run_async(self.mcp_adapter.get_text(selector))
                if result.get("status") == "success":
                    return f"テキスト: {result.get('result', '(テキストなし)')}"
                else:
                    return f"テキスト取得に失敗しました: {selector} - {result.get('message', '不明なエラー')}"
            elif 'get_text' in self.browser_methods and self.browser_methods['get_text']:
                # ブラウザ直接操作
                result = self._run_browser_async(self.browser_methods['get_text'](selector))
                return f"テキスト: {result or '(テキストなし)'}"
            else:
                return "テキスト取得機能が利用できません。"
        except Exception as e:
            logger.error(f"テキスト取得エラー: {e}")
            return f"エラー: {str(e)}"
    
    def _tool_execute_js(self, code: str) -> str:
        """
        JavaScriptコードを実行します。
        
        Args:
            code (str): 実行するJavaScriptコード
            
        Returns:
            str: 実行結果
        """
        if not self.browser_initialized:
            self.initialize_browser()
            if not self.browser_initialized:
                return "ブラウザが初期化されていません。"
        
        try:
            if self.use_mcp and self.mcp_adapter:
                # MCPを使用してJavaScript実行
                result = self.mcp_adapter.run_async(self.mcp_adapter.evaluate_js(code))
                if result.get("status") == "success":
                    return f"実行結果: {result.get('result', '(結果なし)')}"
                else:
                    return f"JavaScript実行に失敗しました: {result.get('message', '不明なエラー')}"
            elif 'evaluate' in self.browser_methods and self.browser_methods['evaluate']:
                # ブラウザ直接操作
                result = self._run_browser_async(self.browser_methods['evaluate'](code))
                return f"実行結果: {result or '(結果なし)'}"
            else:
                return "JavaScript実行機能が利用できません。"
        except Exception as e:
            logger.error(f"JavaScript実行エラー: {e}")
            return f"エラー: {str(e)}"

    def _control_with_llm(self, match, command_text: str) -> Tuple[bool, str]:
        """
        LLMを使用してブラウザを制御します。
        
        Args:
            match: 正規表現マッチオブジェクト
            command_text (str): コマンドテキスト
            
        Returns:
            Tuple[bool, str]: 成功したかどうかと、結果メッセージ
        """
        if not self.agent_executor:
            if not self.llm:
                return False, "LLMが設定されていないため、この操作は実行できません。"
            
            # LLMが設定されている場合は、エージェントを設定
            self.setup_langchain_agent(self.llm)
        
        try:
            # ブラウザが初期化されていない場合は初期化
            if not self.browser_initialized:
                self.initialize_browser()
                if not self.browser_initialized:
                    return False, "ブラウザの初期化に失敗しました。"
            
            # matched_textから実際の命令部分を抽出
            instruction = command_text
            
            # エージェントの実行
            result = self.agent_executor.invoke({"input": instruction})
            return True, result["output"]
        except Exception as e:
            logger.error(f"LLMによるブラウザ制御エラー: {e}")
            return False, f"ブラウザ制御中にエラーが発生しました: {str(e)}"

    def initialize_browser(self):
        """
        ブラウザを初期化します。
        """
        if self.browser_initialized:
            logger.info("ブラウザは既に初期化されています。")
            return
        
        try:
            if self.use_mcp and self.mcp_adapter:
                # MCPサーバーの起動
                if self.mcp_adapter.start_server():
                    # 接続を試行
                    if self.mcp_adapter.run_async(self.mcp_adapter.connect()):
                        self.browser_initialized = True
                        logger.info("MCPサーバー経由でブラウザを初期化しました。")
                        return
                    else:
                        logger.error("MCPサーバーへの接続に失敗しました。")
            
            # MCPが使用できないか、接続に失敗した場合は従来の方法で初期化
            try:
                from browser_use import Browser
                
                # 非同期関数を定義
                async def init_browser_async():
                    try:
                        logger.info("ブラウザを初期化中...")
                        self.browser = Browser()
                        
                        # メソッドの存在を確認し、存在する場合は辞書に追加
                        # navigate/open/gotoのいずれかを使用
                        if hasattr(self.browser, 'navigate'):
                            self.browser_methods['navigate'] = self.browser.navigate
                        elif hasattr(self.browser, 'open'):
                            self.browser_methods['navigate'] = self.browser.open
                        elif hasattr(self.browser, 'goto'):
                            self.browser_methods['navigate'] = self.browser.goto
                        
                        # その他のメソッド
                        self.browser_methods['click'] = getattr(self.browser, 'click', None)
                        self.browser_methods['type'] = getattr(self.browser, 'type', None)
                        self.browser_methods['screenshot'] = getattr(self.browser, 'screenshot', None)
                        self.browser_methods['get_text'] = getattr(self.browser, 'get_text', None)
                        self.browser_methods['evaluate'] = getattr(self.browser, 'evaluate', None)
                        
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
                        
                        logger.info("ブラウザを初期化しました。")
                        self.browser_initialized = True
                    except Exception as e:
                        logger.error(f"ブラウザの初期化に失敗しました: {e}")
                        self.browser = None
                        self.browser_initialized = False
                
                # 非同期関数を実行
                def run_async():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(init_browser_async())
                    loop.close()
                
                run_async()
                
            except ImportError:
                logger.error("browser-useパッケージがインストールされていません。")
                self.browser_initialized = False
        except Exception as e:
            logger.error(f"ブラウザの初期化中にエラーが発生しました: {e}")
            self.browser_initialized = False

    def _run_browser_async(self, coro):
        """
        ブラウザの非同期操作を実行します。
        
        Args:
            coro: 実行する非同期コルーチン
            
        Returns:
            Any: コルーチンの実行結果
        """
        result = None
        
        async def run_and_return():
            nonlocal result
            try:
                result = await coro
                return result
            except Exception as e:
                logger.error(f"ブラウザ操作エラー: {e}")
                raise
        
        try:
            # 現在のスレッドがメインスレッドでない場合、新しいイベントループを作成
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # "There is no current event loop in thread"
                def run_async():
                    nonlocal result
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(run_and_return())
                    loop.close()
                
                run_async()
                return result
            
            # メインスレッドの場合は直接実行
            return loop.run_until_complete(run_and_return())
            
        except Exception as e:
            logger.error(f"ブラウザ操作の実行に失敗しました: {e}")
            raise

    def _search_youtube(self, match, command_text: str) -> Tuple[bool, str]:
        """
        YouTubeで検索を実行します。
        
        Args:
            match: 正規表現マッチオブジェクト
            command_text (str): コマンドテキスト
            
        Returns:
            Tuple[bool, str]: 成功したかどうかと、結果メッセージ
        """
        # ブラウザが初期化されていない場合は初期化
        if not self.browser_initialized:
            self.initialize_browser()
            if not self.browser_initialized:
                return False, "ブラウザの初期化に失敗しました。"
        
        # 検索クエリの抽出
        query = match.group(1).strip() if match and match.groups() else ""
        if not query:
            return False, "検索クエリが指定されていません。"
        
        try:
            if self.use_mcp and self.mcp_adapter:
                # MCPを使用してYouTube検索
                result = self.mcp_adapter.run_async(self.mcp_adapter.search_youtube(query))
                if result.get("status") == "success":
                    return True, f"YouTubeで「{query}」を検索しました。"
                else:
                    return False, f"YouTube検索に失敗しました: {result.get('message', '不明なエラー')}"
            elif 'youtube' in self.browser_methods and self.browser_methods['youtube']:
                # ブラウザ直接操作
                self._run_browser_async(self.browser_methods['youtube'](query))
                return True, f"YouTubeで「{query}」を検索しました。"
            else:
                # 直接URLにアクセス
                url = f"https://www.youtube.com/results?search_query={query}"
                return self._browser_url(None, url)
        except Exception as e:
            logger.error(f"YouTube検索エラー: {e}")
            return False, f"YouTube検索中にエラーが発生しました: {str(e)}"
    
    def _search_google(self, match, command_text: str) -> Tuple[bool, str]:
        """
        Googleで検索を実行します。
        
        Args:
            match: 正規表現マッチオブジェクト
            command_text (str): コマンドテキスト
            
        Returns:
            Tuple[bool, str]: 成功したかどうかと、結果メッセージ
        """
        # ブラウザが初期化されていない場合は初期化
        if not self.browser_initialized:
            self.initialize_browser()
            if not self.browser_initialized:
                return False, "ブラウザの初期化に失敗しました。"
        
        # 検索クエリの抽出
        query = match.group(1).strip() if match and match.groups() else ""
        if not query:
            return False, "検索クエリが指定されていません。"
        
        try:
            if self.use_mcp and self.mcp_adapter:
                # MCPを使用してGoogle検索
                result = self.mcp_adapter.run_async(self.mcp_adapter.search_google(query))
                if result.get("status") == "success":
                    return True, f"Googleで「{query}」を検索しました。"
                else:
                    return False, f"Google検索に失敗しました: {result.get('message', '不明なエラー')}"
            elif 'google' in self.browser_methods and self.browser_methods['google']:
                # ブラウザ直接操作
                self._run_browser_async(self.browser_methods['google'](query))
                return True, f"Googleで「{query}」を検索しました。"
            else:
                # 直接URLにアクセス
                url = f"https://www.google.com/search?q={query}"
                return self._browser_url(None, url)
        except Exception as e:
            logger.error(f"Google検索エラー: {e}")
            return False, f"Google検索中にエラーが発生しました: {str(e)}"

    def close_browser(self):
        """
        ブラウザを閉じます。
        """
        if not self.browser_initialized:
            logger.info("ブラウザは初期化されていません。")
            return
        
        try:
            if self.use_mcp and self.mcp_adapter:
                # MCPサーバーを停止
                self.mcp_adapter.run_async(self.mcp_adapter.disconnect())
                self.mcp_adapter.stop_server()
                logger.info("MCPサーバーを停止しました。")
            elif self.browser:
                # ブラウザ直接操作
                async def close_browser_async():
                    try:
                        # クローズメソッドを探す
                        if hasattr(self.browser, 'close'):
                            await self.browser.close()
                        elif hasattr(self.browser, 'shutdown'):
                            await self.browser.shutdown()
                        logger.info("ブラウザを閉じました。")
                    except Exception as e:
                        logger.error(f"ブラウザを閉じる際にエラーが発生しました: {e}")
                
                # 非同期関数を実行
                self._run_browser_async(close_browser_async())
            
            # 状態をリセット
            self.browser = None
            self.browser_methods = {}
            self.browser_initialized = False
            
        except Exception as e:
            logger.error(f"ブラウザを閉じる際にエラーが発生しました: {e}")

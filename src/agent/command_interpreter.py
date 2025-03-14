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
import urllib.parse

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
        
        if self.use_mcp:
            if MCP_AVAILABLE:
                try:
                    from mcp.mcp_adapter import MCPAdapter
                    self.mcp_adapter = MCPAdapter()
                    logger.info("MCPアダプタを初期化しました")
                except Exception as e:
                    logger.error(f"MCPアダプタの初期化に失敗しました: {e}")
                    self.mcp_adapter = None
                    self.use_mcp = False
            else:
                logger.warning("MCPモジュールが利用できないため、標準ブラウザモードを使用します")
                self.use_mcp = False
        
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
                    return ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=os.environ.get("GOOGLE_API_KEY"))
                elif model_name == "gpt-4omini":
                    return ChatOpenAI(model="gpt-4omini", api_key=os.environ.get("OPENAI_API_KEY"))
                elif model_name == "claude-sonnet":
                    return ChatAnthropic(model="claude-3-5-sonnet-2024", api_key=os.environ.get("ANTHROPIC_API_KEY"))
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
                
        # ブラウザ機能が無効化されている場合
        if not self.browser and not self.mcp_adapter:
            logger.info(f"ブラウザ機能が無効化されています。URLへの移動をシミュレート: {url}")
            return f"URLに移動しました（シミュレーション）: {url}"
        
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
                
        # ブラウザ機能が無効化されている場合
        if not self.browser and not self.mcp_adapter:
            logger.info(f"ブラウザ機能が無効化されています。クリックをシミュレート: {selector}")
            return f"要素をクリックしました（シミュレーション）: {selector}"
        
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
        
        # ブラウザ機能が無効化されている場合
        if not self.browser and not self.mcp_adapter:
            logger.info(f"ブラウザ機能が無効化されています。テキスト入力をシミュレート: {selector} -> {text}")
            return f"テキストを入力しました（シミュレーション）: {selector} -> {text}"
        
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
        
        # ブラウザ機能が無効化されている場合
        if not self.browser and not self.mcp_adapter:
            logger.info("ブラウザ機能が無効化されています。スクリーンショットをシミュレート")
            return "スクリーンショットを撮影しました（シミュレーション）"
            
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
        
        # ブラウザ機能が無効化されている場合
        if not self.browser and not self.mcp_adapter:
            logger.info(f"ブラウザ機能が無効化されています。テキスト取得をシミュレート: {selector}")
            return f"テキスト（シミュレーション）: 要素 {selector} のテキスト"
            
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
        
        # ブラウザ機能が無効化されている場合
        if not self.browser and not self.mcp_adapter:
            logger.info(f"ブラウザ機能が無効化されています。JavaScript実行をシミュレート: {code[:50]}...")
            return f"JavaScript実行（シミュレーション）: {code[:50]}..."
            
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
        try:
            # ブラウザが初期化されていない場合は初期化
            if not self.browser_initialized:
                success = self.initialize_browser()
                if not success:
                    return False, "ブラウザの初期化に失敗しました。"
                    
            # Google APIキーがない場合
            google_api_key = os.environ.get("GOOGLE_API_KEY")
            if not google_api_key:
                return False, "Google APIキーが設定されていません。AIによるブラウザ操作にはAPIキーが必要です。"
            
            # browser-useライブラリのAIエージェントを使用
            if hasattr(self, 'browser_agent'):
                logger.info(f"AIエージェントを使用してブラウザを操作します: {command_text}")
                
                async def run_browser_agent():
                    try:
                        # AIエージェントにコマンドを実行させる
                        result = await self.browser_agent.run(command_text)
                        return result
                    except Exception as e:
                        logger.error(f"AIエージェント実行エラー: {e}")
                        raise
                
                # 非同期実行
                result = self._run_browser_async(run_browser_agent())
                return True, f"AIによるブラウザ操作結果: {result or '完了しました'}"
                
            # AIエージェントがない場合はLangChainエージェントを使用
            elif self.agent_executor:
                logger.info(f"LangChainエージェントを使用してブラウザを操作します: {command_text}")
                result = self.agent_executor.invoke({"input": command_text})
                return True, result["output"]
                
            else:
                return False, "AIエージェントが設定されていません。AIによるブラウザ操作には、browser-useライブラリまたはLangChainエージェントが必要です。"
                
        except Exception as e:
            logger.error(f"LLMによるブラウザ制御エラー: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, f"ブラウザ制御中にエラーが発生しました: {str(e)}"

    def execute_command(self, command: str) -> bool:
        """
        ユーザーコマンドを実行します。
        
        Args:
            command (str): 実行するコマンド
            
        Returns:
            bool: コマンドが成功したかどうか
        """
        logger.info(f"コマンド実行: {command}")
        
        try:
            # ブラウザ関連コマンドのパターン
            browser_patterns = [
                (re.compile(r"ブラウザ[でに](.+?)を開[いくけ]", re.IGNORECASE), self._navigate_url),
                (re.compile(r"(.+?)を検索", re.IGNORECASE), self._search_google),
                (re.compile(r"YouTube[でに](.+?)を検索", re.IGNORECASE), self._search_youtube),
                (re.compile(r"Gmail.*開[いくけ]", re.IGNORECASE), lambda m, c: self._navigate_url(m, "https://mail.google.com")),
                (re.compile(r"カレンダー.*開[いくけ]", re.IGNORECASE), lambda m, c: self._navigate_url(m, "https://calendar.google.com")),
            ]
            
            # ブラウザコマンドの検出と実行
            for pattern, handler in browser_patterns:
                match = pattern.search(command)
                if match:
                    success, message = handler(match, command)
                    logger.info(f"コマンド実行結果: {message}")
                    return success
            
            # LLMを使用したブラウザ制御
            if "AI" in command and ("ブラウザ" in command or "検索" in command):
                success, message = self._control_with_llm(None, command)
                logger.info(f"LLMによるコマンド実行結果: {message}")
                return success
                
            logger.warning(f"認識できないコマンド: {command}")
            return False
            
        except Exception as e:
            logger.error(f"コマンド実行エラー: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
    def _navigate_url(self, match, command_or_url) -> Tuple[bool, str]:
        """
        URLを開きます。
        
        Args:
            match: 正規表現マッチオブジェクト
            command_or_url: コマンドまたは直接URL
            
        Returns:
            Tuple[bool, str]: 成功したかどうかと、結果メッセージ
        """
        try:
            # URLを抽出
            url = command_or_url
            if isinstance(command_or_url, str) and not command_or_url.startswith(('http://', 'https://')):
                # 直接URLでない場合はマッチオブジェクトからURLを抽出
                if match and match.groups():
                    url = match.group(1).strip()
                else:
                    return False, "URLを抽出できませんでした。"
            
            # URLの整形
            if not url.startswith(('http://', 'https://')):
                if '.' in url:
                    url = 'https://' + url
                else:
                    return False, f"無効なURL: {url}"
            
            # ブラウザが初期化されていない場合は初期化
            if not self.browser_initialized:
                success = self.initialize_browser()
                if not success:
                    return False, "ブラウザの初期化に失敗しました。"
            
            # browser-useライブラリがある場合は使用
            if self.browser and hasattr(self.browser, 'goto'):
                logger.info(f"browser-useを使用してURLを開きます: {url}")
                # 非同期実行
                self._run_browser_async(self.browser.goto(url))
                return True, f"{url} を開きました。"
            else:
                # 標準のwebbrowserモジュールを使用
                logger.info(f"標準ブラウザを使用してURLを開きます: {url}")
                import webbrowser
                webbrowser.open(url)
                return True, f"{url} を開きました。"
                
        except Exception as e:
            logger.error(f"ナビゲーションエラー: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, f"エラー: {str(e)}"
            
    def _search_google(self, match, command) -> Tuple[bool, str]:
        """
        Googleで検索を実行します。
        
        Args:
            match: 正規表現マッチオブジェクト
            command: コマンド全体
            
        Returns:
            Tuple[bool, str]: 成功したかどうかと、結果メッセージ
        """
        try:
            # 検索クエリの抽出
            query = match.group(1).strip() if match and match.groups() else ""
            if not query:
                return False, "検索クエリを抽出できませんでした。"
                
            # 検索URLの生成
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            
            # ブラウザが初期化されていない場合は初期化
            if not self.browser_initialized:
                success = self.initialize_browser()
                if not success:
                    return False, "ブラウザの初期化に失敗しました。"
            
            # browser-useライブラリがある場合は使用
            if self.browser and hasattr(self.browser, 'goto'):
                logger.info(f"browser-useを使用してGoogle検索を実行: {query}")
                # 非同期実行
                self._run_browser_async(self.browser.goto(search_url))
                return True, f"Google検索を実行しました: {query}"
            else:
                # 標準のwebbrowserモジュールを使用
                logger.info(f"標準ブラウザを使用してGoogle検索を実行: {query}")
                import webbrowser
                webbrowser.open(search_url)
                return True, f"Google検索を実行しました: {query}"
            
        except Exception as e:
            logger.error(f"Google検索エラー: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, f"エラー: {str(e)}"
            
    def _search_youtube(self, match, command) -> Tuple[bool, str]:
        """
        YouTubeで検索を実行します。
        
        Args:
            match: 正規表現マッチオブジェクト
            command: コマンド全体
            
        Returns:
            Tuple[bool, str]: 成功したかどうかと、結果メッセージ
        """
        try:
            # 検索クエリの抽出
            query = match.group(1).strip() if match and match.groups() else ""
            if not query:
                return False, "検索クエリを抽出できませんでした。"
                
            # 検索URLの生成
            search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
            
            # ブラウザが初期化されていない場合は初期化
            if not self.browser_initialized:
                success = self.initialize_browser()
                if not success:
                    return False, "ブラウザの初期化に失敗しました。"
            
            # browser-useライブラリがある場合は使用
            if self.browser and hasattr(self.browser, 'goto'):
                logger.info(f"browser-useを使用してYouTube検索を実行: {query}")
                # 非同期実行
                self._run_browser_async(self.browser.goto(search_url))
                return True, f"YouTube検索を実行しました: {query}"
            else:
                # 標準のwebbrowserモジュールを使用
                logger.info(f"標準ブラウザを使用してYouTube検索を実行: {query}")
                import webbrowser
                webbrowser.open(search_url)
                return True, f"YouTube検索を実行しました: {query}"
            
        except Exception as e:
            logger.error(f"YouTube検索エラー: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, f"エラー: {str(e)}"

    def initialize_browser(self):
        """ブラウザインターフェースを初期化"""
        if self.browser_initialized:
            logger.info("ブラウザは既に初期化されています。")
            return True

        try:
            # 環境変数からGoogle APIキーを取得
            google_api_key = os.environ.get("GOOGLE_API_KEY")
            if google_api_key:
                logger.info("Google APIキーが設定されています。Google AIを使用します。")
            else:
                logger.warning("GOOGLE_API_KEY環境変数が設定されていません。基本的なブラウザ機能のみを使用します。")

            # MCPアダプタを使用する場合
            if self.use_mcp:
                self._initialize_mcp_browser()
                return True

            # browser-useライブラリを使用
            logger.info("browser-useライブラリを使用してブラウザを初期化します。")
            
            try:
                # browser-useの主要コンポーネントをインポート
                from browser_use import BrowserManager
                
                # BrowserManagerを初期化
                self.browser_manager = BrowserManager()
                browser_instance = self.browser_manager.create_browser()
                self.browser = browser_instance
                
                # Google AIを使用する場合
                if google_api_key:
                    try:
                        from langchain_google_genai import ChatGoogleGenerativeAI
                        from browser_use import setup_agent
                        
                        # Google Geminiモデルを初期化
                        logger.info("Google Gemini AIモデルを初期化しています...")
                        llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
                        
                        # エージェントをセットアップ
                        self.browser_agent = setup_agent(
                            browser=self.browser,
                            llm=llm,
                            task="ユーザーの指示に従ってWebブラウザを操作します"
                        )
                        logger.info("AIエージェントを使用したブラウザ操作が準備できました")
                    except Exception as e:
                        logger.error(f"AIエージェントの初期化に失敗しました: {e}")
                        logger.info("AIなしでブラウザ操作を続行します")
                
                # ブラウザメソッドを設定
                self.browser_methods = {
                    'navigate': self.browser.goto,
                    'click': self.browser.click,
                    'type': self.browser.type,
                    'screenshot': self.browser.screenshot,
                    'evaluate': self.browser.evaluate,
                    'wait_for_navigation': self.browser.wait_for_navigation,
                    'get_url': self.browser.url
                }
                
                logger.info("ブラウザが正常に初期化されました")
                self.browser_initialized = True
                return True
                
            except ImportError:
                logger.error("browser-useライブラリが見つかりません。標準のブラウザモードを使用します。")
                import webbrowser
                
                # 代替の基本ブラウザ機能としてwebbrowserモジュールを使用
                self.browser = None
                
                # ブラウザメソッドを設定（ダミー関数）
                async def dummy_navigate(url):
                    webbrowser.open(url)
                    return True
                    
                async def dummy_click(selector):
                    logger.info(f"クリックをシミュレート: {selector}")
                    return True
                    
                async def dummy_type(selector, text):
                    logger.info(f"テキスト入力をシミュレート: {selector} -> {text}")
                    return True
                    
                async def dummy_screenshot(path=None):
                    logger.info(f"スクリーンショットをシミュレート: {path}")
                    return path or f"screenshot_{int(time.time())}.png"
                    
                async def dummy_evaluate(code):
                    logger.info(f"JavaScript実行をシミュレート: {code[:50]}...")
                    return None
                    
                async def dummy_wait_for_navigation():
                    logger.info("ナビゲーション待機をシミュレート")
                    return True
                    
                async def dummy_get_url():
                    logger.info("URL取得をシミュレート")
                    return "https://example.com"
                    
                # ブラウザメソッドを設定
                self.browser_methods = {
                    'navigate': dummy_navigate,
                    'click': dummy_click,
                    'type': dummy_type,
                    'screenshot': dummy_screenshot,
                    'evaluate': dummy_evaluate,
                    'wait_for_navigation': dummy_wait_for_navigation,
                    'get_url': dummy_get_url
                }
                
                logger.info("ブラウザが正常に初期化されました（シミュレーションモード）")
                self.browser_initialized = True
                return True
            
        except Exception as e:
            logger.error(f"ブラウザの初期化中にエラーが発生しました: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.browser_initialized = False
            return False
    
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
            # スレッドセーフに非同期処理を実行
            def run_async():
                nonlocal result
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(run_and_return())
                except Exception as e:
                    logger.error(f"非同期実行エラー: {e}")
                finally:
                    loop.close()
            
            # 常に新しいループを作成して実行
            run_async()
            return result
            
        except Exception as e:
            logger.error(f"ブラウザ操作の実行に失敗しました: {e}")
            return None
    
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
                        else:
                            logger.warning("ブラウザの閉じ方がわかりません。")
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
    
    def get_available_browsers(self):
        """
        利用可能なブラウザの一覧を返します。
        
        Returns:
            List[str]: 利用可能なブラウザのリスト
        """
        available_browsers = []
        
        try:
            # システムにインストールされているブラウザを検出
            import webbrowser
            browsers = webbrowser._browsers
            
            if any(b for b in browsers if 'chrome' in b.lower()):
                available_browsers.append('Chrome')
            if any(b for b in browsers if 'firefox' in b.lower()):
                available_browsers.append('Firefox')
            if any(b for b in browsers if 'edge' in b.lower() or 'msie' in b.lower()):
                available_browsers.append('Edge')
            if any(b for b in browsers if 'safari' in b.lower()):
                available_browsers.append('Safari')
            if any(b for b in browsers if 'opera' in b.lower()):
                available_browsers.append('Opera')
            
            # MCP使用時はデフォルトブラウザも追加
            if self.use_mcp and self.mcp_adapter:
                available_browsers.append('MCP Browser')
            
            # ブラウザが検出されなかった場合はデフォルト追加
            if not available_browsers:
                available_browsers = ['Chrome', 'Firefox', 'Edge']
                
            return available_browsers
        except Exception as e:
            logger.error(f"利用可能なブラウザの取得エラー: {e}")
            # エラー時はデフォルト値を返す
            return ['Chrome', 'Firefox', 'Edge']

    def _initialize_mcp_browser(self):
        """
        MCPサーバーを使用してブラウザを初期化します。
        
        Returns:
            bool: 初期化が成功したかどうか
        """
        logger.info("MCPサーバーを使用してブラウザを初期化します...")
        try:
            # MCPサーバーの起動
            if not self.mcp_adapter:
                logger.error("MCPアダプタが初期化されていません。")
                return False
                
            if self.mcp_adapter.start_server():
                # 接続を試行
                if self.mcp_adapter.run_async(self.mcp_adapter.connect()):
                    self.browser_initialized = True
                    logger.info("MCPサーバー経由でブラウザを初期化しました。")
                    return True
                else:
                    logger.error("MCPサーバーへの接続に失敗しました。")
            else:
                logger.error("MCPサーバーの起動に失敗しました。")
                
            return False
        except Exception as e:
            logger.error(f"MCPブラウザの初期化中にエラーが発生しました: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False 
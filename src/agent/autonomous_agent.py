import logging
from typing import Dict, Any, List, Optional, Tuple
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAI
import google.generativeai as genai
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
import yaml
from PIL import Image
import io
import os
from dotenv import load_dotenv
import webbrowser
import subprocess
import pyautogui
import keyboard
import time
from .keyboard_monitor import KeyboardMonitor

class AutonomousAgent:
    def __init__(self, db_logger):
        self.logger = logging.getLogger(__name__)
        self.db_logger = db_logger
        self.keyboard_monitor = KeyboardMonitor()
        
        # 環境変数の読み込み
        load_dotenv()
        
        # 設定ファイルの読み込み
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # AIプロバイダー設定の取得
        ai_providers = config.get('ai_providers', {})
        use_vertexai = ai_providers.get('use_vertexai', True)
        use_openai = ai_providers.get('use_openai', False)
        use_anthropic = ai_providers.get('use_anthropic', False)
        
        # デフォルトのモデル設定
        self.vision_model = None
        self.llm = None
        
        # Gemini Proの初期化（デフォルト）
        if use_vertexai:
            try:
                google_api_key = os.getenv("GOOGLE_API_KEY")
                if google_api_key:
                    genai.configure(api_key=google_api_key)
                    # テキスト用モデル
                    self.llm = ChatGoogleGenerativeAI(model="gemini-pro")
                    # マルチモーダル用モデル
                    self.vision_model = GoogleGenerativeAI(model="gemini-pro-vision")
                    self.logger.info("Google AI (Gemini Pro) モデルを初期化しました")
                else:
                    self.logger.warning("GOOGLE_API_KEYが設定されていません")
            except Exception as e:
                self.logger.error(f"Google AI初期化エラー: {e}")
        
        # OpenAI APIの初期化（オプション）
        if use_openai and (self.llm is None or not use_vertexai):
            try:
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if openai_api_key:
                    # テキスト用モデル（GPT-4をデフォルトに）
                    self.llm = ChatOpenAI(api_key=openai_api_key, model_name="gpt-4")
                    self.logger.info("OpenAI GPT-4モデルを初期化しました")
                else:
                    self.logger.warning("OPENAI_API_KEYが設定されていません")
            except Exception as e:
                self.logger.error(f"OpenAI初期化エラー: {e}")
        
        # Anthropic Claude APIの初期化（オプション）
        if use_anthropic and (self.llm is None or (not use_vertexai and not use_openai)):
            try:
                claude_api_key = os.getenv("CLAUDE_API_KEY")
                if claude_api_key:
                    # Claudeモデル
                    self.llm = ChatAnthropic(api_key=claude_api_key, model_name="claude-3-opus-20240229")
                    self.logger.info("Anthropic Claudeモデルを初期化しました")
                else:
                    self.logger.warning("CLAUDE_API_KEYが設定されていません")
            except Exception as e:
                self.logger.error(f"Anthropic初期化エラー: {e}")
        
        # モデルが初期化されていない場合はエラーログ
        if self.llm is None:
            self.logger.error("有効なAIモデルが初期化されませんでした。APIキーを確認してください。")
            # 出力パーサーの設定だけはしておく
            self.parser = JsonOutputParser()
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", """あなたはデスクトップ操作を支援するAIアシスタントです。
                ユーザーの要求を理解し、適切なコマンドに変換してください。
                
                出力は以下のJSON形式で返してください：
                {
                    "command_type": "BROWSER|FILE|DESKTOP|MOUSE|KEYBOARD|VISION",
                    "parameters": {
                        "action": "実行するアクション",
                        "browser_type": "edge|chrome|browser",
                        "url": "開くURL",
                        "path": "ファイルパス",
                        "window": "ウィンドウ名",
                        "application": "アプリケーション名",
                        "x": "X座標",
                        "y": "Y座標",
                        "clicks": "クリック回数",
                        "button": "left|right|middle",
                        "duration": "操作時間（秒）",
                        "keys": "キー操作シーケンス",
                        "speed": "再生速度",
                        "screenshot": "スクリーンショットの有無",
                        "region": "キャプチャ領域"
                    }
                }
                """),
                ("human", "{input}")
            ])
            # APIキーがない場合はチェーンを構築しない
            self.chain = None
        else:
            # 出力パーサーの設定
            self.parser = JsonOutputParser()
            
            # プロンプトテンプレートの設定
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", """あなたはデスクトップ操作を支援するAIアシスタントです。
                ユーザーの要求を理解し、適切なコマンドに変換してください。
                
                出力は以下のJSON形式で返してください：
                {
                    "command_type": "BROWSER|FILE|DESKTOP|MOUSE|KEYBOARD|VISION",
                    "parameters": {
                        "action": "実行するアクション",
                        "browser_type": "edge|chrome|browser",
                        "url": "開くURL",
                        "path": "ファイルパス",
                        "window": "ウィンドウ名",
                        "application": "アプリケーション名",
                        "x": "X座標",
                        "y": "Y座標",
                        "clicks": "クリック回数",
                        "button": "left|right|middle",
                        "duration": "操作時間（秒）",
                        "keys": "キー操作シーケンス",
                        "speed": "再生速度",
                        "screenshot": "スクリーンショットの有無",
                        "region": "キャプチャ領域"
                    }
                }
                """),
                ("human", "{input}")
            ])
            
            # チェーンの構築
            self.chain = self.prompt | self.llm | self.parser
        
        # ブラウザパスの設定
        self.browser_paths = {
            'edge': r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
            'chrome': r'C:\Program Files\Google\Chrome\Application\chrome.exe'
        }
        
        # マウス操作の安全性確保
        pyautogui.FAILSAFE = True  # 画面端に移動でプログラム停止
        pyautogui.PAUSE = 0.5  # 操作間の待機時間
        
        # キーボードモニターの開始
        self.keyboard_monitor.start()
    
    def execute_command(self, command_type: str, params: Dict[str, Any]) -> bool:
        """コマンドを実行し、結果をログに記録"""
        try:
            # コマンド実行の開始をログに記録
            self.db_logger.log_operation(
                operation_type=command_type,
                details=f"コマンド実行開始: {params}",
                status="RUNNING"
            )
            
            # コマンドタイプに応じた処理を実行
            success = False
            if command_type == "BROWSER":
                success = self._handle_browser_command(params)
            elif command_type == "FILE":
                success = self._handle_file_command(params)
            elif command_type == "DESKTOP":
                success = self._handle_desktop_command(params)
            elif command_type == "MOUSE":
                success = self._handle_mouse_command(params)
            elif command_type == "KEYBOARD":
                success = self._handle_keyboard_command(params)
            elif command_type == "VISION":
                success = self._handle_vision_command(params)
            else:
                self.logger.warning(f"不明なコマンドタイプ: {command_type}")
                
            # 実行結果をログに記録
            self.db_logger.log_operation(
                operation_type=command_type,
                details=f"コマンド実行完了: {params}",
                status="SUCCESS" if success else "FAILURE"
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"コマンド実行エラー: {e}")
            
            # エラーをログに記録
            self.db_logger.log_operation(
                operation_type=command_type,
                details=f"コマンド実行エラー: {params}, {str(e)}",
                status="FAILURE",
                error_message=str(e)
            )
            
            return False
    
    def process_natural_language(self, text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        自然言語のテキストを処理し、コマンドタイプとパラメータを生成
        
        Args:
            text (str): 処理する自然言語テキスト
            
        Returns:
            Optional[Tuple[str, Dict[str, Any]]]: コマンドタイプとパラメータ、または解析できない場合はNone
        """
        try:
            # LLMチェーンが利用可能な場合は自然言語処理を実行
            if self.chain is not None:
                result = self.chain.invoke({"input": text})
                command_type = result.get("command_type")
                parameters = result.get("parameters", {})
                
                if command_type:
                    return command_type, parameters
                
            # LLMが利用できない場合は、CommandInterpreterを使用
            result = self.command_interpreter.interpret(text)
            if result:
                return result
                
            self.logger.warning(f"自然言語を解析できませんでした: {text}")
            return None
            
        except Exception as e:
            self.logger.error(f"自然言語処理エラー: {e}")
            return None
    
    def _handle_browser_command(self, params: Dict[str, Any]) -> bool:
        """ブラウザ操作コマンドの処理"""
        try:
            browser_type = params.get("browser_type", "browser")
            url = params.get("url")
            if not url:
                return False
                
            return self._open_browser(browser_type, url)
        except Exception as e:
            self.logger.error(f"ブラウザ操作エラー: {e}")
            return False
    
    def _handle_file_command(self, params: Dict[str, Any]) -> bool:
        """ファイル操作コマンドの処理"""
        try:
            import shutil
            from pathlib import Path
            
            action = params.get("action")
            path = params.get("path")
            if not action or not path:
                return False
                
            if action == "mkdir":
                Path(path).mkdir(parents=True, exist_ok=True)
                return True
            elif action == "move":
                source = params.get("source")
                destination = params.get("destination")
                if not source or not destination:
                    return False
                shutil.move(source, destination)
                return True
            elif action == "delete":
                path_obj = Path(path)
                if path_obj.is_file():
                    path_obj.unlink()
                elif path_obj.is_dir():
                    shutil.rmtree(path_obj)
                return True
            return False
        except Exception as e:
            self.logger.error(f"ファイル操作エラー: {e}")
            return False
    
    def _handle_desktop_command(self, params: Dict[str, Any]) -> bool:
        """デスクトップ操作コマンドの処理"""
        try:
            action = params.get("action")
            if not action:
                return False
                
            if action == "minimize":
                window = params.get("window")
                if not window:
                    return False
                # TODO: ウィンドウの最小化処理を実装
                return True
            elif action == "launch":
                app = params.get("application")
                if not app:
                    return False
                subprocess.Popen(app)
                return True
            return False
        except Exception as e:
            self.logger.error(f"デスクトップ操作エラー: {e}")
            return False
    
    def _handle_mouse_command(self, params: Dict[str, Any]) -> bool:
        """マウス操作コマンドの処理"""
        try:
            action = params.get("action")
            if not action:
                return False
            
            if action == "move":
                # 座標移動
                x = params.get("x")
                y = params.get("y")
                duration = float(params.get("duration", 0.5))
                if x is not None and y is not None:
                    pyautogui.moveTo(x, y, duration=duration)
                    return True
                    
            elif action == "click":
                # クリック
                button = params.get("button", "left")
                clicks = int(params.get("clicks", 1))
                x = params.get("x")
                y = params.get("y")
                
                if x is not None and y is not None:
                    pyautogui.click(x, y, clicks=clicks, button=button)
                else:
                    pyautogui.click(clicks=clicks, button=button)
                return True
                
            elif action == "drag":
                # ドラッグ
                start_x = params.get("start_x")
                start_y = params.get("start_y")
                end_x = params.get("end_x")
                end_y = params.get("end_y")
                duration = float(params.get("duration", 0.5))
                
                if all(v is not None for v in [start_x, start_y, end_x, end_y]):
                    pyautogui.moveTo(start_x, start_y)
                    pyautogui.dragTo(end_x, end_y, duration=duration)
                    return True
                    
            elif action == "scroll":
                # スクロール
                amount = int(params.get("amount", 0))
                pyautogui.scroll(amount)
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"マウス操作エラー: {e}")
            return False
    
    def _handle_keyboard_command(self, params: Dict[str, Any]) -> bool:
        """キーボード操作コマンドの処理"""
        try:
            action = params.get("action")
            if not action:
                return False
            
            if action == "record":
                # キー操作の記録を開始
                self.keyboard_monitor.start_recording()
                return True
                
            elif action == "stop":
                # キー操作の記録を停止
                events = self.keyboard_monitor.stop_recording()
                self.logger.info(f"記録したキー操作: {self.keyboard_monitor.get_key_sequence()}")
                return True
                
            elif action == "replay":
                # 記録したキー操作を再生
                events = params.get("events", [])
                speed = float(params.get("speed", 1.0))
                if events:
                    self.keyboard_monitor.replay_events(events, speed)
                    return True
                    
            elif action == "type":
                # テキストを入力
                text = params.get("text")
                if text:
                    keyboard.write(text)
                    return True
                    
            elif action == "hotkey":
                # ホットキーを実行
                keys = params.get("keys", "").split("+")
                if keys:
                    keyboard.press_and_release("+".join(keys))
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"キーボード操作エラー: {e}")
            return False
    
    def _handle_vision_command(self, params: Dict[str, Any]) -> bool:
        """画像認識コマンドの処理"""
        try:
            action = params.get("action")
            if not action:
                return False
            
            if action == "analyze":
                # スクリーンショットを取得
                if params.get("region"):
                    x1, y1, x2, y2 = params["region"]
                    screenshot = pyautogui.screenshot(region=(x1, y1, x2-x1, y2-y1))
                else:
                    screenshot = pyautogui.screenshot()
                
                # PILイメージをバイトストリームに変換
                img_byte_arr = io.BytesIO()
                screenshot.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                # Geminiで画像を分析
                response = self.vision_model.generate_content([
                    "画面の内容を分析して、何が表示されているか説明してください。",
                    img_byte_arr
                ])
                
                self.logger.info(f"画像分析結果: {response.text}")
                return True

            elif action == "analyze_video":
                # 動画ファイルを読み込み
                video_path = params.get("video_path")
                if not video_path:
                    return False

                import cv2
                cap = cv2.VideoCapture(video_path)
                frames = []
                
                # 1秒ごとにフレームを抽出
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_interval = int(fps)
                frame_count = 0
                
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    if frame_count % frame_interval == 0:
                        # OpenCV形式からPIL形式に変換
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frame_pil = Image.fromarray(frame_rgb)
                        
                        # フレームをバイトストリームに変換
                        frame_byte_arr = io.BytesIO()
                        frame_pil.save(frame_byte_arr, format='PNG')
                        frames.append(frame_byte_arr.getvalue())
                        
                    frame_count += 1
                    
                cap.release()
                
                # Geminiで動画を分析
                response = self.vision_model.generate_content([
                    "この動画の内容を時系列で説明してください。",
                    *frames
                ])
                
                self.logger.info(f"動画分析結果: {response.text}")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"画像認識エラー: {e}")
            return False
    
    def _open_browser(self, browser_type: str, url: str) -> bool:
        """指定されたブラウザでURLを開く"""
        try:
            if browser_type == 'browser':
                # デフォルトブラウザで開く
                webbrowser.open(url)
                return True
            
            browser_path = self.browser_paths.get(browser_type)
            if not browser_path:
                self.logger.error(f"未サポートのブラウザ: {browser_type}")
                return False
            
            # 指定されたブラウザで開く
            subprocess.Popen([browser_path, url])
            self.logger.info(f"{browser_type}で{url}を開きました")
            return True
            
        except Exception as e:
            self.logger.error(f"ブラウザ起動エラー: {e}")
            return False
    
    def cleanup(self):
        """リソースのクリーンアップ"""
        try:
            self.keyboard_monitor.stop()
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}") 
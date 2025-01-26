#!/usr/bin/env python
# coding: utf-8

"""
このファイルは、以下を一つにまとめたデモです:
1. デスクトップ操作(DesktopController) と Edgeブラウザ操作(EdgeController)
2. LangChainのエージェント (Tool/Agent/Memory) でユーザーの自然言語指示を処理
3. PyQt GUI でユーザー入力を受けて、エージェント実行 → 結果表示
4. LLM部分を OpenAI ではなく Google Generative AI (PaLM/Vertex AI) に切り替え
   => langchain.chat_models.ChatGooglePalm を使用

前提:
 - pip install langchain google-generativeai
 - 環境変数 GOOGLE_API_KEY または google_generativeai.configure(api_key=...) 等でAPIキーを設定
 - Windows向け: pywin32, pyautogui, seleniumなどインストール & EdgeWebDriver
 - Python 3.8+

実行:
   python advanced_langchain_with_google.py
"""

import sys
import os
import logging
import re
import time
import requests
from typing import Optional, List, Dict, Any, Union
from dotenv import load_dotenv

# PyQt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QMessageBox
)
from PyQt5.QtCore import QThread, pyqtSignal, QObject, QMetaObject, Qt, QEvent, QEventLoop, QTimer, QMutex, QWaitCondition, Q_ARG, pyqtSlot

# Windows特有の操作
import pyautogui
import pygetwindow as gw
import win32gui
import win32con

# Selenium (Edge)
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.common.exceptions import WebDriverException

# LangChain
from langchain.agents import Tool, AgentExecutor, BaseSingleActionAgent
from langchain_core.agents import AgentAction, AgentFinish, AgentOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.memory import ConversationBufferMemory

# Google Generative AI
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

# プロンプトテンプレートの定義
CUSTOM_PROMPT = """あなたはマルチツール対応のエージェントです。
以下のツールを使用できます:
{tool_descriptions}

会話履歴:
{history}

ユーザー入力:
{input}

出力形式:
Action: <tool名>
Action Input: <引数>
または
Final Answer: <最終回答>

注意：
- URLは完全な形式で指定してください
- DeepSeekのURLは https://chat.deepseek.com/ です
- 必ずAction/Action Inputの形式で応答してください
- 'navigate'ツールを使用してURLを開いてください
"""

##############################################
# 1) DesktopController / EdgeController
##############################################
class DesktopController:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        self.is_active = False

    def start(self):
        self.is_active = True
        self.logger.info("DesktopController started")

    def stop(self):
        self.is_active = False
        self.logger.info("DesktopController stopped")

    def move_mouse(self, x: int, y: int, duration: float = 0.5) -> bool:
        if not self.is_active:
            return False
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return True
        except Exception as e:
            self.logger.error(f"move_mouse error: {e}")
            return False

    def type_text(self, text: str) -> bool:
        if not self.is_active:
            return False
        try:
            pyautogui.typewrite(text, interval=0.1)
            return True
        except Exception as e:
            self.logger.error(f"type_text error: {e}")
            return False

    def press_key(self, key: str) -> bool:
        if not self.is_active:
            return False
        try:
            pyautogui.press(key)
            return True
        except Exception as e:
            self.logger.error(f"press_key error: {e}")
            return False


class EdgeController:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.driver = None
        self.initialized = False

    def initialize(self) -> bool:
        try:
            options = Options()
            headless_mode = os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
            if headless_mode:
                options.add_argument("--headless")
            
            # GPU関連のエラーを回避するオプションを追加
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-gpu-sandbox")
            options.add_argument("--disable-software-rasterizer")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")
            options.add_argument("--ignore-gpu-blocklist")
            options.add_argument("--disable-gpu-compositing")
            options.add_argument("--disable-accelerated-2d-canvas")
            options.add_argument("--disable-webgl")
            options.add_argument("--inprivate")
            
            # 追加のオプション
            options.add_argument("--disable-features=msEdgeUserTopicOnUrl")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--disable-notifications")
            
            self.driver = webdriver.Edge(options=options)
            self.driver.implicitly_wait(10)
            self.initialized = True
            self.logger.info("EdgeController initialized")
            return True
        except WebDriverException as e:
            self.logger.error(f"Edge init failed: {e}")
            return False

    def cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("EdgeController cleaned up")
            except Exception as e:
                self.logger.error(f"Edge cleanup error: {e}")

    def navigate(self, url: str) -> bool:
        if not self.initialized or not self.driver:
            return False
        try:
            self.driver.get(url)
            self.logger.info(f"Navigated to: {url}")
            return True
        except WebDriverException as e:
            self.logger.error(f"navigate error: {e}")
            return False


##############################################
# 2) コントローラインスタンス + 簡単な確認関数
##############################################
desktop = DesktopController()
edge = EdgeController()

class DialogHelper(QObject):
    def __init__(self, message):
        super().__init__()
        self.message = message
        self.result = False
        self.event_loop = QEventLoop()

    @pyqtSlot()
    def show_dialog(self):
        try:
            box = QMessageBox()
            box.setWindowTitle("確認")
            box.setText(self.message)
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            ret = box.exec_()
            self.result = ret == QMessageBox.Yes
        finally:
            self.event_loop.quit()

def user_confirmation(msg: str) -> bool:
    if QThread.currentThread() is QApplication.instance().thread():
        # メインスレッドの場合は直接表示
        box = QMessageBox()
        box.setWindowTitle("確認")
        box.setText(msg)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        ret = box.exec_()
        return ret == QMessageBox.Yes
    else:
        # 別スレッドの場合はメインスレッドで表示
        helper = DialogHelper(msg)
        helper.moveToThread(QApplication.instance().thread())  # メインスレッドに移動
        QMetaObject.invokeMethod(helper, 
                               "show_dialog",
                               Qt.ConnectionType.QueuedConnection)
        helper.event_loop.exec_()
        return helper.result


##############################################
# 3) LangChainのTool定義
##############################################
def navigate_tool(url: str) -> str:
    logging.info(f"[Tool] navigate_tool: {url}")
    try:
        if not edge.initialized:
            if not edge.initialize():
                return "Failed to initialize Edge browser."
        
        if not user_confirmation(f"ブラウザで {url} に移動します。よろしいですか？"):
            return "Cancelled by user."
            
        ok = edge.navigate(url)
        return "Success" if ok else "Failed"
    except Exception as e:
        logging.error(f"Navigation error: {e}")
        return f"Error: {str(e)}"

NAVIGATE_TOOL = Tool(
    name="navigate",
    func=navigate_tool,
    description="ブラウザで指定URLに移動する。DeepSeekの場合は https://chat.deepseek.com/ を使用"
)

def type_text_tool(text: str) -> str:
    logging.info(f"[Tool] type_text_tool: {text}")
    if not user_confirmation(f"テキスト [{text}] を入力します。よろしいですか？"):
        return "Cancelled."
    ok = desktop.type_text(text)
    return "Success" if ok else "Failed"

TYPE_TEXT_TOOL = Tool(
    name="type_text",
    func=type_text_tool,
    description="デスクトップに文字入力する。Input=string"
)

def press_key_tool(key: str) -> str:
    logging.info(f"[Tool] press_key_tool: {key}")
    if not user_confirmation(f"キー [{key}] を押します。よろしいですか？"):
        return "Cancelled."
    ok = desktop.press_key(key)
    return "Success" if ok else "Failed"

PRESS_KEY_TOOL = Tool(
    name="press_key",
    func=press_key_tool,
    description="指定のキーを押す。Input=string(key name)"
)

def move_mouse_tool(params: str) -> str:
    logging.info(f"[Tool] move_mouse_tool: {params}")
    try:
        s = params.split(",")
        x = int(s[0].split("=")[1])
        y = int(s[1].split("=")[1])
    except:
        return "Param error. Use x=100,y=200"
    if not user_confirmation(f"マウスを({x},{y})に移動します。よろしいですか？"):
        return "Cancelled."
    ok = desktop.move_mouse(x, y)
    return "Success" if ok else "Failed"

MOVE_MOUSE_TOOL = Tool(
    name="move_mouse",
    func=move_mouse_tool,
    description="マウスを指定座標に移動。Input='x=100,y=200'"
)

TOOLS = [
    NAVIGATE_TOOL,
    TYPE_TEXT_TOOL,
    PRESS_KEY_TOOL,
    MOVE_MOUSE_TOOL
]

##############################################
# 4) カスタムPrompt & OutputParser & Agent
##############################################
class CustomOutputParser(AgentOutputParser):
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        if isinstance(text, AIMessage):
            text = text.content
        elif isinstance(text, dict) and "text" in text:
            text = text["text"]
        elif not isinstance(text, str):
            text = str(text)

        if "Final Answer:" in text:
            ans = text.split("Final Answer:")[1].strip()
            return AgentFinish(return_values={"output": ans}, log=text)
        elif "Action:" in text:
            action_match = re.search(r"Action:\s*(.*?)(?:\n|$)", text)
            input_match = re.search(r"Action Input:\s*(.*?)(?:\n|$)", text)
            
            if not action_match or not input_match:
                return AgentFinish(return_values={"output": text}, log=text)
            
            action = action_match.group(1).strip()
            action_input = input_match.group(1).strip()
            return AgentAction(tool=action, tool_input=action_input, log=text)
        else:
            return AgentFinish(return_values={"output": text}, log=text)

class CustomAgent(BaseSingleActionAgent):
    """カスタムエージェントの実装"""
    llm_chain: Any
    output_parser: CustomOutputParser
    allowed_tools: List[str]

    def __init__(self, llm_chain: Any, output_parser: CustomOutputParser, allowed_tools: List[str]):
        super().__init__()
        self.llm_chain = llm_chain
        self.output_parser = output_parser
        self.allowed_tools = allowed_tools

    @property
    def input_keys(self) -> List[str]:
        return ["history", "input", "tool_descriptions"]

    def plan(self, intermediate_steps: List[tuple[AgentAction, str]], **kwargs) -> Union[AgentAction, AgentFinish]:
        try:
            if intermediate_steps:
                steps_info = "\n".join([f"Action: {step[0].tool}\nAction Input: {step[0].tool_input}\nObservation: {step[1]}" 
                                      for step in intermediate_steps])
                kwargs["input"] = f"{kwargs.get('input', '')}\n\n前回までの実行ステップ:\n{steps_info}"

            prompt_output = self.llm_chain.invoke(kwargs)
            return self.output_parser.parse(prompt_output)
        except Exception as e:
            logging.error(f"Agent plan error: {e}")
            return AgentFinish(return_values={"output": f"エラーが発生しました: {str(e)}"}, log=str(e))

##############################################
# 5) CallbackHandler (オプション: ログのみ)
##############################################
class StepCallbackHandler(BaseCallbackHandler):
    def on_tool_start(self, tool, input, **kwargs):
        logging.info(f"[Callback] Tool Start: {tool.name}, input={input}")

    def on_tool_end(self, output, **kwargs):
        logging.info(f"[Callback] Tool End. output={output}")

    def on_llm_start(self, serialized, prompts, **kwargs):
        logging.info(f"[Callback] LLM Start. prompts={prompts}")

    def on_llm_end(self, response, **kwargs):
        logging.info(f"[Callback] LLM End. response={response}")


##############################################
# 6) PyQt GUI
##############################################
class AgentThread(QThread):
    result_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, agent_executor, user_input):
        super().__init__()
        self.agent_executor = agent_executor
        self.user_input = user_input
        self.is_running = False

    def run(self):
        self.is_running = True
        try:
            result = self.agent_executor.invoke(
                {
                    "input": self.user_input,
                    "tool_descriptions": "\n".join([f"{t.name}: {t.description}" for t in TOOLS])
                }
            )
            if self.is_running:
                if isinstance(result, dict):
                    output = result.get("output", "")
                    if isinstance(output, dict):
                        output = output.get("output", str(output))
                else:
                    output = str(result)
                self.result_signal.emit(output)
        except Exception as e:
            if self.is_running:
                self.error_signal.emit(str(e))
                logging.error(f"Agent execution error: {e}")
        finally:
            self.is_running = False
            self.finished_signal.emit()

    def stop(self):
        self.is_running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LangChain + Google Generative AI Demo")
        self.resize(800, 600)

        # 中央ウィジェットの設定
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # レイアウトの設定
        layout = QVBoxLayout(self.central_widget)

        self.label_info = QLabel("プロンプトを入力してください:")
        layout.addWidget(self.label_info)

        self.input_line = QLineEdit()
        layout.addWidget(self.input_line)

        self.run_button = QPushButton("エージェントに送信")
        self.run_button.clicked.connect(self.on_run)
        layout.addWidget(self.run_button)

        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        layout.addWidget(self.output_area)

        # デスクトップ/Edge 初期化
        if not edge.initialize():
            QMessageBox.warning(self, "警告", "Edgeブラウザの初期化に失敗しました。")
        desktop.start()

        # 環境変数の読み込み
        load_dotenv()

        # Google APIキーを.envファイルから取得
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            QMessageBox.critical(self, "エラー", ".envファイルにGOOGLE_API_KEYが設定されていません")
            sys.exit(1)

        # Gemini設定
        genai.configure(api_key=api_key)

        # LLMをGeminiに設定
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0.2,
            google_api_key=api_key,
            convert_system_message_to_human=True
        )

        # メモリ
        self.memory = ConversationBufferMemory(
            return_messages=True,
            output_key="output",
            input_key="input"
        )
        
        # プロンプト
        self.prompt = PromptTemplate(
            template=CUSTOM_PROMPT,
            input_variables=["tool_descriptions", "history", "input"]
        )
        
        # チェーンの構築
        self.llm_chain = (
            {
                "input": RunnablePassthrough(),
                "history": lambda x: self.memory.load_memory_variables({})["history"],
                "tool_descriptions": lambda x: "\n".join([f"{t.name}: {t.description}" for t in TOOLS])
            }
            | self.prompt
            | self.llm
        )

        # エージェント構築
        self.output_parser = CustomOutputParser()
        self.agent = CustomAgent(
            llm_chain=self.llm_chain,
            output_parser=self.output_parser,
            allowed_tools=[t.name for t in TOOLS]
        )

        # エージェントエグゼキューターの設定
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=TOOLS,
            verbose=True,
            memory=self.memory,
            max_iterations=5,
            return_intermediate_steps=True,
            handle_parsing_errors=True
        )

        self.agent_thread = None

    def on_run(self):
        user_text = self.input_line.text().strip()
        if not user_text:
            return

        self.output_area.append(f">> User: {user_text}")
        self.run_button.setEnabled(False)
        self.input_line.setEnabled(False)  # 入力を無効化

        # 既存のスレッドを停止
        if self.agent_thread and self.agent_thread.isRunning():
            self.agent_thread.stop()
            self.agent_thread.wait()

        # 新しいスレッドを作成
        self.agent_thread = AgentThread(self.agent_executor, user_text)
        self.agent_thread.result_signal.connect(self.on_agent_result)
        self.agent_thread.error_signal.connect(self.on_agent_error)
        self.agent_thread.finished_signal.connect(self.on_agent_finished)
        self.agent_thread.start()

    def on_agent_result(self, result):
        self.output_area.append(f"[Agent Output]: {result}\n")

    def on_agent_error(self, error):
        self.output_area.append(f"[Agent Error]: {error}\n")

    def on_agent_finished(self):
        self.run_button.setEnabled(True)
        self.input_line.setEnabled(True)  # 入力を再度有効化

    def closeEvent(self, event):
        if self.agent_thread and self.agent_thread.isRunning():
            self.agent_thread.stop()
            self.agent_thread.wait()
        desktop.stop()
        edge.cleanup()
        super().closeEvent(event)


def main():
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
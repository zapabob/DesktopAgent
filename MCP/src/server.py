#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MCPサーバー - モデルとブラウザの連携を提供するサーバー
"""

import os
import sys
import asyncio
import signal
import logging
import json
import time
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 内部モジュールのインポート
try:
    from models.model_manager import ModelManager
except ImportError:
    # デモ用のダミークラス
    class ModelManager:
        def __init__(self):
            self.initialized = False
        
        async def initialize(self):
            self.initialized = True
            return True
            
        async def generate(self, *args, **kwargs):
            return "モデルが初期化されていません"
            
        async def generate_with_image(self, *args, **kwargs):
            return "モデルが初期化されていません"

try:
    from browser.browser_controller import BrowserController, BROWSER_USE_AVAILABLE
except ImportError:
    # デモ用のダミークラス
    class BrowserController:
        def __init__(self):
            self.initialized = False
        
        async def initialize(self):
            self.initialized = True
            return True
            
        async def execute_action(self, *args, **kwargs):
            return "ブラウザコントローラーが初期化されていません"
            
        async def cleanup(self):
            return True
    
    BROWSER_USE_AVAILABLE = False

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mcp_server.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("mcp_server")

# データモデル
class MessageContent(BaseModel):
    type: str = "text"  # text, image, tool_call, tool_result
    text: Optional[str] = None
    image_url: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Any] = None

class Message(BaseModel):
    role: str  # user, assistant, system, tool
    content: Union[str, List[MessageContent], None] = None
    name: Optional[str] = None
    
class GenerationRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.95
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    
class BrowserRequest(BaseModel):
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)
    
class ServerStatusResponse(BaseModel):
    status: str
    version: str
    uptime: float
    models: Dict[str, Any]
    browser: Dict[str, Any]

# アプリケーションの作成
app = FastAPI(
    title="MCP Server",
    description="Model Context Protocol Server - 大規模言語モデルとブラウザの連携サービス",
    version="0.1.0"
)

# CORSミドルウェアの追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限すること
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 環境変数の読み込み
script_dir = Path(__file__).parent
project_root = script_dir.parent
env_path = project_root / '.env'

if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # デフォルトの.envを探す

# グローバル変数
model_manager = ModelManager()
browser_controller = BrowserController()
start_time = time.time()
server_version = "0.1.0"

# スタートアップイベント
@app.on_event("startup")
async def startup_event():
    logger.info("MCPサーバーを起動中...")
    
    # モデルマネージャーの初期化
    try:
        await model_manager.initialize()
        logger.info("モデルマネージャーを初期化しました")
    except Exception as e:
        logger.error(f"モデルマネージャーの初期化に失敗しました: {e}")
    
    # ブラウザコントローラーの初期化
    try:
        await browser_controller.initialize()
        logger.info("ブラウザコントローラーを初期化しました")
    except Exception as e:
        logger.error(f"ブラウザコントローラーの初期化に失敗しました: {e}")
    
    logger.info("MCPサーバーの起動が完了しました")

# シャットダウンイベント
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("MCPサーバーをシャットダウン中...")
    
    # ブラウザコントローラーのクリーンアップ
    try:
        await browser_controller.cleanup()
        logger.info("ブラウザコントローラーをクリーンアップしました")
    except Exception as e:
        logger.error(f"ブラウザコントローラーのクリーンアップに失敗しました: {e}")
    
    logger.info("MCPサーバーのシャットダウンが完了しました")

# ヘルスチェックエンドポイント
@app.get("/health")
async def health_check():
    """サーバーの健全性を確認するエンドポイント"""
    return {"status": "healthy", "message": "サーバーは正常に動作しています"}

# サーバーステータスエンドポイント
@app.get("/status", response_model=ServerStatusResponse)
async def get_status():
    # モデル情報の取得
    model_info = {}
    try:
        if hasattr(model_manager, "list_models"):
            model_info["available_models"] = await model_manager.list_models()
        else:
            model_info["available_models"] = []
            
        model_info["initialized"] = getattr(model_manager, "initialized", False)
        
        if hasattr(model_manager, "get_usage"):
            model_info["usage"] = await model_manager.get_usage()
        else:
            model_info["usage"] = {}
    except Exception as e:
        logger.error(f"モデル情報の取得に失敗しました: {e}")
        model_info["error"] = str(e)
    
    # ブラウザ情報の取得
    browser_info = {}
    try:
        browser_info["available"] = BROWSER_USE_AVAILABLE
        browser_info["initialized"] = getattr(browser_controller, "initialized", False)
        
        if hasattr(browser_controller, "get_active_browsers"):
            browser_info["active_sessions"] = browser_controller.get_active_browsers()
        else:
            browser_info["active_sessions"] = []
    except Exception as e:
        logger.error(f"ブラウザ情報の取得に失敗しました: {e}")
        browser_info["error"] = str(e)
    
    return {
        "status": "running",
        "version": server_version,
        "uptime": time.time() - start_time,
        "models": model_info,
        "browser": browser_info
    }

# テキスト生成エンドポイント
@app.post("/generate")
async def generate(request: GenerationRequest):
    if not getattr(model_manager, "initialized", False):
        try:
            await model_manager.initialize()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"モデルマネージャーの初期化に失敗しました: {e}")
    
    try:
        # ストリーミングモードが有効な場合の処理
        if request.stream:
            return Response(
                content=streaming_generator(request),
                media_type="text/event-stream"
            )
        
        # 通常の生成モード
        messages = request.messages
        model = request.model
        params = {
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "tools": request.tools,
            "tool_choice": request.tool_choice
        }
        
        # メッセージをAPIが期待する形式に変換
        formatted_messages = []
        for msg in messages:
            if isinstance(msg.content, list):
                # コンテンツが複数の要素を持つ場合
                formatted_content = []
                for item in msg.content:
                    if item.type == "text":
                        formatted_content.append({"type": "text", "text": item.text})
                    elif item.type == "image":
                        formatted_content.append({"type": "image", "image_url": item.image_url})
                    elif item.type == "tool_call":
                        formatted_content.append({
                            "type": "tool_call",
                            "tool_call": {
                                "name": item.tool_name,
                                "arguments": item.tool_args
                            }
                        })
                    elif item.type == "tool_result":
                        formatted_content.append({
                            "type": "tool_result",
                            "tool_result": item.tool_result
                        })
                formatted_msg = {"role": msg.role, "content": formatted_content}
            else:
                # 単一のテキストコンテンツの場合
                formatted_msg = {"role": msg.role, "content": msg.content}
                
            if msg.name:
                formatted_msg["name"] = msg.name
                
            formatted_messages.append(formatted_msg)
        
        # イメージがあるかどうかをチェック
        has_image = any(
            isinstance(msg.content, list) and 
            any(item.type == "image" for item in msg.content)
            for msg in messages
        )
        
        if has_image:
            # 画像付きのリクエスト
            response = await model_manager.generate_with_image(
                formatted_messages, model=model, **params
            )
        else:
            # テキストのみのリクエスト
            response = await model_manager.generate(
                formatted_messages, model=model, **params
            )
        
        return response
    except Exception as e:
        logger.error(f"テキスト生成エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ストリーミングジェネレーター
async def streaming_generator(request: GenerationRequest):
    try:
        # TODO: 実装予定
        yield "data: " + json.dumps({"text": "ストリーミングはまだサポートされていません"}) + "\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"ストリーミングエラー: {e}")
        yield f"data: " + json.dumps({"error": str(e)}) + "\n\n"
        yield "data: [DONE]\n\n"

# ブラウザコントロールエンドポイント
@app.post("/browser")
async def browser_control(request: BrowserRequest):
    if not BROWSER_USE_AVAILABLE:
        raise HTTPException(status_code=400, detail="browser-useパッケージが利用できません")
    
    if not getattr(browser_controller, "initialized", False):
        try:
            await browser_controller.initialize()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"ブラウザコントローラーの初期化に失敗しました: {e}")
    
    try:
        result = await browser_controller.execute_action(
            action=request.action,
            **request.params
        )
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"ブラウザ制御エラー ({request.action}): {e}")
        raise HTTPException(status_code=500, detail=str(e))

# シャットダウンエンドポイント
@app.post("/shutdown")
async def shutdown():
    """サーバーを安全に停止するエンドポイント"""
    logger.info("シャットダウンリクエストを受信しました")
    # 非同期でサーバーを停止
    asyncio.create_task(shutdown_server())
    return {"status": "success", "message": "サーバーをシャットダウンしています"}

async def shutdown_server():
    """サーバーを安全に停止する"""
    logger.info("サーバーリソースをクリーンアップしています...")
    
    # ブラウザコントローラーのクリーンアップ
    if browser_controller:
        await browser_controller.shutdown()
    
    # モデルマネージャーのクリーンアップ
    if model_manager:
        await model_manager.shutdown()
    
    # 少し待機してからプロセスを終了
    await asyncio.sleep(1)
    logger.info("サーバーを停止します")
    os.kill(os.getpid(), signal.SIGTERM)

# シグナルハンドラ
def signal_handler(sig, frame):
    """シグナルを受け取った時の処理"""
    logger.info(f"シグナル {sig} を受信しました。アプリケーションを終了します。")
    # asyncio.run(shutdown_server()) # これはイベントループ内からの呼び出しでエラーになる
    
    # 現在のイベントループを取得して、そこにタスクをスケジュール
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # イベントループが実行中の場合は、タスクとしてシャットダウン処理を追加
        loop.create_task(shutdown_server())
    else:
        # イベントループが実行中でない場合（通常はここには来ない）
        asyncio.run(shutdown_server())

# 主要なシグナルをキャッチ
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# サーバー起動
def start_server():
    """UvicornでFastAPIサーバーを起動"""
    host = os.environ.get("MCP_HOST", "localhost")
    port = int(os.environ.get("MCP_PORT", 8765))
    
    logger.info(f"MCPサーバーを起動しています: {host}:{port}")
    
    # 環境変数で指定されている場合はリロードを有効化
    reload = os.environ.get("MCP_RELOAD", "").lower() == "true"
    
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

if __name__ == "__main__":
    start_server() 
import os
import asyncio
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
app = FastAPI(title="MCP Server", description="Model Context Protocol Server", version="0.1.0")

# CORSミドルウェアの追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では特定のオリジンに制限すべき
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {"status": "ok"}

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

# メインエントリーポイント
if __name__ == "__main__":
    # 環境変数から設定を取得
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("MCP_PORT", 8000))
    
    # サーバー起動
    uvicorn.run("server:app", host=host, port=port, reload=True) 
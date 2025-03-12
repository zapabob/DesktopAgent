from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import logging
import sys
import os
import json
from dotenv import load_dotenv

# プロジェクトのルートディレクトリをPYTHONPATHに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 他のモジュールをインポート
from src.models.model_manager import ModelManager
from src.broker.message_broker import MessageBroker
from src.browser.browser_controller import BrowserController
from src.scheduler.task_scheduler import TaskScheduler

# 環境変数の読み込み
load_dotenv()

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("mcp_server.log", encoding="utf-8")
    ]
)

logger = logging.getLogger("mcp_server")

# FastAPIインスタンスの作成
app = FastAPI(
    title="Model Context Protocol Server",
    description="AIモデルとブラウザ自動化を一元管理するMCPサーバー",
    version="1.0.0"
)

# CORSミドルウェアの追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限する
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# モデルとブローカーのインスタンスを作成
model_manager = ModelManager()
message_broker = MessageBroker()
browser_controller = BrowserController()
task_scheduler = TaskScheduler()

# リクエスト/レスポンスモデルの定義
class ModelRequest(BaseModel):
    model_name: str
    prompt: str
    parameters: Optional[Dict[str, Any]] = None

class BrowserRequest(BaseModel):
    action: str
    url: Optional[str] = None
    selector: Optional[str] = None
    text: Optional[str] = None
    code: Optional[str] = None

class TaskRequest(BaseModel):
    task_type: str
    priority: int = 0
    data: Dict[str, Any]
    schedule: Optional[str] = None

class ModelResponse(BaseModel):
    model_name: str
    response: str
    tokens: Optional[int] = None
    usage: Optional[Dict[str, Any]] = None

# WebSocketのコネクション管理
active_connections: List[WebSocket] = []

# APIルートの定義
@app.get("/")
async def root():
    return {"message": "MCPサーバーが稼働中です"}

@app.get("/status")
async def server_status():
    """サーバーの状態を確認するエンドポイント"""
    return {
        "status": "online",
        "models": model_manager.list_available_models(),
        "active_browsers": browser_controller.get_active_browsers(),
        "pending_tasks": task_scheduler.get_pending_tasks_count(),
    }

@app.post("/model/generate", response_model=ModelResponse)
async def generate_text(request: ModelRequest):
    """AIモデルでテキスト生成を行うエンドポイント"""
    try:
        response = await model_manager.generate(
            request.model_name,
            request.prompt,
            request.parameters or {}
        )
        return response
    except Exception as e:
        logger.error(f"生成エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/browser/action")
async def browser_action(request: BrowserRequest):
    """ブラウザ操作を行うエンドポイント"""
    try:
        result = await browser_controller.execute_action(
            request.action,
            url=request.url,
            selector=request.selector,
            text=request.text,
            code=request.code
        )
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"ブラウザ操作エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/task/schedule")
async def schedule_task(request: TaskRequest):
    """タスクをスケジュールするエンドポイント"""
    try:
        task_id = task_scheduler.add_task(
            request.task_type,
            request.data,
            priority=request.priority,
            schedule=request.schedule
        )
        return {"task_id": task_id}
    except Exception as e:
        logger.error(f"タスクスケジューリングエラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """タスクの状態を取得するエンドポイント"""
    try:
        status = task_scheduler.get_task_status(task_id)
        if status is None:
            raise HTTPException(status_code=404, detail="タスクが見つかりません")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"タスク状態取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocketエンドポイント
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            
            if request.get("type") == "model_request":
                response = await model_manager.generate(
                    request.get("model_name", "default"),
                    request.get("prompt", ""),
                    request.get("parameters", {})
                )
                await websocket.send_json(response)
            
            elif request.get("type") == "browser_request":
                result = await browser_controller.execute_action(
                    request.get("action", ""),
                    url=request.get("url"),
                    selector=request.get("selector"),
                    text=request.get("text"),
                    code=request.get("code")
                )
                await websocket.send_json({"success": True, "result": result})
            
            elif request.get("type") == "subscribe":
                # メッセージブローカーへのサブスクリプション
                topic = request.get("topic", "")
                if topic:
                    await message_broker.subscribe(topic, websocket)
                    await websocket.send_json({"subscribed": topic})
            
            else:
                await websocket.send_json({"error": "不明なリクエストタイプです"})
                
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        await message_broker.unsubscribe_all(websocket)
    except Exception as e:
        logger.error(f"WebSocketエラー: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)
            await message_broker.unsubscribe_all(websocket)

# 起動イベント
@app.on_event("startup")
async def startup_event():
    logger.info("MCPサーバーの起動開始...")
    try:
        # 各コンポーネントの初期化
        await model_manager.initialize()
        await message_broker.initialize()
        await browser_controller.initialize()
        await task_scheduler.initialize()
        
        logger.info("すべてのコンポーネントが正常に初期化されました")
    except Exception as e:
        logger.error(f"起動時エラー: {e}")
        # 致命的なエラーの場合はサーバーを停止
        sys.exit(1)

# 終了イベント
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("MCPサーバーのシャットダウン開始...")
    try:
        # 各コンポーネントのクリーンアップ
        await model_manager.cleanup()
        await message_broker.cleanup()
        await browser_controller.cleanup()
        await task_scheduler.cleanup()
        
        logger.info("すべてのコンポーネントが正常にシャットダウンされました")
    except Exception as e:
        logger.error(f"シャットダウン時エラー: {e}")

# メイン関数
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
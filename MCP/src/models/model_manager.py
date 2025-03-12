import os
import logging
import json
import google.generativeai as genai
from typing import Dict, Any, List, Optional, Union

# ロギングの設定
logger = logging.getLogger(__name__)

class ModelManager:
    """
    LLMモデルの管理と操作を行うクラス
    """
    
    def __init__(self):
        """
        ModelManagerを初期化します。
        """
        self.initialized = False
        self.models = {}
        self.default_model = None
        self.usage_stats = {"requests": 0, "tokens": 0}
        
        # API キー
        self.google_api_key = os.environ.get("GOOGLE_API_KEY")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        
        logger.info("ModelManagerが初期化されました")
    
    async def initialize(self) -> bool:
        """
        モデルマネージャーを初期化します。
        
        Returns:
            bool: 初期化に成功したかどうか
        """
        try:
            # Googleのモデルを設定
            if self.google_api_key:
                genai.configure(api_key=self.google_api_key)
                self.models["gemini-pro"] = {"provider": "google", "name": "gemini-pro", "status": "available"}
                self.default_model = "gemini-pro"
                logger.info("Googleのモデルが設定されました")
            
            # デフォルトモデルの設定
            self.default_model = os.environ.get("DEFAULT_MODEL", self.default_model)
            
            self.initialized = True
            logger.info("ModelManagerの初期化が完了しました")
            return True
        except Exception as e:
            logger.error(f"ModelManagerの初期化に失敗しました: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """
        モデルマネージャーをシャットダウンします。
        
        Returns:
            bool: シャットダウンに成功したかどうか
        """
        self.initialized = False
        logger.info("ModelManagerをシャットダウンしました")
        return True
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        利用可能なモデルのリストを取得します。
        
        Returns:
            List[Dict[str, Any]]: モデル情報のリスト
        """
        return list(self.models.values())
    
    async def get_usage(self) -> Dict[str, Any]:
        """
        使用状況の統計を取得します。
        
        Returns:
            Dict[str, Any]: 使用状況の統計
        """
        return self.usage_stats
    
    async def generate(self, messages: List[Dict[str, Any]], model: str = None, **kwargs) -> Dict[str, Any]:
        """
        テキストを生成します。
        
        Args:
            messages (List[Dict[str, Any]]): メッセージのリスト
            model (str, optional): 使用するモデル名
            **kwargs: その他のパラメータ
            
        Returns:
            Dict[str, Any]: 生成結果
        """
        if not self.initialized:
            await self.initialize()
        
        # 使用状況の更新
        self.usage_stats["requests"] += 1
        
        # モデルの選択
        model_name = model or self.default_model
        if not model_name or model_name not in self.models:
            if self.default_model:
                model_name = self.default_model
                logger.warning(f"指定されたモデル '{model}' が見つかりません。デフォルトモデル '{self.default_model}' を使用します。")
            else:
                return {"error": "有効なモデルが指定されていません"}
        
        try:
            model_info = self.models.get(model_name, {})
            provider = model_info.get("provider")
            
            if provider == "google":
                return await self._generate_with_google(messages, model_name, **kwargs)
            else:
                return {"error": f"プロバイダ '{provider}' はサポートされていません"}
        except Exception as e:
            logger.error(f"テキスト生成中にエラーが発生しました: {e}")
            return {"error": str(e)}
    
    async def generate_with_image(self, messages: List[Dict[str, Any]], model: str = None, **kwargs) -> Dict[str, Any]:
        """
        画像付きのテキストを生成します。
        
        Args:
            messages (List[Dict[str, Any]]): メッセージのリスト（画像URLを含む）
            model (str, optional): 使用するモデル名
            **kwargs: その他のパラメータ
            
        Returns:
            Dict[str, Any]: 生成結果
        """
        if not self.initialized:
            await self.initialize()
        
        # 使用状況の更新
        self.usage_stats["requests"] += 1
        
        # モデルの選択
        model_name = model or "gemini-pro-vision"  # 画像対応モデル
        
        try:
            if self.google_api_key:
                return await self._generate_with_google_vision(messages, model_name, **kwargs)
            else:
                return {"error": "画像対応モデルが設定されていません"}
        except Exception as e:
            logger.error(f"画像付きテキスト生成中にエラーが発生しました: {e}")
            return {"error": str(e)}
    
    async def _generate_with_google(self, messages: List[Dict[str, Any]], model_name: str, **kwargs) -> Dict[str, Any]:
        """
        Google AI (Gemini) を使用してテキストを生成します。
        
        Args:
            messages (List[Dict[str, Any]]): メッセージのリスト
            model_name (str): モデル名
            **kwargs: その他のパラメータ
            
        Returns:
            Dict[str, Any]: 生成結果
        """
        try:
            # パラメータの設定
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens")
            
            # Googleの生成AIモデルを設定
            generation_config = {
                "temperature": temperature,
                "top_p": kwargs.get("top_p", 0.95),
                "top_k": kwargs.get("top_k", 40),
            }
            
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens
            
            # モデルの取得
            model = genai.GenerativeModel(model_name=model_name, generation_config=generation_config)
            
            # メッセージの変換
            google_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    google_messages.append({"role": "user", "parts": [content]})
                    google_messages.append({"role": "model", "parts": ["I'll help you with that request, following the instructions."]})
                elif role == "user":
                    google_messages.append({"role": "user", "parts": [content]})
                elif role == "assistant":
                    google_messages.append({"role": "model", "parts": [content]})
            
            # チャットの生成
            chat = model.start_chat(history=google_messages[:-1] if google_messages else [])
            response = chat.send_message(google_messages[-1]["parts"][0] if google_messages else "")
            
            # トークン使用量の更新
            if hasattr(response, "usage"):
                prompt_tokens = getattr(response.usage, "prompt_tokens", 0)
                completion_tokens = getattr(response.usage, "completion_tokens", 0)
                self.usage_stats["tokens"] += prompt_tokens + completion_tokens
            
            # レスポンスの加工
            return {
                "text": response.text,
                "model": model_name,
                "finish_reason": "stop"
            }
        except Exception as e:
            logger.error(f"Google AI でのテキスト生成中にエラーが発生しました: {e}")
            return {"error": str(e)}
    
    async def _generate_with_google_vision(self, messages: List[Dict[str, Any]], model_name: str, **kwargs) -> Dict[str, Any]:
        """
        Google AI (Gemini) の画像対応モデルを使用してテキストを生成します。
        
        Args:
            messages (List[Dict[str, Any]]): メッセージのリスト（画像URLを含む）
            model_name (str): モデル名
            **kwargs: その他のパラメータ
            
        Returns:
            Dict[str, Any]: 生成結果
        """
        try:
            # パラメータの設定
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens")
            
            # Googleの生成AIモデルを設定
            generation_config = {
                "temperature": temperature,
                "top_p": kwargs.get("top_p", 0.95),
                "top_k": kwargs.get("top_k", 40),
            }
            
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens
            
            # モデルの取得
            model = genai.GenerativeModel(model_name="gemini-pro-vision", generation_config=generation_config)
            
            # メッセージの変換
            prompt_parts = []
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if isinstance(content, list):
                    # マルチモーダルコンテンツ
                    for item in content:
                        if item.get("type") == "text":
                            prompt_parts.append(item.get("text", ""))
                        elif item.get("type") == "image":
                            image_url = item.get("image_url", {}).get("url", "")
                            if image_url:
                                prompt_parts.append(genai.types.Image.from_url(image_url))
                else:
                    # テキストのみのコンテンツ
                    prompt_parts.append(content)
            
            # 応答の生成
            response = model.generate_content(prompt_parts)
            
            # トークン使用量の更新
            if hasattr(response, "usage"):
                prompt_tokens = getattr(response.usage, "prompt_tokens", 0)
                completion_tokens = getattr(response.usage, "completion_tokens", 0)
                self.usage_stats["tokens"] += prompt_tokens + completion_tokens
            
            # レスポンスの加工
            return {
                "text": response.text,
                "model": model_name,
                "finish_reason": "stop"
            }
        except Exception as e:
            logger.error(f"Google Vision AIでのテキスト生成中にエラーが発生しました: {e}")
            return {"error": str(e)} 
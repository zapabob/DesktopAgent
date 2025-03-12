import os
import logging
import asyncio
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# 環境変数の読み込み
load_dotenv()

logger = logging.getLogger("model_manager")

class ModelManager:
    """
    AIモデルを管理するクラス。
    複数のAIプロバイダー（Google AI, OpenAI, Anthropic）をサポートし、
    モデルの初期化、生成リクエストの処理、使用状況の追跡を行います。
    """
    
    def __init__(self):
        self.models = {}
        self.vision_models = {}
        self.usage_stats = {}
        self.google_models = ["gemini-pro", "gemini-pro-vision"]
        self.openai_models = ["gpt-4", "gpt-3.5-turbo"]
        self.anthropic_models = ["claude-3-opus", "claude-3-sonnet"]
        
    async def initialize(self) -> None:
        """
        利用可能なすべてのAIモデルを初期化します。
        """
        logger.info("モデルマネージャーの初期化を開始...")
        
        # Google AI モデルの初期化
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if google_api_key:
            try:
                genai.configure(api_key=google_api_key)
                # テキスト用モデル
                self.models["gemini-pro"] = ChatGoogleGenerativeAI(model="gemini-pro")
                # マルチモーダル用モデル
                self.vision_models["gemini-pro-vision"] = GoogleGenerativeAI(model="gemini-pro-vision")
                logger.info("Google AI (Gemini Pro) モデルを初期化しました")
            except Exception as e:
                logger.error(f"Google AI初期化エラー: {e}")
        else:
            logger.warning("GOOGLE_API_KEYが設定されていません")
        
        # OpenAI APIモデルの初期化
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            try:
                # テキスト用モデル（GPT-4をデフォルトに）
                self.models["gpt-4"] = ChatOpenAI(api_key=openai_api_key, model_name="gpt-4")
                self.models["gpt-3.5-turbo"] = ChatOpenAI(api_key=openai_api_key, model_name="gpt-3.5-turbo")
                logger.info("OpenAI GPT-4/GPT-3.5モデルを初期化しました")
            except Exception as e:
                logger.error(f"OpenAI初期化エラー: {e}")
        else:
            logger.warning("OPENAI_API_KEYが設定されていません")
        
        # Anthropic Claude APIモデルの初期化
        claude_api_key = os.getenv("CLAUDE_API_KEY")
        if claude_api_key:
            try:
                # Claudeモデル
                self.models["claude-3-opus"] = ChatAnthropic(api_key=claude_api_key, model_name="claude-3-opus-20240229")
                self.models["claude-3-sonnet"] = ChatAnthropic(api_key=claude_api_key, model_name="claude-3-sonnet-20240229")
                logger.info("Anthropic Claudeモデルを初期化しました")
            except Exception as e:
                logger.error(f"Anthropic初期化エラー: {e}")
        else:
            logger.warning("CLAUDE_API_KEYが設定されていません")
            
        logger.info(f"初期化されたモデル: {list(self.models.keys())}")
        logger.info(f"初期化されたビジョンモデル: {list(self.vision_models.keys())}")
    
    async def generate(self, model_name: str, prompt: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        指定されたモデルを使用してテキスト生成を行います。
        
        Args:
            model_name: 使用するモデルの名前
            prompt: 生成のためのプロンプト
            parameters: 生成パラメータのディクショナリ
            
        Returns:
            生成結果を含むディクショナリ
        """
        if parameters is None:
            parameters = {}
            
        # モデル名の正規化
        model_name = model_name.lower()
        
        # モデルが初期化されているか確認
        if model_name not in self.models:
            if model_name in self.vision_models:
                raise ValueError(f"{model_name}はビジョンモデルです。テキスト生成には使用できません。")
            
            # 利用可能なモデルが存在しない場合は初期化
            if not self.models:
                await self.initialize()
                if not self.models:
                    raise ValueError("有効なAIモデルが初期化されていません。APIキーを確認してください。")
            
            # 指定されたモデルが利用できない場合、代替モデルを選択
            if self.models:
                model_name = next(iter(self.models.keys()))
                logger.warning(f"指定されたモデル '{model_name}' は利用できません。代わりに '{model_name}' を使用します。")
            else:
                raise ValueError(f"モデル '{model_name}' が利用できません。")
        
        try:
            # モデルを使用してテキスト生成
            model = self.models[model_name]
            
            # 使用統計の更新
            if model_name not in self.usage_stats:
                self.usage_stats[model_name] = {"requests": 0, "tokens": 0}
            self.usage_stats[model_name]["requests"] += 1
            
            # LangChainモデルに対応する処理
            response = model.invoke(prompt)
            content = response.content
            
            # レスポンスの整形
            result = {
                "model_name": model_name,
                "response": content,
                "tokens": None,  # トークン数の計算は省略
                "usage": None
            }
            
            return result
        except Exception as e:
            logger.error(f"生成エラー ({model_name}): {e}")
            raise
    
    async def generate_with_image(self, model_name: str, prompt: str, image_data: bytes, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        画像とテキストのプロンプトを使用してテキスト生成を行います。
        
        Args:
            model_name: 使用するビジョンモデルの名前
            prompt: 生成のためのテキストプロンプト
            image_data: バイナリ形式の画像データ
            parameters: 生成パラメータのディクショナリ
            
        Returns:
            生成結果を含むディクショナリ
        """
        if parameters is None:
            parameters = {}
            
        # モデル名の正規化
        model_name = model_name.lower()
        
        # ビジョンモデルが初期化されているか確認
        if model_name not in self.vision_models:
            # デフォルトのビジョンモデルがあれば使用
            if "gemini-pro-vision" in self.vision_models:
                model_name = "gemini-pro-vision"
                logger.warning(f"指定されたモデルは利用できません。代わりに '{model_name}' を使用します。")
            else:
                raise ValueError(f"ビジョンモデル '{model_name}' が利用できません。")
        
        try:
            # モデルを使用してテキスト生成
            model = self.vision_models[model_name]
            
            # 使用統計の更新
            if model_name not in self.usage_stats:
                self.usage_stats[model_name] = {"requests": 0, "tokens": 0}
            self.usage_stats[model_name]["requests"] += 1
            
            # LangChainモデルに対応する処理
            response = model.invoke([prompt, image_data])
            content = response.text
            
            # レスポンスの整形
            result = {
                "model_name": model_name,
                "response": content,
                "tokens": None,  # トークン数の計算は省略
                "usage": None
            }
            
            return result
        except Exception as e:
            logger.error(f"画像付き生成エラー ({model_name}): {e}")
            raise
    
    def list_available_models(self) -> Dict[str, List[str]]:
        """利用可能なモデルの一覧を返します"""
        available_text_models = list(self.models.keys())
        available_vision_models = list(self.vision_models.keys())
        
        return {
            "text_models": available_text_models,
            "vision_models": available_vision_models
        }
    
    def get_usage_statistics(self) -> Dict[str, Dict[str, int]]:
        """各モデルの使用統計を返します"""
        return self.usage_stats
    
    async def cleanup(self) -> None:
        """モデルリソースのクリーンアップを行います"""
        logger.info("モデルマネージャーのクリーンアップを実行...")
        # 現在の実装では特別なクリーンアップは不要 
import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, SecretStr
from dotenv import load_dotenv
import logging
from pathlib import Path
import yaml
import json
from datetime import datetime
import google.generativeai as genai
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import asyncio
import time
from desktop_agent.monitoring.performance import PerformanceMonitor
from desktop_agent.caching.response_cache import ResponseCache
from desktop_agent.security.rate_limiter import RateLimiter

load_dotenv()

class AIConfig(BaseModel):
    """AI設定クラス"""
    google_api_key: Optional[SecretStr] = None
    openai_api_key: Optional[SecretStr] = None
    anthropic_api_key: Optional[SecretStr] = None
    
    # モデル設定
    gemini_pro_model: str = "gemini-pro"
    gemini_pro_vision_model: str = "gemini-pro-vision"
    openai_model: str = "gpt-4-turbo-preview"
    anthropic_model: str = "claude-3-opus-20240229"
    
    # 生成設定
    generation_config: Dict[str, Any] = {
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
        "max_output_tokens": 2048,
    }
    
    # セーフティ設定
    safety_settings: Dict[str, str] = {
        "HARM_CATEGORY_HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE",
        "HARM_CATEGORY_HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE",
        "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_MEDIUM_AND_ABOVE",
    }
    
    # プロバイダーの重み付け
    provider_weights: Dict[str, float] = {
        "google": 1.0,
        "openai": 0.8,
        "anthropic": 0.6
    }
    
    # リトライ設定
    retry_limit: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        
    @property
    def has_valid_provider(self) -> bool:
        """有効なプロバイダーが存在するか確認"""
        return any([
            self.google_api_key,
            self.openai_api_key,
            self.anthropic_api_key
        ])
        
    def validate_generation_config(self) -> None:
        """生成設定の検証"""
        if not 0.0 <= self.generation_config["temperature"] <= 1.0:
            raise ValueError("temperature must be between 0.0 and 1.0")
            
        if not 0.0 <= self.generation_config["top_p"] <= 1.0:
            raise ValueError("top_p must be between 0.0 and 1.0")
            
        if self.generation_config["top_k"] < 1:
            raise ValueError("top_k must be greater than 0")
            
        if self.generation_config["max_output_tokens"] < 1:
            raise ValueError("max_output_tokens must be greater than 0")
            
    def validate_provider_weights(self) -> None:
        """プロバイダーの重み付けを検証"""
        for provider, weight in self.provider_weights.items():
            if weight < 0.0:
                raise ValueError(f"Weight for {provider} must be non-negative")
                
    def validate_safety_settings(self) -> None:
        """セーフティ設定の検証"""
        valid_levels = [
            "BLOCK_NONE",
            "BLOCK_LOW_AND_ABOVE",
            "BLOCK_MEDIUM_AND_ABOVE",
            "BLOCK_HIGH_AND_ABOVE"
        ]
        
        for category, level in self.safety_settings.items():
            if level not in valid_levels:
                raise ValueError(f"Invalid safety level for {category}: {level}")
                
    def validate_all(self) -> None:
        """すべての設定を検証"""
        self.validate_generation_config()
        self.validate_provider_weights()
        self.validate_safety_settings()

    def __init__(self, **data):
        super().__init__(**data)
        self.monitor = PerformanceMonitor()
        self.cache = ResponseCache()
        self.rate_limiter = RateLimiter()

def load_ai_config(config_path: Optional[str] = None) -> AIConfig:
    """AI設定の読み込み"""
    try:
        # 環境変数からAPIキーを読み込み
        config_data = {
            "google_api_key": os.getenv("GOOGLE_API_KEY"),
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY")
        }
        
        # 設定ファイルが指定されている場合は読み込み
        if config_path:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    if config_file.suffix == ".yaml":
                        file_config = yaml.safe_load(f)
                    elif config_file.suffix == ".json":
                        file_config = json.load(f)
                    else:
                        raise ValueError(f"Unsupported config file format: {config_file.suffix}")
                        
                    # 設定ファイルの値で上書き
                    config_data.update(file_config)
                
        # APIキーをSecretStrに変換
        for key, value in config_data.items():
            if value and key.endswith("_api_key"):
                config_data[key] = SecretStr(value)
                
        return AIConfig(**config_data)
        
    except Exception as e:
        logging.error(f"設定読み込みエラー: {e}")
        raise

class ConfigManager:
    """設定管理クラス"""
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else Path("config")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "ai_config.yaml"
        self.logger = logging.getLogger(__name__)
        
    def save_config(self, config: AIConfig):
        """設定の保存"""
        try:
            config_dict = config.dict(exclude={"google_api_key",
                                             "openai_api_key",
                                             "anthropic_api_key"})
            
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(config_dict, f, default_flow_style=False,
                             allow_unicode=True)
                
        except Exception as e:
            self.logger.error(f"設定保存エラー: {e}")
            raise
            
    def load_config(self) -> AIConfig:
        """設定の読み込み"""
        return load_ai_config(str(self.config_file))

class AIManager:
    """AIマネージャークラス"""
    def __init__(self, config_path: Optional[str] = None):
        self.config = load_ai_config(config_path)
        self.logger = logging.getLogger(__name__)
        self.providers = {}
        
        # 各コンポーネントの初期化
        self.monitor = PerformanceMonitor()
        self.cache = ResponseCache()
        self.rate_limiter = RateLimiter()
        
        self._setup_providers()
        self._start_background_tasks()
        
    def _start_background_tasks(self):
        """バックグラウンドタスクの開始"""
        asyncio.create_task(self.monitor.start_monitoring())
        asyncio.create_task(self.cache.start_cache_maintenance())
        
    async def _execute_with_monitoring(self, provider: str,
                                     func_name: str,
                                     *args, **kwargs) -> str:
        """モニタリング付きの実行"""
        start_time = time.time()
        success = True
        
        try:
            # レート制限のチェック
            await self.rate_limiter.wait_if_needed(provider)
            
            # キャッシュのチェック
            cache_key = {
                "func": func_name,
                "args": args,
                "kwargs": kwargs
            }
            if cached_response := await self.cache.get(
                provider, func_name, cache_key
            ):
                return cached_response
                
            # 実際の実行
            response = await getattr(self, f"_execute_{func_name}")(
                provider, *args, **kwargs
            )
            
            # キャッシュの更新
            await self.cache.set(provider, func_name, cache_key, response)
            
            return response
            
        except Exception as e:
            success = False
            self.logger.error(f"実行エラー: {e}")
            raise
            
        finally:
            # メトリクスの記録
            latency = time.time() - start_time
            await self.monitor.record_request(provider, latency, success)
            
    async def _execute_generate_text(self, provider: str,
                                   prompt: str) -> str:
        """テキスト生成の実行"""
        provider_info = self.providers[provider]
        
        if provider == "google":
            response = await provider_info["text_model"].generate_content_async(prompt)
            return response.text
        elif provider == "openai":
            response = await provider_info["client"].chat.completions.create(
                model=provider_info["model"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.generation_config["max_output_tokens"],
                temperature=self.config.generation_config["temperature"]
            )
            return response.choices[0].message.content
        elif provider == "anthropic":
            response = await provider_info["client"].messages.create(
                model=provider_info["model"],
                max_tokens=self.config.generation_config["max_output_tokens"],
                temperature=self.config.generation_config["temperature"],
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
            
    async def _execute_analyze_image(self, provider: str,
                                   image_path: str,
                                   prompt: str) -> str:
        """画像分析の実行"""
        provider_info = self.providers[provider]
        
        if provider == "google":
            image = genai.Image.from_file(image_path)
            response = await provider_info["vision_model"].generate_content_async(
                [prompt, image]
            )
            return response.text
        elif provider == "openai":
            with open(image_path, "rb") as image_file:
                response = await provider_info["client"].chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_file.read()}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=self.config.generation_config["max_output_tokens"]
                )
            return response.choices[0].message.content
            
    async def _execute_chat(self, provider: str,
                          messages: list) -> str:
        """チャットの実行"""
        provider_info = self.providers[provider]
        
        if provider == "google":
            chat = provider_info["text_model"].start_chat(history=[])
            response = await chat.send_message_async(messages[-1]["content"])
            return response.text
        elif provider == "openai":
            response = await provider_info["client"].chat.completions.create(
                model=provider_info["model"],
                messages=[{"role": m["role"], "content": m["content"]}
                         for m in messages],
                max_tokens=self.config.generation_config["max_output_tokens"],
                temperature=self.config.generation_config["temperature"]
            )
            return response.choices[0].message.content
        elif provider == "anthropic":
            response = await provider_info["client"].messages.create(
                model=provider_info["model"],
                max_tokens=self.config.generation_config["max_output_tokens"],
                temperature=self.config.generation_config["temperature"],
                messages=[{"role": m["role"], "content": m["content"]}
                         for m in messages]
            )
            return response.content[0].text
            
    # 公開メソッドの更新
    async def generate_text(self, prompt: str) -> str:
        """テキスト生成"""
        provider_name, _ = await self._select_provider("text")
        return await self._execute_with_monitoring(
            provider_name, "generate_text", prompt
        )
        
    async def analyze_image(self, image_path: str, prompt: str) -> str:
        """画像分析"""
        provider_name, _ = await self._select_provider("vision")
        return await self._execute_with_monitoring(
            provider_name, "analyze_image", image_path, prompt
        )
        
    async def chat(self, messages: list) -> str:
        """チャット応答生成"""
        provider_name, _ = await self._select_provider("text")
        return await self._execute_with_monitoring(
            provider_name, "chat", messages
        )

    def _setup_providers(self):
        """プロバイダーの設定"""
        try:
            # Google AI
            if self.config.google_api_key:
                genai.configure(api_key=self.config.google_api_key.get_secret_value())
                self.providers["google"] = {
                    "text_model": genai.GenerativeModel(
                        model_name=self.config.gemini_pro_model,
                        generation_config=self.config.generation_config,
                        safety_settings=self.config.safety_settings
                    ),
                    "vision_model": genai.GenerativeModel(
                        model_name=self.config.gemini_pro_vision_model,
                        generation_config=self.config.generation_config,
                        safety_settings=self.config.safety_settings
                    ),
                    "weight": self.config.provider_weights["google"]
                }
                
            # OpenAI
            if self.config.openai_api_key:
                openai_client = AsyncOpenAI(
                    api_key=self.config.openai_api_key.get_secret_value()
                )
                self.providers["openai"] = {
                    "client": openai_client,
                    "model": self.config.openai_model,
                    "weight": self.config.provider_weights["openai"]
                }
                
            # Anthropic
            if self.config.anthropic_api_key:
                anthropic_client = AsyncAnthropic(
                    api_key=self.config.anthropic_api_key.get_secret_value()
                )
                self.providers["anthropic"] = {
                    "client": anthropic_client,
                    "model": self.config.anthropic_model,
                    "weight": self.config.provider_weights["anthropic"]
                }
                
        except Exception as e:
            self.logger.error(f"プロバイダー設定エラー: {e}")
            raise
            
    async def _select_provider(self, task_type: str = "text") -> tuple[str, Any]:
        """プロバイダーの選択"""
        available_providers = {
            name: info for name, info in self.providers.items()
            if (task_type != "vision" or "vision_model" in info)
        }
        
        if not available_providers:
            raise RuntimeError(f"利用可能な{task_type}プロバイダーがありません")
            
        # 重み付き選択
        weights = [info["weight"] for info in available_providers.values()]
        total_weight = sum(weights)
        if total_weight == 0:
            raise RuntimeError("プロバイダーの重みが不正です")
            
        r = asyncio.get_event_loop().time() * total_weight
        for name, info in available_providers.items():
            r -= info["weight"]
            if r <= 0:
                return name, info
                
        # フォールバック
        name, info = list(available_providers.items())[0]
        return name, info 
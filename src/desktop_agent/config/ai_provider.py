from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, SecretStr
import google.generativeai as genai
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import asyncio
import random
from datetime import datetime, timedelta
import torch
import os

class AIProviderConfig(BaseModel):
    """AIプロバイダー設定"""
    provider_type: str
    api_key: SecretStr
    model_name: str
    weight: float = 1.0
    max_tokens: int = 2048
    temperature: float = 0.7
    retry_limit: int = 3
    timeout: float = 30.0

class BaseAIProvider(ABC):
    """AIプロバイダー基底クラス"""
    def __init__(self, config: AIProviderConfig):
        self.config = config
        self.last_used = datetime.min
        self.error_count = 0
        self.success_count = 0
        
    @abstractmethod
    async def generate_text(self, prompt: str) -> str:
        pass
        
    @abstractmethod
    async def analyze_image(self, image_path: str, prompt: str) -> str:
        pass
        
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]]) -> str:
        pass
        
    def update_stats(self, success: bool):
        """統計情報の更新"""
        self.last_used = datetime.now()
        if success:
            self.success_count += 1
            self.error_count = max(0, self.error_count - 1)
        else:
            self.error_count += 1

class GoogleAIProvider(BaseAIProvider):
    """Google AI Studioプロバイダー"""
    def __init__(self, config: AIProviderConfig):
        super().__init__(config)
        genai.configure(api_key=config.api_key.get_secret_value())
        self.text_model = genai.GenerativeModel(
            model_name=config.model_name,
            generation_config={
                "temperature": config.temperature,
                "max_output_tokens": config.max_tokens,
            }
        )
        self.vision_model = genai.GenerativeModel(
            model_name="gemini-pro-vision",
            generation_config={
                "temperature": config.temperature,
                "max_output_tokens": config.max_tokens,
            }
        )
        
    async def generate_text(self, prompt: str) -> str:
        try:
            response = await self.text_model.generate_content_async(prompt)
            self.update_stats(True)
            return response.text
        except Exception as e:
            self.update_stats(False)
            raise
            
    async def analyze_image(self, image_path: str, prompt: str) -> str:
        try:
            image = genai.Image.from_file(image_path)
            response = await self.vision_model.generate_content_async([prompt, image])
            self.update_stats(True)
            return response.text
        except Exception as e:
            self.update_stats(False)
            raise
            
    async def chat(self, messages: List[Dict[str, str]]) -> str:
        try:
            chat = self.text_model.start_chat(history=[])
            response = await chat.send_message_async(messages[-1]["content"])
            self.update_stats(True)
            return response.text
        except Exception as e:
            self.update_stats(False)
            raise

class OpenAIProvider(BaseAIProvider):
    """OpenAIプロバイダー"""
    def __init__(self, config: AIProviderConfig):
        super().__init__(config)
        self.client = AsyncOpenAI(api_key=config.api_key.get_secret_value())
        
    async def generate_text(self, prompt: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            self.update_stats(True)
            return response.choices[0].message.content
        except Exception as e:
            self.update_stats(False)
            raise
            
    async def analyze_image(self, image_path: str, prompt: str) -> str:
        try:
            with open(image_path, "rb") as image_file:
                response = await self.client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{image_file.read()}"}
                                }
                            ]
                        }
                    ],
                    max_tokens=self.config.max_tokens
                )
            self.update_stats(True)
            return response.choices[0].message.content
        except Exception as e:
            self.update_stats(False)
            raise
            
    async def chat(self, messages: List[Dict[str, str]]) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[{"role": m["role"], "content": m["content"]} for m in messages],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            self.update_stats(True)
            return response.choices[0].message.content
        except Exception as e:
            self.update_stats(False)
            raise

class AnthropicProvider(BaseAIProvider):
    """Anthropicプロバイダー"""
    def __init__(self, config: AIProviderConfig):
        super().__init__(config)
        self.client = AsyncAnthropic(api_key=config.api_key.get_secret_value())
        
    async def generate_text(self, prompt: str) -> str:
        try:
            response = await self.client.messages.create(
                model=self.config.model_name,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            self.update_stats(True)
            return response.content[0].text
        except Exception as e:
            self.update_stats(False)
            raise
            
    async def analyze_image(self, image_path: str, prompt: str) -> str:
        # Anthropicは現在画像分析をサポートしていないため、
        # 他のプロバイダーにフォールバック
        raise NotImplementedError("Anthropic does not support image analysis")
            
    async def chat(self, messages: List[Dict[str, str]]) -> str:
        try:
            response = await self.client.messages.create(
                model=self.config.model_name,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[{"role": m["role"], "content": m["content"]} for m in messages]
            )
            self.update_stats(True)
            return response.content[0].text
        except Exception as e:
            self.update_stats(False)
            raise

class LoadBalancer:
    """AIプロバイダーロードバランサー"""
    def __init__(self):
        self.providers: Dict[str, BaseAIProvider] = {}
        self.lock = asyncio.Lock()
        
    def add_provider(self, provider_id: str, provider: BaseAIProvider):
        """プロバイダーの追加"""
        self.providers[provider_id] = provider
        
    def remove_provider(self, provider_id: str):
        """プロバイダーの削除"""
        if provider_id in self.providers:
            del self.providers[provider_id]
            
    async def get_best_provider(self, task_type: str = "text") -> BaseAIProvider:
        """最適なプロバイダーの選択"""
        async with self.lock:
            available_providers = [
                p for p in self.providers.values()
                if (task_type != "image" or hasattr(p, "analyze_image")) and
                p.error_count < p.config.retry_limit and
                datetime.now() - p.last_used > timedelta(seconds=1)
            ]
            
            if not available_providers:
                raise RuntimeError("No available AI providers")
                
            # 重み付きランダム選択
            weights = [
                p.config.weight * (1.0 / (p.error_count + 1)) *
                (p.success_count + 1) / (p.success_count + p.error_count + 1)
                for p in available_providers
            ]
            
            return random.choices(available_providers, weights=weights, k=1)[0]
            
    async def execute_with_fallback(self, task_type: str, func_name: str, *args, **kwargs) -> str:
        """フォールバック付きタスク実行"""
        errors = []
        
        for _ in range(3):  # 最大3回リトライ
            try:
                provider = await self.get_best_provider(task_type)
                func = getattr(provider, func_name)
                return await func(*args, **kwargs)
            except Exception as e:
                errors.append(str(e))
                await asyncio.sleep(1)
                
        raise Exception(f"All providers failed: {errors}")

class AIOrchestrator:
    """AIオーケストレーター"""
    def __init__(self):
        self.load_balancer = LoadBalancer()
        self._setup_providers()
        
    def _setup_providers(self):
        """プロバイダーの設定"""
        # Google AI
        if google_api_key := os.getenv("GOOGLE_API_KEY"):
            self.load_balancer.add_provider(
                "google",
                GoogleAIProvider(AIProviderConfig(
                    provider_type="google",
                    api_key=SecretStr(google_api_key),
                    model_name="gemini-pro",
                    weight=1.0
                ))
            )
            
        # OpenAI
        if openai_api_key := os.getenv("OPENAI_API_KEY"):
            self.load_balancer.add_provider(
                "openai",
                OpenAIProvider(AIProviderConfig(
                    provider_type="openai",
                    api_key=SecretStr(openai_api_key),
                    model_name="gpt-4-turbo-preview",
                    weight=0.8
                ))
            )
            
        # Anthropic
        if anthropic_api_key := os.getenv("ANTHROPIC_API_KEY"):
            self.load_balancer.add_provider(
                "anthropic",
                AnthropicProvider(AIProviderConfig(
                    provider_type="anthropic",
                    api_key=SecretStr(anthropic_api_key),
                    model_name="claude-3-opus-20240229",
                    weight=0.6
                ))
            )
            
    async def generate_text(self, prompt: str) -> str:
        """テキスト生成"""
        return await self.load_balancer.execute_with_fallback(
            "text", "generate_text", prompt
        )
        
    async def analyze_image(self, image_path: str, prompt: str) -> str:
        """画像分析"""
        return await self.load_balancer.execute_with_fallback(
            "image", "analyze_image", image_path, prompt
        )
        
    async def chat(self, messages: List[Dict[str, str]]) -> str:
        """チャット応答生成"""
        return await self.load_balancer.execute_with_fallback(
            "text", "chat", messages
        ) 
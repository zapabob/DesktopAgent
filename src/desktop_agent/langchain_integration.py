<<<<<<< HEAD
# -*- coding: utf-8 -*-
"""LangChain integration module."""

from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

class LangChainManager:
    def __init__(self, config):
        self.config = config
        self.models = {
            'GPT-4': ChatOpenAI(
                model="gpt-4",
                api_key=config.get('api_keys', {}).get('openai')
            ),
            'Claude-3': ChatAnthropic(
                model="claude-3-opus-20240229",
                api_key=config.get('api_keys', {}).get('anthropic')
            ),
            'Gemini-Pro': ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=config.get('api_keys', {}).get('google')
            )
        }
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful desktop agent assistant."),
            ("user", "{input}")
        ])
        
    async def process_message(self, message: str, model_name: str) -> str:
        try:
            model = self.models.get(model_name)
            if not model:
                return f"Error: Model {model_name} not found"
                
            chain = self.prompt | model
            response = await chain.ainvoke({"input": message})
            return response.content
            
        except Exception as e:
=======
# -*- coding: utf-8 -*-
"""LangChain integration module."""

from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

class LangChainManager:
    def __init__(self, config):
        self.config = config
        self.models = {
            'GPT-4': ChatOpenAI(
                model="gpt-4",
                api_key=config.get('api_keys', {}).get('openai')
            ),
            'Claude-3': ChatAnthropic(
                model="claude-3-opus-20240229",
                api_key=config.get('api_keys', {}).get('anthropic')
            ),
            'Gemini-Pro': ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=config.get('api_keys', {}).get('google')
            )
        }
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful desktop agent assistant."),
            ("user", "{input}")
        ])
        
    async def process_message(self, message: str, model_name: str) -> str:
        try:
            model = self.models.get(model_name)
            if not model:
                return f"Error: Model {model_name} not found"
                
            chain = self.prompt | model
            response = await chain.ainvoke({"input": message})
            return response.content
            
        except Exception as e:
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
            return f"Error processing message: {str(e)}" 
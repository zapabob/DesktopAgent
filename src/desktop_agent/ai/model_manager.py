# -*- coding: utf-8 -*-
"""AI model manager module."""

from typing import Dict, Any, List, Optional
import time
from langchain.llms import VertexAI, OpenAI, Anthropic
from langchain.callbacks import get_openai_callback
from ..database.models import AIModelMetrics
from sqlalchemy.orm import Session

class AIModelManager:
    """AIモデルマネージャー"""
    def __init__(self, db_session: Session, config: Dict[str, Any]):
        self.db_session = db_session
        self.config = config
        self.models = {}
        self.metrics = {}
        self._initialize_models()
        
    def _initialize_models(self):
        """モデルの初期化"""
        # Google AI Studio
        if self.config.get('use_vertexai', True):
            self.models['vertexai'] = VertexAI()
            
        # OpenAI (オプション)
        if self.config.get('use_openai'):
            self.models['openai'] = OpenAI(
                api_key=self.config['openai_api_key']
            )
            
        # Anthropic (オプション)
        if self.config.get('use_anthropic'):
            self.models['anthropic'] = Anthropic(
                api_key=self.config['anthropic_api_key']
            )
            
    async def get_best_model(self) -> str:
        """最適なモデルの選択"""
        best_model = None
        best_score = float('-inf')
        
        for model_name in self.models.keys():
            metrics = self.db_session.query(AIModelMetrics)\
                .filter_by(model_name=model_name)\
                .order_by(AIModelMetrics.timestamp.desc())\
                .first()
                
            if metrics:
                # スコアの計算 (応答時間、成功率、コストのバランス)
                score = (
                    metrics.success_rate * 0.5 -
                    metrics.response_time * 0.3 -
                    metrics.cost * 0.2
                )
                
                if score > best_score:
                    best_score = score
                    best_model = model_name
                    
        return best_model or 'vertexai'  # デフォルトはVertexAI
        
    async def execute_with_fallback(self, 
                                  prompt: str,
                                  model_name: Optional[str] = None) -> str:
        """フォールバック機能付きモデル実行"""
        if not model_name:
            model_name = await self.get_best_model()
            
        start_time = time.time()
        success = False
        response = None
        cost = 0
        
        try:
            model = self.models[model_name]
            
            with get_openai_callback() as cb:
                response = await model.agenerate([prompt])
                cost = cb.total_cost
                
            success = True
            
        except Exception as e:
            # フォールバック
            for fallback_model in self.models.keys():
                if fallback_model != model_name:
                    try:
                        response = await self.models[fallback_model]\
                            .agenerate([prompt])
                        model_name = fallback_model
                        success = True
                        break
                    except:
                        continue
                        
        finally:
            # メトリクスの記録
            response_time = time.time() - start_time
            self._record_metrics(
                model_name,
                response_time,
                success,
                cost
            )
            
        if not success:
            raise Exception("全てのモデルが失敗しました")
            
        return response.generations[0][0].text
        
    def _record_metrics(self,
                       model_name: str,
                       response_time: float,
                       success: bool,
                       cost: float):
        """メトリクスの記録"""
        metrics = AIModelMetrics(
            model_name=model_name,
            response_time=response_time,
            success_rate=1.0 if success else 0.0,
            cost=cost
        )
        
        try:
            self.db_session.add(metrics)
            self.db_session.commit()
        except:
            self.db_session.rollback() 
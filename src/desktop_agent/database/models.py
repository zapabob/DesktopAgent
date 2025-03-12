# -*- coding: utf-8 -*-
"""Database models."""

from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class AgentLog(Base):
    """エージェントログモデル"""
    __tablename__ = 'agent_logs'
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(String(50))
    action = Column(String(100))
    timestamp = Column(DateTime, default=datetime.utcnow)
    extra_data = Column(JSON)
    
class TrainingData(Base):
    """学習データモデル"""
    __tablename__ = 'training_data'
    
    id = Column(Integer, primary_key=True)
    data_type = Column(String(50))
    content = Column(JSON)
    embedding = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
class AgentCommunication(Base):
    """エージェント間通信モデル"""
    __tablename__ = 'agent_communications'
    
    id = Column(Integer, primary_key=True)
    sender_id = Column(String(50))
    receiver_id = Column(String(50))
    message_type = Column(String(50))
    content = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20))
    
class AIModelMetrics(Base):
    """AIモデルメトリクスモデル"""
    __tablename__ = 'ai_model_metrics'
    
    id = Column(Integer, primary_key=True)
    model_name = Column(String(100))
    response_time = Column(Float)
    success_rate = Column(Float)
    cost = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow) 
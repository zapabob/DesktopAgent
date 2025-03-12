# -*- coding: utf-8 -*-
"""Database initialization module."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

def init_database(db_url: str = "sqlite:///desktop_agent.db"):
    """データベースの初期化"""
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    return Session() 
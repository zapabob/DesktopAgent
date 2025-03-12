<<<<<<< HEAD
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
=======
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
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
    return Session() 
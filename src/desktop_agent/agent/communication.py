<<<<<<< HEAD
# -*- coding: utf-8 -*-
"""Agent communication module."""

from typing import Dict, Any, List
import asyncio
from datetime import datetime
from ..database.models import AgentCommunication
from sqlalchemy.orm import Session
from sqlalchemy import and_

class AgentCommunicationManager:
    """エージェント間通信マネージャー"""
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.message_handlers = {}
        
    async def send_message(self,
                          sender_id: str,
                          receiver_id: str,
                          message_type: str,
                          content: Dict[str, Any]):
        """メッセージの送信"""
        try:
            message = AgentCommunication(
                sender_id=sender_id,
                receiver_id=receiver_id,
                message_type=message_type,
                content=content,
                status='pending'
            )
            
            self.db_session.add(message)
            self.db_session.commit()
            
            # 非同期でメッセージを処理
            asyncio.create_task(
                self._process_message(message.id)
            )
            
        except Exception as e:
            self.db_session.rollback()
            raise e
            
    async def register_handler(self,
                             agent_id: str,
                             message_type: str,
                             handler):
        """メッセージハンドラーの登録"""
        if agent_id not in self.message_handlers:
            self.message_handlers[agent_id] = {}
            
        self.message_handlers[agent_id][message_type] = handler
        
    async def get_messages(self,
                          agent_id: str,
                          status: str = None) -> List[Dict[str, Any]]:
        """メッセージの取得"""
        query = self.db_session.query(AgentCommunication)\
            .filter(
                and_(
                    AgentCommunication.receiver_id == agent_id,
                    AgentCommunication.status != 'completed'
                )
            )
            
        if status:
            query = query.filter(AgentCommunication.status == status)
            
        messages = query.all()
        return [
            {
                'id': msg.id,
                'sender_id': msg.sender_id,
                'message_type': msg.message_type,
                'content': msg.content,
                'timestamp': msg.timestamp,
                'status': msg.status
            }
            for msg in messages
        ]
        
    async def _process_message(self, message_id: int):
        """メッセージの処理"""
        try:
            message = self.db_session.query(AgentCommunication)\
                .filter_by(id=message_id)\
                .first()
                
            if not message:
                return
                
            # ハンドラーの取得と実行
            handler = self.message_handlers.get(message.receiver_id, {})\
                .get(message.message_type)
                
            if handler:
                message.status = 'processing'
                self.db_session.commit()
                
                try:
                    await handler(message.content)
                    message.status = 'completed'
                except Exception as e:
                    message.status = 'failed'
                    message.content['error'] = str(e)
                    
                self.db_session.commit()
                
        except Exception as e:
            self.db_session.rollback()
=======
# -*- coding: utf-8 -*-
"""Agent communication module."""

from typing import Dict, Any, List
import asyncio
from datetime import datetime
from ..database.models import AgentCommunication
from sqlalchemy.orm import Session
from sqlalchemy import and_

class AgentCommunicationManager:
    """エージェント間通信マネージャー"""
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.message_handlers = {}
        
    async def send_message(self,
                          sender_id: str,
                          receiver_id: str,
                          message_type: str,
                          content: Dict[str, Any]):
        """メッセージの送信"""
        try:
            message = AgentCommunication(
                sender_id=sender_id,
                receiver_id=receiver_id,
                message_type=message_type,
                content=content,
                status='pending'
            )
            
            self.db_session.add(message)
            self.db_session.commit()
            
            # 非同期でメッセージを処理
            asyncio.create_task(
                self._process_message(message.id)
            )
            
        except Exception as e:
            self.db_session.rollback()
            raise e
            
    async def register_handler(self,
                             agent_id: str,
                             message_type: str,
                             handler):
        """メッセージハンドラーの登録"""
        if agent_id not in self.message_handlers:
            self.message_handlers[agent_id] = {}
            
        self.message_handlers[agent_id][message_type] = handler
        
    async def get_messages(self,
                          agent_id: str,
                          status: str = None) -> List[Dict[str, Any]]:
        """メッセージの取得"""
        query = self.db_session.query(AgentCommunication)\
            .filter(
                and_(
                    AgentCommunication.receiver_id == agent_id,
                    AgentCommunication.status != 'completed'
                )
            )
            
        if status:
            query = query.filter(AgentCommunication.status == status)
            
        messages = query.all()
        return [
            {
                'id': msg.id,
                'sender_id': msg.sender_id,
                'message_type': msg.message_type,
                'content': msg.content,
                'timestamp': msg.timestamp,
                'status': msg.status
            }
            for msg in messages
        ]
        
    async def _process_message(self, message_id: int):
        """メッセージの処理"""
        try:
            message = self.db_session.query(AgentCommunication)\
                .filter_by(id=message_id)\
                .first()
                
            if not message:
                return
                
            # ハンドラーの取得と実行
            handler = self.message_handlers.get(message.receiver_id, {})\
                .get(message.message_type)
                
            if handler:
                message.status = 'processing'
                self.db_session.commit()
                
                try:
                    await handler(message.content)
                    message.status = 'completed'
                except Exception as e:
                    message.status = 'failed'
                    message.content['error'] = str(e)
                    
                self.db_session.commit()
                
        except Exception as e:
            self.db_session.rollback()
>>>>>>> 42de7d643d987d98855d441372a3931e7de31809
            raise e 
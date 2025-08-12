"""Database models"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, Float, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from src.database.connection import Base


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    whatsapp_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(255))
    email = Column(String(255))
    student_id = Column(String(50))
    course = Column(String(255))
    year_of_study = Column(Integer)
    campus = Column(String(100))
    preferences = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_users_whatsapp_id', 'whatsapp_id'),
        Index('idx_users_student_id', 'student_id'),
    )


class Conversation(Base):
    """Conversation model"""
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_whatsapp_id = Column(String(50), nullable=False)
    session_id = Column(String(100), nullable=False)
    status = Column(String(50), default="active")  # active, completed, archived
    context = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_conversations_user_whatsapp_id', 'user_whatsapp_id'),
        Index('idx_conversations_session_id', 'session_id'),
        Index('idx_conversations_status', 'status'),
    )


class Message(Base):
    """Message model"""
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), nullable=False)
    user_whatsapp_id = Column(String(50), nullable=False)
    message_type = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    metadata = Column(JSON, default=dict)
    vector_results = Column(JSON)
    web_search_results = Column(JSON)
    mcp_results = Column(JSON)
    confidence_score = Column(Float)
    processing_time = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_messages_conversation_id', 'conversation_id'),
        Index('idx_messages_user_whatsapp_id', 'user_whatsapp_id'),
        Index('idx_messages_created_at', 'created_at'),
        Index('idx_messages_type', 'message_type'),
    )


class GuardrailLog(Base):
    """Guardrail violation log"""
    __tablename__ = "guardrail_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_whatsapp_id = Column(String(50), nullable=False)
    violation_type = Column(String(100), nullable=False)
    user_message = Column(Text, nullable=False)
    rule_triggered = Column(String(255))
    severity = Column(String(20))  # low, medium, high, critical
    action_taken = Column(String(100))  # blocked, warned, redirected
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_guardrail_logs_user_whatsapp_id', 'user_whatsapp_id'),
        Index('idx_guardrail_logs_violation_type', 'violation_type'),
        Index('idx_guardrail_logs_severity', 'severity'),
        Index('idx_guardrail_logs_created_at', 'created_at'),
    )


class KnowledgeUpdate(Base):
    """Knowledge base update tracking"""
    __tablename__ = "knowledge_updates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(100), nullable=False)  # vector_db, web_search, manual
    content_type = Column(String(100))  # course_info, policy, procedure, etc.
    content_id = Column(String(255))
    update_type = Column(String(50))  # create, update, delete
    old_content = Column(Text)
    new_content = Column(Text)
    confidence_score = Column(Float)
    verified = Column(Boolean, default=False)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_knowledge_updates_source', 'source'),
        Index('idx_knowledge_updates_content_type', 'content_type'),
        Index('idx_knowledge_updates_verified', 'verified'),
        Index('idx_knowledge_updates_created_at', 'created_at'),
    )


class Analytics(Base):
    """Analytics and metrics"""
    __tablename__ = "analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_type = Column(String(100), nullable=False)
    metric_name = Column(String(255), nullable=False)
    value = Column(Float, nullable=False)
    dimensions = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_analytics_metric_type', 'metric_type'),
        Index('idx_analytics_metric_name', 'metric_name'),
        Index('idx_analytics_timestamp', 'timestamp'),
    )
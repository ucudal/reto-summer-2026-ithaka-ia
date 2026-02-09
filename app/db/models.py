from sqlalchemy import Column, Float, Integer, String, DateTime, ForeignKey, JSON, func, Text
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .config.database import Base


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())

    messages = relationship("Message", back_populates="conversation")
    postulations = relationship("Postulation", back_populates="conversation")
    wizard_sessions = relationship(
        "WizardSession", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conv_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    role = Column(String(50), nullable=False)
    content = Column(String, nullable=False)
    ts = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")


class Postulation(Base):
    __tablename__ = "postulations"
    id = Column(Integer, primary_key=True, index=True)
    conv_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    payload_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    creatividad = Column(Integer, nullable=True)
    claridad = Column(Integer, nullable=True)
    compromiso = Column(Integer, nullable=True)
    score_total = Column(Float, nullable=True)
    conversation = relationship("Conversation", back_populates="postulations")


class FAQEmbedding(Base):
    __tablename__ = "faq_embeddings"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, nullable=False)
    answer = Column(Text, nullable=False)
    embedding = Column(Vector(1536))  # OpenAI embeddings dimension
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WizardSession(Base):
    __tablename__ = "wizard_sessions"
    id = Column(Integer, primary_key=True, index=True)
    conv_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    current_question = Column(Integer, default=1)
    responses = Column(JSON, default={})
    # ACTIVE, PAUSED, COMPLETED, CANCELLED
    state = Column(String(50), default="ACTIVE")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    conversation = relationship(
        "Conversation", back_populates="wizard_sessions")

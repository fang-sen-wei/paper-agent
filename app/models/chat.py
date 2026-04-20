from enum import Enum

from sqlalchemy import JSON, Boolean, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ChatMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Chat")
    created_at: Mapped[object] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False)
    role: Mapped[ChatMessageRole] = mapped_column(
        SqlEnum(ChatMessageRole, native_enum=False),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    used_web_search: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[object] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    session: Mapped["ChatSession"] = relationship(back_populates="messages")

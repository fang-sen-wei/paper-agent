from enum import Enum

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ChatMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Chat")

    # Day7/8 新增：
    # 这里保存 Claude SDK 返回的真实会话 id。
    # 之后无论服务是否重启，我们都可以用这个 id 做 resume，
    # 从而把“同一个聊天窗口”恢复到同一个 Claude 会话里。
    claude_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # 中文说明：会话级文档范围。None 表示搜索全部已索引文献；有值时只检索指定文档。
    document_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 中文说明：会话级联网开关，发送消息时默认沿用它，避免每一轮都重复传参。
    web_search_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

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
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id"), nullable=False
    )
    role: Mapped[ChatMessageRole] = mapped_column(
        SqlEnum(ChatMessageRole, native_enum=False),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 这里继续沿用你之前的设计：
    # assistant 消息会把 citations 结构化地存下来，
    # 这样后面前端刷新页面时，仍然能展示引用来源。
    citations_json: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)

    used_web_search: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[object] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    session: Mapped["ChatSession"] = relationship(back_populates="messages")

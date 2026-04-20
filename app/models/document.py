from enum import Enum

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# 文档的状态，枚举类型
class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# 文档模型，对应数据库中的documents表


class Document(Base):
    """
    文档模型，对应数据库中的documents表
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        SqlEnum(DocumentStatus, native_enum=False),
        default=DocumentStatus.PENDING,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        # 中文说明：这里显式声明关联条件，避免在移除数据库物理外键后 ORM 无法自动推断 join。
        primaryjoin="Document.id == foreign(DocumentChunk.document_id)",
        foreign_keys="DocumentChunk.document_id",
    )


class DocumentChunk(Base):
    """
    文档块模型，对应数据库中的document_chunks表
    """

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 中文说明：document_id 只保留为普通字段，父子一致性改由应用层校验与删除流程维护。
    document_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    # 文档和chunk是一对多的关系
    document: Mapped["Document"] = relationship(
        back_populates="chunks",
        primaryjoin="foreign(DocumentChunk.document_id) == Document.id",
        foreign_keys=[document_id],
    )

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk


async def get_document_or_404(db: AsyncSession, document_id: int) -> Document:
    """
    中文说明：虚拟外键模式下，写入 chunk 前要先到应用层确认文档是否存在。
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在，无法继续操作切片。",
        )

    return document


async def delete_document_with_chunks(db: AsyncSession, document_id: int) -> None:
    """
    中文说明：删除文档时先手动清理所有切片，再删主文档，替代数据库物理外键的约束行为。
    """
    document = await get_document_or_404(db, document_id)

    try:
        await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        await db.delete(document)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

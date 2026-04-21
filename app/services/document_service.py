from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.chunk_service import build_chunks
from app.services.embedding_service import EmbeddingService
from app.services.parser_service import parse_document_file
from app.services.vector_service import VectorService

async def get_document_or_404(db: AsyncSession, document_id: int) -> Document:
    """
    中文说明：虚拟外键模式下，写入 chunk 前要先到应用层确认文档是否存在。
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
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


async def process_document_and_save_chunks(
    db: AsyncSession,
    document_id: int,
) -> tuple[Document, int]:
    """
    Day4 核心函数：
    1. 把文档状态更新为 processing
    2. 解析文件
    3. 切块
    4. 把 chunks 写进 document_chunks 表
    5. 更新文档状态为 completed / failed
    """

    document = await get_document_or_404(db, document_id)

    # 先把状态更新为 processing
    document.status = DocumentStatus.PROCESSING
    document.error_message = None
    await db.commit()
    await db.refresh(document)

    try:
        # 第一步：解析文件
        sections = parse_document_file(document.file_path)
        if not sections:
            raise ValueError("文档解析后没有得到可用文本。")

        # 第二步：切块
        chunks = build_chunks(
            sections=sections,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        if not chunks:
            raise ValueError("文档切块后没有得到可用内容。")

        # 为了支持重复处理，先清空旧 chunk
        await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )

        # 把新 chunk 写入数据库
        for chunk in chunks:
            db.add(
                DocumentChunk(
                    document_id=document_id,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    text=chunk.text,
                )
            )

        # 更新文档状态
        document.status = DocumentStatus.COMPLETED
        document.error_message = None

        await db.commit()
        await db.refresh(document)

        return document, len(chunks)

    except Exception as exc:
        # 先回滚当前事务
        await db.rollback()

        # 重新查询文档对象，再把状态改为失败
        document = await get_document_or_404(db, document_id)
        document.status = DocumentStatus.FAILED
        document.error_message = str(exc)

        await db.commit()
        await db.refresh(document)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文档处理失败：{exc}",
        )


async def list_document_chunks(
    db: AsyncSession,
    document_id: int,
) -> list[DocumentChunk]:
    """
    获取某个文档的全部 chunks，方便我们在 Day4 做验证。
    """
    # 先确认文档存在，避免查一个不存在的 id
    await get_document_or_404(db, document_id)

    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
    )
    return list(result.scalars().all())


async def index_document_chunks_to_qdrant(
    db: AsyncSession,
    document_id: int,
) -> int:
    """
    Day5 核心函数：
    1. 从 MySQL 读取 chunks
    2. 调 embedding 服务生成向量
    3. 写入 Qdrant
    4. 回写 qdrant_point_id
    """
    document = await get_document_or_404(db, document_id)

    # 这里限制一下流程，防止用户跳过 Day4 直接做 Day5
    if document.status != DocumentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先完成文档解析与切块，再执行向量化。",
        )
    #查询该document-id 的所有的chunks
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
    )

    chunks = list(result.scalars().all())

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前文档还没有可向量化的 chunks。",
        )

    embedding_service = EmbeddingService()
    vector_service = VectorService()

    try:
        vectors: list[list[float]] = []

        # 分批调用 embedding，避免一次请求过大
        for start in range(0, len(chunks), settings.EMBEDDING_BATCH_SIZE):
            batch_chunks = chunks[start : start + settings.EMBEDDING_BATCH_SIZE]
            batch_texts = [chunk.text for chunk in batch_chunks]

            batch_vectors = await embedding_service.embed_texts(batch_texts)
            vectors.extend(batch_vectors)

        if len(vectors) != len(chunks):
            raise ValueError("最终生成的向量数量和 chunk 数量不一致。")

        # 确保 Qdrant collection 存在
        await vector_service.ensure_collection()

        # 把 points 写入 Qdrant
        await vector_service.upsert_document_chunks(document, chunks, vectors)

        # 回写 point id，方便后面调试和展示。
        # 这里存回 MySQL 时保留字符串形式即可，
        # 但真正发给 Qdrant 的时候必须是整数 chunk.id。
        for chunk in chunks:
            chunk.qdrant_point_id = str(chunk.id)

        await db.commit()

        return len(chunks)

    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文档向量化失败：{exc}",
        )

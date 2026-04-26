from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.document import Document, DocumentStatus
from app.models.schemas import (
    CitationItem,
    DocumentChunkItem,
    DocumentDeleteResponse,
    DocumentIndexResponse,
    DocumentItem,
    DocumentProcessResponse,
    DocumentUploadResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from app.services.citation_service import build_citations
from app.services.document_service import (
    delete_document_with_chunks,
    index_document_chunks_to_qdrant,
    list_document_chunks,
    process_document_and_save_chunks,
)
from app.services.file_service import save_upload_file, validate_upload_file
from app.services.retrieval_service import RetrievalService

router = APIRouter(prefix="/documents")


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_file(
    files: Annotated[list[UploadFile], File(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentUploadResponse:
    """
    上传文档接口。

    Day3 只做三件事：
    1. 校验文件数量和类型
    2. 保存文件到本地
    3. 写入 documents 表
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="至少上传一个文件",
        )

    if len(files) > settings.MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="超过文件上传数目"
        )

    created_documents: list[Document] = []

    try:
        for upload_file in files:
            # 先做个文件校验
            _ = validate_upload_file(upload_file)

            # 保存文件到服务器本地
            saved_path = await save_upload_file(upload_file)

            document = Document(
                filename=upload_file.filename or "unknown",
                content_type=upload_file.content_type or "application/octet-stream",
                file_path=saved_path,
                status=DocumentStatus.PENDING,
            )

            # 存到数据库
            db.add(document)
            created_documents.append(document)

        # 统一提交事务
        await db.commit()

        # 提交后刷新对象，确保拿到数据库生成的 id、created_at 等字段
        for document in created_documents:
            await db.refresh(document)

        return DocumentUploadResponse(
            message="文件上传成功，已写入数据库。",
            documents=[DocumentItem.model_validate(doc) for doc in created_documents],
        )

    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="上传文档失败，请稍后重试。",
        )


@router.get("/list", response_model=list[DocumentItem])
async def list_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DocumentItem]:
    """
    获取文档列表接口。

    这个接口很有用：
    - 方便你验证上传是否成功
    - 后面前端做文档列表页时也直接会用到
    """

    result = await db.execute(select(Document).order_by(Document.created_at.desc()))

    documents = result.scalars().all()

    return [DocumentItem.model_validate(doc) for doc in documents]


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentDeleteResponse:
    """
    删除文档接口。

    中文说明：虚拟外键模式下，这里必须先清理 chunk，再删除主文档，
    否则 document_chunks 会留下孤儿数据。
    """
    try:
        await delete_document_with_chunks(db, document_id)
        return DocumentDeleteResponse(message="文档及其切片删除成功。")
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除文档失败，请稍后重试。",
        )


@router.post("/{document_id}/process", response_model=DocumentProcessResponse)
async def process_document(
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentProcessResponse:
    """
    文档处理接口。

    它会完成：
    1. 解析文件
    2. 切块
    3. 保存 chunks
    4. 写入 Qdrant 向量库
    5. 更新文档状态
    """
    document, chunk_count = await process_document_and_save_chunks(db, document_id)
    await index_document_chunks_to_qdrant(db, document_id)
    await db.refresh(document)

    return DocumentProcessResponse(
        message="文档解析、切块与向量索引完成。",
        document=DocumentItem.model_validate(document),
        chunk_count=chunk_count,
    )


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkItem])
async def get_document_chunks(
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DocumentChunkItem]:
    """
    获取某个文档的 chunks。

    这个接口是 Day4 非常重要的验证工具：
    你可以直接看每个 chunk 是怎么切出来的。
    """
    chunks = await list_document_chunks(db, document_id)
    return [DocumentChunkItem.model_validate(chunk) for chunk in chunks]


@router.post("/{document_id}/index", response_model=DocumentIndexResponse)
async def index_document(
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentIndexResponse:
    """
    Day5 文档向量化接口。

    它会完成：
    1. 读取 chunks
    2. 调 embedding 服务
    3. 写入 Qdrant
    4. 回写 qdrant_point_id
    """
    chunk_count = await index_document_chunks_to_qdrant(db, document_id)

    return DocumentIndexResponse(
        message="文档向量化并写入 Qdrant 成功。",
        document_id=document_id,
        chunk_count=chunk_count,
        collection_name=settings.QDRANT_COLLECTION_NAME,
    )


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
) -> SearchResponse:
    """
    Day6 检索接口。

    它会完成：
    1. 把问题转成向量
    2. 去 Qdrant 检索相似 chunks
    3. 组装引用信息
    """
    retrieval_service = RetrievalService()

    results = await retrieval_service.retrieve(
        question=request.question,
        top_k=request.top_k,
        document_id=request.document_id,
    )

    citations = build_citations(results)

    return SearchResponse(
        question=request.question,
        top_k=request.top_k or settings.RETRIEVAL_TOP_K,
        results=[
            SearchResultItem(
                chunk_id=item.chunk_id,
                document_id=item.document_id,
                filename=item.filename,
                page_number=item.page_number,
                text=item.text,
                score=round(item.score, 4),
            )
            for item in results
        ],
        citations=[
            CitationItem(
                index=item["index"],
                chunk_id=item["chunk_id"],
                document_id=item["document_id"],
                filename=item["filename"],
                page_number=item["page_number"],
                text_preview=item["text_preview"],
                score=item["score"],
            )
            for item in citations
        ],
    )

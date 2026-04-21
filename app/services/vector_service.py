from fastapi import HTTPException, status
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from app.core.config import settings
from app.models.document import Document, DocumentChunk


class VectorService:
    """
    中文说明：
    这个服务专门负责和 Qdrant 交互。

    它主要做两件事：
    1. 确保 collection 存在
    2. 把 chunk 向量写入 Qdrant
    """

    def __init__(self) -> None:
        """
        初始化 Qdrant 客户端。
        """
        self.client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
            timeout=30,
        )

    async def ensure_collection(self) -> None:
        """
        确保 collection 存在。

        如果 collection 不存在，就自动创建。
        如果已经存在，就顺便检查向量维度是否一致。
        """
        exists = await self.client.collection_exists(settings.QDRANT_COLLECTION_NAME)

        if not exists:
            # collection 不存在时，自动创建
            _ = await self.client.create_collection(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=settings.EMBEDDING_VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )
            return

        try:
            collection_info = await self.client.get_collection(
                settings.QDRANT_COLLECTION_NAME
            )

            current_size = collection_info.config.params.vectors.size
            if current_size != settings.EMBEDDING_VECTOR_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=(
                        f"Qdrant collection 向量维度不匹配。"
                        f"当前 collection={current_size}，"
                        f"配置期望={settings.EMBEDDING_VECTOR_SIZE}。"
                    ),
                )

        except HTTPException:
            raise
        except Exception:
            # 这里不再把所有异常都当成“collection 不存在”，
            # 否则网络错误、认证错误也会被误判成创建 collection。
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="获取 Qdrant collection 信息失败，请检查 QDRANT_URL 和 QDRANT_API_KEY。",
            )

    async def upsert_document_chunks(
        self,
        document: Document,
        chunks: list[DocumentChunk],
        vectors: list[list[float]],
    ) -> None:
        """
        把某个文档的所有 chunks 写入 Qdrant。

        设计说明：
        - point id 直接用 chunk.id，便于回写和排查
        - payload 中保留 document_id、filename、page_number、text
        - 后面做检索时，payload 会直接参与引用组装
        """
        if len(chunks) != len(vectors):
            raise ValueError("chunks 数量和 vectors 数量不一致。")

        points: list[PointStruct] = []

        for chunk, vector in zip(chunks, vectors, strict=True):
            # Qdrant 的 point id 这里直接使用整数。
            # 注意：8 和 "8" 对 Qdrant 来说不是一回事。
            # 它接受无符号整数或 UUID，但不接受这种数字字符串。
            point_id = chunk.id

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "document_id": document.id,
                        "chunk_id": chunk.id,
                        "filename": document.filename,
                        "page_number": chunk.page_number,
                        "text": chunk.text,
                    },
                )
            )

        _ = await self.client.upsert(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points=points,
        )

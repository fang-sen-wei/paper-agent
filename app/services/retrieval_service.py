from dataclasses import dataclass

from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService


@dataclass
class RetrievedChunk:
    """
    检索结果的统一数据结构。

    为什么要自己定义一层：
    - 不要让 API 层直接依赖 Qdrant 原始对象
    - 后面 Day7 给大模型时，也可以直接复用
    """

    chunk_id: int
    document_id: int
    filename: str
    page_number: int | None
    text: str
    score: float


class RetrievalService:
    """
    中文说明：
    这个服务负责完整的检索流程：

    1. 把用户问题转成向量
    2. 去 Qdrant 查询最相关内容
    3. 把结果整理成统一结构
    """

    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()
        self.vector_service = VectorService()

    async def retrieve(
        self,
        question: str,
        top_k: int | None = None,
        document_id: int | None = None,
    ) -> list[RetrievedChunk]:
        """
        执行一次完整检索。
        """
        actual_top_k = top_k or settings.RETRIEVAL_TOP_K

        # 第一步：把问题转成向量
        query_vectors = await self.embedding_service.embed_texts([question])
        query_vector = query_vectors[0]

        # 第二步：去 Qdrant 检索
        points = await self.vector_service.query_similar_chunks(
            query_vector=query_vector,
            top_k=actual_top_k,
            document_id=document_id,
        )

        results: list[RetrievedChunk] = []

        for point in points:
            payload = point.payload or {}

            results.append(
                RetrievedChunk(
                    chunk_id=int(payload["chunk_id"]),
                    document_id=int(payload["document_id"]),
                    filename=str(payload["filename"]),
                    page_number=payload.get("page_number"),
                    text=str(payload["text"]),
                    score=float(point.score),
                )
            )

        return results

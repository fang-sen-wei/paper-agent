import asyncio

from fastapi import HTTPException, status
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

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

    def _format_qdrant_exception(self, exc: Exception) -> str:
        """
        中文说明：
        qdrant-client 某些网络异常直接 str(exc) 会变成空字符串，
        调试时几乎没有信息。

        这里统一改成优先展示 repr(exc)，
        如果底层还有原始异常，也一并带出来，方便定位是代理、TLS 还是网络抖动。
        """
        parts = [repr(exc)]

        root_cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
        if root_cause is not None:
            parts.append(f"root_cause={repr(root_cause)}")

        return " | ".join(parts)

    async def ensure_collection(self) -> None:
        """
        确保 collection 存在。

        如果 collection 不存在，就自动创建。
        如果已经存在，就顺便检查向量维度是否一致，并补齐检索过滤需要的 payload index。
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
            await self._ensure_payload_indexes()
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

            await self._ensure_payload_indexes()

        except HTTPException:
            raise
        except Exception:
            # 这里不再把所有异常都当成“collection 不存在”，
            # 否则网络错误、认证错误也会被误判成创建 collection。
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="获取 Qdrant collection 信息失败，请检查 QDRANT_URL 和 QDRANT_API_KEY。",
            )

    async def _ensure_payload_indexes(self) -> None:
        """
        中文说明：
        当前聊天接口支持按 document_id 过滤检索，
        而 Qdrant Cloud 对过滤字段通常要求先建 payload index。

        这里统一在 collection 准备完成后补齐索引，
        避免只有传 document_id 时接口才突然报 400。
        """
        try:
            await self.client.create_payload_index(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                field_name="document_id",
                field_schema=PayloadSchemaType.INTEGER,
                wait=True,
            )
        except UnexpectedResponse as exc:
            # 中文说明：索引已存在时不需要中断主流程，其余错误继续抛给上层处理。
            response_text = exc.response.text if exc.response is not None else ""
            if "already exists" in response_text.lower():
                return
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "创建 Qdrant payload index 失败："
                    f"{response_text or self._format_qdrant_exception(exc)}"
                ),
            ) from exc
        except ResponseHandlingException as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "连接 Qdrant 创建 payload index 失败："
                    f"{self._format_qdrant_exception(exc)}"
                ),
            ) from exc

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

    async def query_similar_chunks(
        self,
        query_vector: list[float],
        top_k: int,
        document_id: int | None = None,
    ) -> list:
        """
        根据问题向量检索最相似的 chunk。

        说明：
        - 当前 qdrant-client 版本使用 query_points()，不是旧版 search()
        - document_id 可选，用于限定只搜索某个文档
        """
        query_filter = None

        if document_id is not None:
            # 中文说明：调用过滤检索前先确保 payload index 存在，
            # 避免云端 Qdrant 因 document_id 无索引直接拒绝请求。
            await self._ensure_payload_indexes()
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            )

        last_error: Exception | None = None

        for attempt in range(3):
            try:
                response = await self.client.query_points(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=top_k,
                    with_payload=True,
                    with_vectors=False,
                    score_threshold=settings.RETRIEVAL_SCORE_THRESHOLD,
                )
                return response.points
            except (UnexpectedResponse, ResponseHandlingException) as exc:
                last_error = exc

                # 中文说明：
                # 这里主要兜底 Qdrant Cloud 偶发的首次连接失败。
                # 如果马上重试可以成功，就不要把这种瞬时网络抖动直接暴露给用户。
                if attempt < 2:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Qdrant 检索失败：{self._format_qdrant_exception(last_error)}",
        ) from last_error

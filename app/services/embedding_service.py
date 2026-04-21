from fastapi import HTTPException, status
from openai import AsyncOpenAI

from app.core.config import settings


class EmbeddingService:
    """
    中文说明：
    这个服务只做一件事：
    把文本列表发送给 embedding 接口，并返回向量列表。

    这里接的是阿里云百炼的 OpenAI 兼容接口。
    所以我们可以直接使用 openai SDK，而不用自己手写 HTTP 请求。
    """

    def __init__(self) -> None:
        """
        初始化 embedding 客户端。
        """
        self.client = AsyncOpenAI(
            api_key=settings.EMBEDDING_API_KEY,
            base_url=settings.EMBEDDING_BASE_URL,
            timeout=settings.EMBEDDING_TIMEOUT_SECONDS,
        )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        批量生成文本向量。

        输入：
        - texts: 多段文本

        输出：
        - 每段文本对应一个向量
        """
        if not texts:
            return []

        if not settings.EMBEDDING_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="EMBEDDING_API_KEY 未配置，无法生成向量。",
            )

        # 阿里云 text-embedding-v4 单次最多支持 10 条文本。
        # 我们这里再做一层保护，避免错误配置把请求打爆。
        if len(texts) > settings.EMBEDDING_BATCH_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"当前批次文本数量超过限制。"
                    f"请确保单批不超过 EMBEDDING_BATCH_SIZE={settings.EMBEDDING_BATCH_SIZE}。"
                ),
            )

        try:
            response = await self.client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=texts,
                dimensions=settings.EMBEDDING_VECTOR_SIZE,
                encoding_format="float",
            )

            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Embedding 服务返回为空。",
                )

            # 按 index 排序，确保返回顺序与输入 texts 顺序一致。
            sorted_items = sorted(response.data, key=lambda item: item.index)
            vectors = [item.embedding for item in sorted_items]

            if len(vectors) != len(texts):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Embedding 返回数量和输入文本数量不一致。",
                )

            # 再做一层维度校验，避免后面写入 Qdrant 时才报错。
            for vector in vectors:
                if len(vector) != settings.EMBEDDING_VECTOR_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=(
                            f"Embedding 向量维度不匹配。"
                            f"期望 {settings.EMBEDDING_VECTOR_SIZE}，实际 {len(vector)}。"
                        ),
                    )

            return vectors

        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"调用 Embedding 服务失败：{exc}",
            )

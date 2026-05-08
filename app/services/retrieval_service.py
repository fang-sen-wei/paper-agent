import re
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
    说明：
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
        expanded_queries = self._expand_query(question)
        candidate_top_k = max(actual_top_k, settings.RETRIEVAL_CANDIDATE_TOP_K)

        # 中文说明：扩展查询用于提高召回率，尤其适合论文问答里的中英文混合表达。
        query_vectors = await self.embedding_service.embed_texts(expanded_queries)

        points_by_chunk_id: dict[int, RetrievedChunk] = {}

        for query_vector in query_vectors:
            points = await self.vector_service.query_similar_chunks(
                query_vector=query_vector,
                top_k=candidate_top_k,
                document_id=document_id,
            )

            for point in points:
                payload = point.payload or {}
                chunk_id = int(payload["chunk_id"])
                result = RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=int(payload["document_id"]),
                    filename=str(payload["filename"]),
                    page_number=payload.get("page_number"),
                    text=str(payload["text"]),
                    score=float(point.score),
                )

                existing = points_by_chunk_id.get(chunk_id)
                if existing is None or result.score > existing.score:
                    points_by_chunk_id[chunk_id] = result

        reranked_results = self._rerank_chunks(
            question=question,
            chunks=list(points_by_chunk_id.values()),
        )

        return reranked_results[:actual_top_k]

    def _expand_query(self, question: str) -> list[str]:
        """
        说明：生成少量查询变体，提升向量检索的召回面。

        用法示例：
        - 输入“这篇论文的方法有什么创新？”
        - 会额外召回“method contribution novelty”等论文常见英文表达

        这里故意不用 LLM 改写，避免每次检索多一次模型调用；面试时可以说明这是低成本
        query expansion，后续可替换为 HyDE 或 LLM 多查询生成。
        """
        normalized_question = question.strip()
        if not normalized_question:
            return [question]

        expansions = [normalized_question]
        academic_terms = self._matched_academic_terms(normalized_question)
        if academic_terms:
            expansions.append(f"{normalized_question} {' '.join(academic_terms)}")

        # 中文说明：去重并保序，保证扩展查询稳定且不会重复打 embedding。
        deduplicated: list[str] = []
        seen: set[str] = set()
        for item in expansions:
            if item not in seen:
                deduplicated.append(item)
                seen.add(item)

        return deduplicated[: settings.RETRIEVAL_QUERY_EXPANSION_LIMIT]

    def _matched_academic_terms(self, question: str) -> list[str]:
        """
        说明：把论文问答里的中文意图补成英文关键词。

        为什么这样写：
        - 很多论文 chunk 保留英文原文，中文问题直接向量召回可能漏掉同义表达
        - 只做小词表映射，避免为了单次检索引入复杂抽象
        """
        term_map = {
            "方法": ["method", "approach"],
            "创新": ["contribution", "novelty"],
            "贡献": ["contribution"],
            "实验": ["experiment", "evaluation"],
            "结果": ["result", "performance"],
            "数据集": ["dataset", "benchmark"],
            "局限": ["limitation"],
            "结论": ["conclusion"],
            "消融": ["ablation"],
            "指标": ["metric"],
        }
        matched_terms: list[str] = []
        for keyword, terms in term_map.items():
            if keyword in question:
                matched_terms.extend(terms)

        return matched_terms

    def _rerank_chunks(
        self,
        question: str,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """
        中文说明：对扩展召回后的候选片段做轻量重排。

        重排分数 = 原向量相似度 + 关键词覆盖奖励。
        这样既保留语义检索能力，也能把包含关键术语的 chunk 往前排；
        “候选召回后 rerank”，后续可以平滑替换成 BGE reranker 这类交叉编码器。
        """
        query_terms = self._extract_query_terms(question)
        if not query_terms:
            return sorted(chunks, key=lambda item: item.score, reverse=True)

        def rerank_score(chunk: RetrievedChunk) -> float:
            text = chunk.text.lower()
            matched_count = sum(1 for term in query_terms if term in text)
            keyword_bonus = (
                matched_count / len(query_terms) * settings.RERANK_KEYWORD_WEIGHT
            )
            return chunk.score + keyword_bonus

        return sorted(chunks, key=rerank_score, reverse=True)

    def _extract_query_terms(self, question: str) -> list[str]:
        """
        中文说明：提取可用于关键词覆盖的查询词。
        中文连续片段和英文单词都保留，过短英文词丢弃以降低噪声。
        """
        terms = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_-]{2,}", question)
        return [term.lower() for term in terms]

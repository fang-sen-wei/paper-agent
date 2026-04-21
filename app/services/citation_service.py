from app.core.config import settings
from app.services.retrieval_service import RetrievedChunk


def build_citations(results: list[RetrievedChunk]) -> list[dict]:
    """
    把检索结果整理成 citations。

    设计说明：
    - index 从 1 开始，便于以后在回答里写 [1][2][3]
    - text_preview 只保留前一小段，避免返回过长
    """
    citations: list[dict] = []

    for index, item in enumerate(results, start=1):
        preview = item.text[: settings.CITATION_TEXT_PREVIEW_LENGTH].strip()

        citations.append(
            {
                "index": index,
                "chunk_id": item.chunk_id,
                "document_id": item.document_id,
                "filename": item.filename,
                "page_number": item.page_number,
                "text_preview": preview,
                "score": round(item.score, 4),
            }
        )

    return citations

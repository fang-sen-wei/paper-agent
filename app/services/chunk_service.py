from dataclasses import dataclass

from app.services.parser_service import ParsedSection


@dataclass
class ChunkPayload:
    """
    准备写入 document_chunks 表的数据结构。
    """
    chunk_index: int
    page_number: int | None
    text: str


def build_chunks(
    sections: list[ParsedSection],
    chunk_size: int,
    chunk_overlap: int,
) -> list[ChunkPayload]:
    """
    把解析后的 sections 切成更小的 chunks。

    设计选择：
    - 先用最简单、最容易理解的“按字符长度切块”
    - 不跨 section 切块
    - 所以 PDF 的 chunk 会保留页码，TXT / MD 的 chunk 会保留段号
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0。")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap 不能小于 0。")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须小于 chunk_size。")

    chunks: list[ChunkPayload] = []
    global_chunk_index = 0

    for section in sections:
        text = section.text.strip()
        if not text:
            continue

        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(
                    ChunkPayload(
                        chunk_index=global_chunk_index,
                        page_number=section.source_number,
                        text=chunk_text,
                    )
                )
                global_chunk_index += 1

            # 到末尾就停止
            if end >= len(text):
                break

            # 留一点重叠，让上下文不要断得太生硬
            start = end - chunk_overlap

    return chunks

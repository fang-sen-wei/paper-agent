from datetime import datetime

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from app.models.document import DocumentStatus


class DocumentItem(BaseModel):
    """
    单个文档的返回结构。
    以后前端展示文档列表时，就会用这个结构。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    content_type: str
    file_path: str
    status: DocumentStatus
    error_message: str | None
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    """
    上传接口的返回结构。
    这里返回 message + documents，方便前端直接显示上传结果。
    """

    message: str
    documents: list[DocumentItem]


class DocumentDeleteResponse(BaseModel):
    """
    删除文档接口的返回结构。
    """

    message: str


class DocumentChunkItem(BaseModel):
    """
    单个 chunk 的返回结构。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    chunk_index: int
    page_number: int | None
    text: str
    created_at: datetime


class DocumentProcessResponse(BaseModel):
    """
    文档处理接口的返回结构。
    """

    message: str
    document: DocumentItem
    chunk_count: int


class DocumentIndexResponse(BaseModel):
    """
    文档向量化接口的返回结构。
    """

    message: str
    document_id: int
    chunk_count: int
    collection_name: str


class SearchRequest(BaseModel):
    """
    检索接口的请求体。

    document_id 可选：
    - 不传：在整个默认知识库里检索
    - 传了：只在某个 document 的 chunks 中检索
    """

    question: str = Field(..., min_length=1, description="用户提问内容")
    top_k: int | None = Field(None, ge=1, le=20, description="返回多少条结果")
    document_id: int | None = Field(None, description="可选：限定只搜索某个文档")


class SearchResultItem(BaseModel):
    """
    单条检索结果。
    """

    chunk_id: int
    document_id: int
    filename: str
    page_number: int | None
    text: str
    score: float


class CitationItem(BaseModel):
    """
    引用信息结构。
    这是未来 Day7 给大模型和前端都要用到的结构。
    """

    index: int
    chunk_id: int
    document_id: int
    filename: str
    page_number: int | None
    text_preview: str
    score: float


class SearchResponse(BaseModel):
    """
    检索接口返回结构。
    """

    question: str
    top_k: int
    results: list[SearchResultItem]
    citations: list[CitationItem]

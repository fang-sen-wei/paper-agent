from pydantic.config import ConfigDict

from datetime import datetime

from pydantic import BaseModel

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

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schemas import (
    ChatMessageCreateRequest,
    ChatMessageCreateResponse,
    ChatMessageItem,
    ChatSessionCreateRequest,
    ChatSessionDeleteResponse,
    ChatSessionDetailResponse,
    ChatSessionItem,
    ChatSessionUpdateRequest,
    CitationItem,
)
from app.services.chat_service import (
    create_chat_session,
    delete_chat_session,
    get_chat_session_detail,
    list_chat_sessions,
    send_message_in_session,
    update_chat_session,
)

router = APIRouter(prefix="/chat")


def _build_chat_message_item(message) -> ChatMessageItem:
    """
    把 ORM 消息对象转换成 API 响应结构。

    这里单独拆一个函数，是因为数据库里存的是 citations_json，
    但接口层更适合返回结构化的 citations 列表。
    """
    citations = None

    if message.citations_json:
        citations = [
            CitationItem(
                index=item["index"],
                chunk_id=item["chunk_id"],
                document_id=item["document_id"],
                filename=item["filename"],
                page_number=item["page_number"],
                text_preview=item["text_preview"],
                score=item["score"],
            )
            for item in message.citations_json
        ]

    return ChatMessageItem(
        id=message.id,
        session_id=message.session_id,
        role=message.role,
        content=message.content,
        citations=citations,
        used_web_search=message.used_web_search,
        created_at=message.created_at,
    )


@router.post("/sessions", response_model=ChatSessionItem)
async def create_session(
    request: ChatSessionCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatSessionItem:
    """
    创建一个新的聊天会话。
    """
    session = await create_chat_session(
        db=db,
        title=request.title,
        document_id=request.document_id,
        web_search_enabled=request.web_search_enabled,
    )
    return ChatSessionItem.model_validate(session)


@router.get("/sessions", response_model=list[ChatSessionItem])
async def get_sessions(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ChatSessionItem]:
    """
    获取聊天会话列表。
    """
    sessions = await list_chat_sessions(db)
    return [ChatSessionItem.model_validate(item) for item in sessions]


@router.patch("/sessions/{session_id}", response_model=ChatSessionItem)
async def update_session(
    session_id: int,
    request: ChatSessionUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatSessionItem:
    """
    更新聊天会话的标题、默认文档范围和联网搜索开关。
    """
    session = await update_chat_session(
        db=db,
        session_id=session_id,
        title=request.title,
        document_id=request.document_id,
        web_search_enabled=request.web_search_enabled,
    )
    return ChatSessionItem.model_validate(session)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_session_detail(
    session_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatSessionDetailResponse:
    """
    获取某个聊天会话详情，包括消息列表。
    """
    session = await get_chat_session_detail(
        db=db,
        session_id=session_id,
    )

    return ChatSessionDetailResponse(
        session=ChatSessionItem.model_validate(session),
        messages=[_build_chat_message_item(message) for message in session.messages],
    )


@router.post(
    "/sessions/{session_id}/messages", response_model=ChatMessageCreateResponse
)
async def create_message(
    session_id: int,
    request: ChatMessageCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatMessageCreateResponse:
    """
    在某个聊天会话中发送一条消息。

    整体流程：
    1. 当前轮先检索知识库
    2. 再调用 ClaudeSDKClient
    3. 如果该会话已有 claude_session_id，则通过 resume 恢复
    4. 最后把 user / assistant 消息都保存到数据库
    """
    result = await send_message_in_session(
        db=db,
        session_id=session_id,
        question=request.question,
        top_k=request.top_k,
        document_id=request.document_id,
        web_search_enabled=request.web_search_enabled,
    )

    return ChatMessageCreateResponse(
        session_id=result["session_id"],
        claude_session_id=result["claude_session_id"],
        question=result["question"],
        answer=result["answer"],
        retrieved_count=result["retrieved_count"],
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
            for item in result["citations"]
        ],
        used_web_search=result["used_web_search"],
    )


@router.delete("/sessions/{session_id}", response_model=ChatSessionDeleteResponse)
async def delete_session(
    session_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatSessionDeleteResponse:
    """
    删除聊天会话，并一次性删除该会话下的全部历史消息。
    """
    await delete_chat_session(
        db=db,
        session_id=session_id,
    )
    return ChatSessionDeleteResponse(message="聊天会话已删除。")

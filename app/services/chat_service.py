from collections.abc import AsyncIterator

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import ChatMessage, ChatMessageRole, ChatSession
from app.services.document_service import get_document_or_404
from app.services.agent_service import AgentService
from app.services.citation_service import build_citations
from app.services.retrieval_service import RetrievalService


async def create_chat_session(
    db: AsyncSession,
    title: str | None = None,
    document_id: int | None = None,
    web_search_enabled: bool = False,
) -> ChatSession:
    if document_id is not None:
        await get_document_or_404(db, document_id)

    session = ChatSession(
        title=(title or "New Chat").strip() or "New Chat",
        document_id=document_id,
        web_search_enabled=web_search_enabled,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def list_chat_sessions(db: AsyncSession) -> list[ChatSession]:
    result = await db.execute(
        select(ChatSession).order_by(
            ChatSession.updated_at.desc(), ChatSession.id.desc()
        )
    )
    return list(result.scalars().all())


async def get_chat_session_detail(
    db: AsyncSession,
    session_id: int,
) -> ChatSession:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id)
        .options(selectinload(ChatSession.messages))
    )
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="聊天会话不存在。",
        )

    session.messages.sort(key=lambda item: item.created_at)
    return session


async def send_message_in_session(
    db: AsyncSession,
    session_id: int,
    question: str,
    top_k: int | None = None,
    document_id: int | None = None,
    web_search_enabled: bool | None = None,
) -> dict:
    session = await _get_chat_session(db, session_id)
    actual_document_id = document_id if document_id is not None else session.document_id
    actual_web_search_enabled = (
        web_search_enabled
        if web_search_enabled is not None
        else session.web_search_enabled
    )

    retrieval_service = RetrievalService()
    retrieved_chunks = await retrieval_service.retrieve(
        question=question,
        top_k=top_k,
        document_id=actual_document_id,
    )
    citations = build_citations(retrieved_chunks)
    # 中文说明：联网搜索由会话开关显式控制，避免知识库未命中时偷偷联网。
    allow_web_search = actual_web_search_enabled

    agent_result = await AgentService().answer_question(
        question=question,
        retrieved_chunks=retrieved_chunks,
        citations=citations,
        claude_session_id=session.claude_session_id,
        allow_web_search=allow_web_search,
    )

    session.claude_session_id = agent_result.claude_session_id

    user_message = ChatMessage(
        session_id=session.id,
        role=ChatMessageRole.USER,
        content=question,
        citations_json=None,
        used_web_search=False,
    )
    assistant_message = ChatMessage(
        session_id=session.id,
        role=ChatMessageRole.ASSISTANT,
        content=agent_result.answer,
        citations_json=citations,
        used_web_search=agent_result.used_web_search,
    )

    db.add(user_message)
    db.add(assistant_message)
    await db.commit()
    await db.refresh(session)

    return {
        "session_id": session.id,
        "claude_session_id": session.claude_session_id,
        "question": question,
        "answer": agent_result.answer,
        "retrieved_count": len(retrieved_chunks),
        "citations": citations,
        "used_web_search": agent_result.used_web_search,
    }


async def stream_message_in_session(
    db: AsyncSession,
    session_id: int,
    question: str,
    top_k: int | None = None,
    document_id: int | None = None,
    web_search_enabled: bool | None = None,
) -> AsyncIterator[dict]:
    """
    中文说明：以事件流方式完成一次聊天问答。

    事件顺序：
    1. citations：先把本轮检索引用返回给前端，方便界面提前展示来源
    2. delta/tool：Agent 输出文本或调用联网工具时即时推送
    3. done：模型完成后落库，并返回最终完整消息
    """
    session = await _get_chat_session(db, session_id)
    actual_document_id = document_id if document_id is not None else session.document_id
    actual_web_search_enabled = (
        web_search_enabled
        if web_search_enabled is not None
        else session.web_search_enabled
    )

    retrieval_service = RetrievalService()
    retrieved_chunks = await retrieval_service.retrieve(
        question=question,
        top_k=top_k,
        document_id=actual_document_id,
    )
    citations = build_citations(retrieved_chunks)
    yield {
        "event": "citations",
        "data": {
            "retrieved_count": len(retrieved_chunks),
            "citations": citations,
        },
    }

    answer_parts: list[str] = []
    next_claude_session_id = session.claude_session_id
    used_web_search = False

    async for agent_event in AgentService().stream_answer_question(
        question=question,
        retrieved_chunks=retrieved_chunks,
        citations=citations,
        claude_session_id=session.claude_session_id,
        allow_web_search=actual_web_search_enabled,
    ):
        if agent_event.session_id:
            next_claude_session_id = agent_event.session_id
        used_web_search = used_web_search or agent_event.used_web_search

        if agent_event.event == "delta":
            answer_parts.append(agent_event.text)
            yield {
                "event": "delta",
                "data": {"text": agent_event.text},
            }
        elif agent_event.event == "tool":
            yield {
                "event": "tool",
                "data": {"used_web_search": True},
            }

    answer = "".join(answer_parts).strip() or "抱歉，我没有生成有效回答。"
    session.claude_session_id = next_claude_session_id

    user_message = ChatMessage(
        session_id=session.id,
        role=ChatMessageRole.USER,
        content=question,
        citations_json=None,
        used_web_search=False,
    )
    assistant_message = ChatMessage(
        session_id=session.id,
        role=ChatMessageRole.ASSISTANT,
        content=answer,
        citations_json=citations,
        used_web_search=used_web_search,
    )

    db.add(user_message)
    db.add(assistant_message)
    await db.commit()
    await db.refresh(session)

    yield {
        "event": "done",
        "data": {
            "session_id": session.id,
            "claude_session_id": session.claude_session_id,
            "question": question,
            "answer": answer,
            "retrieved_count": len(retrieved_chunks),
            "citations": citations,
            "used_web_search": used_web_search,
        },
    }


async def delete_chat_session(
    db: AsyncSession,
    session_id: int,
) -> None:
    session = await _get_chat_session(db, session_id)
    await db.delete(session)
    await db.commit()


async def update_chat_session(
    db: AsyncSession,
    session_id: int,
    title: str | None = None,
    document_id: int | None = None,
    web_search_enabled: bool | None = None,
) -> ChatSession:
    """
    中文说明：更新会话标题、默认检索文档范围和联网搜索开关。
    document_id=None 表示恢复为“全部文献”。
    """
    session = await _get_chat_session(db, session_id)

    if document_id is not None:
        await get_document_or_404(db, document_id)

    if title is not None:
        session.title = title.strip() or "New Chat"
    session.document_id = document_id
    if web_search_enabled is not None:
        session.web_search_enabled = web_search_enabled

    await db.commit()
    await db.refresh(session)
    return session


async def _get_chat_session(
    db: AsyncSession,
    session_id: int,
) -> ChatSession:
    session = await db.get(ChatSession, session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="聊天会话不存在。",
        )

    return session

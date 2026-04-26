from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import ChatMessage, ChatMessageRole, ChatSession
from app.services.agent_service import AgentService
from app.services.citation_service import build_citations
from app.services.retrieval_service import RetrievalService


async def create_chat_session(
    db: AsyncSession,
    title: str | None = None,
) -> ChatSession:
    session = ChatSession(title=title or "New Chat")
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
    web_search_enabled: bool = False,
) -> dict:
    session = await _get_chat_session(db, session_id)

    retrieval_service = RetrievalService()
    retrieved_chunks = await retrieval_service.retrieve(
        question=question,
        top_k=top_k,
        document_id=document_id,
    )
    citations = build_citations(retrieved_chunks)
    allow_web_search = web_search_enabled or not retrieved_chunks

    print("-------------已执行到这里，session id表示的是主键id的意思------------")

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


async def delete_chat_session(
    db: AsyncSession,
    session_id: int,
) -> None:
    session = await _get_chat_session(db, session_id)
    await db.delete(session)
    await db.commit()


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

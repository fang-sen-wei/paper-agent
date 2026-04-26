import asyncio
import platform
from dataclasses import dataclass

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)
from dotenv import load_dotenv
from fastapi import HTTPException, status

from app.core.config import settings
from app.services.retrieval_service import RetrievedChunk

load_dotenv()


@dataclass
class AgentAnswer:
    answer: str
    claude_session_id: str | None
    used_web_search: bool


class AgentService:
    def __init__(self) -> None:
        self.model = settings.AGENT_MODEL
        self.max_turns = settings.AGENT_MAX_TURNS

    async def answer_question(
        self,
        question: str,
        retrieved_chunks: list[RetrievedChunk],
        citations: list[dict],
        claude_session_id: str | None = None,
        allow_web_search: bool = False,
    ) -> AgentAnswer:
        if not self.model:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AGENT_MODEL 未配置，请先在 .env 中设置模型名称。",
            )

        prompt = self._build_prompt(
            question=question,
            retrieved_chunks=retrieved_chunks,
            citations=citations,
            allow_web_search=allow_web_search,
        )
        options = self._build_options(
            claude_session_id=claude_session_id,
            allow_web_search=allow_web_search,
        )

        print("-----------------===1===---------")
        try:
            answer_parts, next_session_id, used_web_search = await self._run_client(
                prompt=prompt,
                options=options,
                claude_session_id=claude_session_id,
                allow_web_search=allow_web_search,
            )

        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Agent 调用失败：{exc}",
            ) from exc

        answer = "".join(answer_parts).strip()
        if not answer:
            answer = "抱歉，我没有生成有效回答。"

        return AgentAnswer(
            answer=answer,
            claude_session_id=next_session_id,
            used_web_search=used_web_search,
        )

    async def _run_client(
        self,
        prompt: str,
        options: ClaudeAgentOptions,
        claude_session_id: str | None,
        allow_web_search: bool,
    ) -> tuple[list[str], str | None, bool]:
        """
        在兼容的事件循环中运行 Claude SDK。

        Claude SDK 底层会用 asyncio 创建 Claude Code 子进程。Windows 的
        SelectorEventLoop 不支持异步子进程，FastAPI/uvicorn 某些启动方式会使用它，
        所以这里在 Windows 上自动切到独立线程的 ProactorEventLoop，避免接口内报
        `Failed to start Claude Code:` 但独立脚本可运行的差异。
        """
        if self._needs_windows_proactor_loop():
            return await asyncio.to_thread(
                self._run_client_in_proactor_thread,
                prompt,
                options,
                claude_session_id,
                allow_web_search,
            )

        return await self._run_client_in_current_loop(
            prompt=prompt,
            options=options,
            claude_session_id=claude_session_id,
            allow_web_search=allow_web_search,
        )

    def _needs_windows_proactor_loop(self) -> bool:
        """判断当前 Windows 事件循环是否缺少异步子进程能力。"""
        if platform.system() != "Windows":
            return False

        return not isinstance(asyncio.get_running_loop(), asyncio.ProactorEventLoop)

    def _run_client_in_proactor_thread(
        self,
        prompt: str,
        options: ClaudeAgentOptions,
        claude_session_id: str | None,
        allow_web_search: bool,
    ) -> tuple[list[str], str | None, bool]:
        """在线程内创建 ProactorEventLoop，专门用于启动 Claude Code 子进程。"""
        loop = asyncio.ProactorEventLoop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                self._run_client_in_current_loop(
                    prompt=prompt,
                    options=options,
                    claude_session_id=claude_session_id,
                    allow_web_search=allow_web_search,
                )
            )
        finally:
            asyncio.set_event_loop(None)
            loop.close()

    async def _run_client_in_current_loop(
        self,
        prompt: str,
        options: ClaudeAgentOptions,
        claude_session_id: str | None,
        allow_web_search: bool,
    ) -> tuple[list[str], str | None, bool]:
        """执行一次完整的 Agent 请求，并提取回答、会话 ID 与联网使用状态。"""
        answer_parts: list[str] = []
        next_session_id = claude_session_id
        used_web_search = allow_web_search

        async with ClaudeSDKClient(options=options) as client:
            print("-----------------===2===---------")
            await client.query(prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    if message.session_id:
                        next_session_id = message.session_id

                    for block in message.content:
                        if isinstance(block, TextBlock):
                            answer_parts.append(block.text)
                        elif (
                            isinstance(block, ToolUseBlock)
                            and block.name == "WebSearch"
                        ):
                            used_web_search = True

                elif isinstance(message, ResultMessage):
                    if message.session_id:
                        next_session_id = message.session_id
                    if message.is_error:
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail="Agent 调用失败，请检查模型配置或 Claude Agent SDK 输出。",
                        )

        return answer_parts, next_session_id, used_web_search

    def _build_options(
        self,
        claude_session_id: str | None,
        allow_web_search: bool,
    ) -> ClaudeAgentOptions:
        tools = ["Glob", "WebSearch", "WebFetch"] if allow_web_search else ["Glob"]
        env = {
            "ANTHROPIC_BASE_URL": settings.ANTHROPIC_BASE_URL,
            "ANTHROPIC_API_KEY": settings.ANTHROPIC_API_KEY,
        }

        return ClaudeAgentOptions(
            model=self.model,
            allowed_tools=tools,
            system_prompt=self._system_prompt(),
            max_turns=self.max_turns,
            resume=claude_session_id,
            cwd=settings.BASE_DIR,
            setting_sources=["project"],
            env=env,
        )

    def _system_prompt(self) -> str:
        return (
            "你是一位严谨的文献分析助手。优先依据用户上传到知识库的文档片段回答。"
            "回答必须使用中文。引用知识库内容时，在相关句子后标注 [1]、[2] 这样的编号。"
            "如果知识库片段不足以回答，并且本轮允许联网搜索，可以使用 WebSearch 补充，"
            "但必须明确区分知识库内容和联网结果。不要编造引用编号。"
        )

    def _build_prompt(
        self,
        question: str,
        retrieved_chunks: list[RetrievedChunk],
        citations: list[dict],
        allow_web_search: bool,
    ) -> str:
        context_text = self._format_retrieved_context(retrieved_chunks, citations)
        web_search_instruction = (
            "本轮允许使用 WebSearch；只有当知识库内容不足时才联网补充。"
            if allow_web_search
            else "本轮不允许联网搜索；如果知识库内容不足，请直接说明无法从已上传文件中确认。"
        )

        return (
            f"用户问题：\n{question}\n\n"
            f"知识库检索结果：\n{context_text}\n\n"
            f"联网策略：{web_search_instruction}\n\n"
            "回答要求：\n"
            "1. 先基于知识库检索结果回答。\n"
            "2. 使用知识库内容时必须在句尾标注对应编号，例如 [1]。\n"
            "3. 不要引用没有出现在检索结果里的编号。\n"
            "4. 如果使用了联网结果，请单独写出“联网补充：”。\n"
        )

    def _format_retrieved_context(
        self,
        retrieved_chunks: list[RetrievedChunk],
        citations: list[dict],
    ) -> str:
        if not retrieved_chunks:
            return "没有检索到足够相关的知识库片段。"

        parts: list[str] = []
        for chunk, citation in zip(retrieved_chunks, citations, strict=True):
            page = (
                citation["page_number"]
                if citation["page_number"] is not None
                else "无页码"
            )
            parts.append(
                f"[{citation['index']}] 文件：{citation['filename']}；页码/段落：{page}；"
                f"相似度：{citation['score']}\n{chunk.text}"
            )

        return "\n\n".join(parts)

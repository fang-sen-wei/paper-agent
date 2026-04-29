import asyncio
from typing import Any

from claude_agent_sdk import tool
from tavily import TavilyClient

from app.core.config import settings


def _format_tavily_result(result: dict[str, Any]) -> str:
    """将 Tavily 的结构化结果压缩成适合 Agent 阅读的中文文本。"""
    parts: list[str] = []
    answer = result.get("answer")
    if answer:
        parts.append(f"直接答案：{answer}")

    results = result.get("results") or []
    for index, item in enumerate(results, start=1):
        title = item.get("title") or "无标题"
        url = item.get("url") or "无链接"
        content = item.get("content") or item.get("raw_content") or "无摘要"
        parts.append(f"[{index}] {title}\n链接：{url}\n摘要：{content}")

    return "\n\n".join(parts) if parts else "Tavily 没有返回可用结果。"


def _search_tavily(query: str) -> str:
    """同步调用 Tavily；上层 async tool 会放到线程里执行，避免阻塞事件循环。"""
    api_key = settings.TAVILY_API
    if not api_key:
        return "错误：TAVILY_API 未在 .env 文件中配置。"

    client = TavilyClient(api_key=api_key)
    result = client.search(
        query=query,
        search_depth="basic",
        max_results=5,
        include_answer=True,
        include_raw_content=False,
    )
    return _format_tavily_result(result)


@tool(
    "search_with_web",
    "Use Tavily to search the web when local context is insufficient or current external information is required.",
    {"query": str},
)
async def search_with_web(args: dict[str, Any]) -> dict[str, Any]:
    """
    Claude SDK 自定义网页搜索工具，入参 query 为搜索关键词，返回 Tavily 摘要和链接。
    当信息不足时可以使用该tool进行网页搜索补充信息
    """
    query = str(args.get("query", "")).strip()
    if not query:
        return {
            "content": [{"type": "text", "text": "错误：query 不能为空。"}],
            "is_error": True,
        }

    try:
        text = await asyncio.to_thread(_search_tavily, query)
        return {"content": [{"type": "text", "text": text}]}
    except Exception as exc:
        return {
            "content": [{"type": "text", "text": f"Tavily 搜索失败：{exc}"}],
            "is_error": True,
        }

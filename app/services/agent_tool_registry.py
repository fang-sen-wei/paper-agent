from claude_agent_sdk import create_sdk_mcp_server

from app.services.tools import search_with_web

WEB_SEARCH_SERVER_NAME = "web_search"
WEB_SEARCH_TOOL_NAME = "search_with_web"
WEB_SEARCH_TOOL_ID = f"mcp__{WEB_SEARCH_SERVER_NAME}__{WEB_SEARCH_TOOL_NAME}"

# 将 tools.py 中的自定义 tool 包成 Claude SDK 的进程内 MCP server。
web_search_server = create_sdk_mcp_server(
    name=WEB_SEARCH_SERVER_NAME,
    version="1.0.0",
    tools=[search_with_web],
)


def is_web_search_tool(tool_name: str) -> bool:
    """兼容 SDK 返回短工具名或 mcp__server__tool 全名两种情况。"""
    return tool_name in {WEB_SEARCH_TOOL_ID, WEB_SEARCH_TOOL_NAME}

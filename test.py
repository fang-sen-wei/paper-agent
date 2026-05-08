import asyncio

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)
from dotenv import load_dotenv

from app.core.config import settings
from app.services.agent_tool_registry import (
    WEB_SEARCH_SERVER_NAME,
    WEB_SEARCH_TOOL_ID,
    web_search_server,
)

load_dotenv()


Qwen_model = settings.AGENT_MODEL


async def main():
    options = ClaudeAgentOptions(
        model=Qwen_model,
        tools=["Glob"],
        disallowed_tools=["Bash", "Edit"],
        allowed_tools=[
            "Glob",
            WEB_SEARCH_TOOL_ID,
        ],  # Tools Claude can use
        mcp_servers={WEB_SEARCH_SERVER_NAME: web_search_server},
        system_prompt="you are a good helper",
        setting_sources=["project"],
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("deepseekv4pro哪天发布的?")
        async for message in client.receive_response():
            print_response(message)


def print_response(message):
    """Print only the human-readable parts of a message."""
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                print(block.text)
    elif isinstance(message, ResultMessage):
        cost = (
            f"${message.total_cost_usd:.4f}"
            if message.total_cost_usd is not None
            else "N/A"
        )
        print(f"[done: {message.subtype}, cost: {cost}]")


asyncio.run(main())

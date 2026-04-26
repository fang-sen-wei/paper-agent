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

load_dotenv()


Qwen_model = settings.AGENT_MODEL


async def main():

    options = ClaudeAgentOptions(
        model=Qwen_model,
        allowed_tools=["Read", "Edit", "Glob", "WebSearch"],  # Tools Claude can use
        system_prompt="you are a good helper",
        setting_sources=["project"],
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("who are you?")
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

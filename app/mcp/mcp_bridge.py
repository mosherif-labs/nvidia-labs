import asyncio, json, os, sys
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp_types import TextContent
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()  # nearest .env, searching up from this file

nim = AsyncOpenAI(
    base_url=os.environ.get("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=os.environ["NVIDIA_API_KEY"],
)
MODEL = os.environ.get("AGENT_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")


def to_openai(tool):  # MCP tool -> OpenAI/NIM function schema
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema,
        },
    }


async def ask(server_cmd: list[str], question: str, max_steps: int = 6):
    params = StdioServerParameters(command=server_cmd[0], args=server_cmd[1:])
    async with Client(stdio_client(params)) as mcp:
        tools = (await mcp.list_tools()).tools
        print("MCP tools:", [t.name for t in tools])
        schemas = [to_openai(t) for t in tools]
        messages = [{"role": "user", "content": question}]
        for step in range(1, max_steps + 1):
            msg = (
                (
                    await nim.chat.completions.create(
                        model=MODEL,
                        messages=messages,
                        tools=schemas,
                        tool_choice="auto",
                        temperature=1.0,
                        top_p=0.95,
                    )
                )
                .choices[0]
                .message
            )
            messages.append(msg)
            if not msg.tool_calls:
                return msg.content
            for tc in msg.tool_calls:
                result = await mcp.call_tool(
                    tc.function.name, json.loads(tc.function.arguments)
                )
                text = "\n".join(
                    b.text for b in result.content if isinstance(b, TextContent)
                )
                print(
                    f"[{step}] MCP {tc.function.name}({tc.function.arguments}) -> {text[:150]}"
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": ("ERROR: " if result.is_error else "") + text,
                    }
                )
    return None


if __name__ == "__main__":
    # python mcp_bridge.py "<question>" -- <command that starts any stdio MCP server>
    cut = sys.argv.index("--")
    print(asyncio.run(ask(sys.argv[cut + 1 :], " ".join(sys.argv[1:cut]))))

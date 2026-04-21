"""Agent core loop - orchestrates LLM calls and tool execution."""

import json
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from src.llm import LLM
from src.tools import BUILTIN_TOOL_DEFINITIONS, execute_builtin_tool
from src.mcp_client import MCPClient
from src.skills import Skill, get_skill_tool_definitions, execute_skill

console = Console()


class Agent:
    def __init__(self, llm: LLM, mcp_client: MCPClient, skills: dict[str, Skill], system_prompt: str):
        self.llm = llm
        self.mcp_client = mcp_client
        self.skills = skills
        self.system_prompt = system_prompt
        self.messages: list[dict] = [
            {"role": "system", "content": system_prompt}
        ]

    def get_all_tools(self) -> list[dict]:
        """Get combined built-in + MCP + skill tool definitions."""
        return (
            BUILTIN_TOOL_DEFINITIONS
            + self.mcp_client.get_tool_definitions()
            + get_skill_tool_definitions(self.skills)
        )

    async def run(self, user_input: str) -> str:
        """Process user input through the agent loop. Returns assistant text."""
        self.messages.append({"role": "user", "content": user_input})

        while True:
            tools = self.get_all_tools()
            response = self.llm.chat(self.messages, tools=tools if tools else None)

            # Append assistant message
            msg_dict = self._message_to_dict(response)
            self.messages.append(msg_dict)

            # Check if there are tool calls
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    # Execute tool
                    console.print(f"  [dim]⚡ {tool_name}({self._truncate_args(arguments)})[/dim]")
                    result = await self._execute_tool(tool_name, arguments)

                    # Append tool result
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })

                # Continue loop to get LLM response after tool results
                continue
            else:
                # No tool calls - return the text response
                text = response.content or ""
                return text

    async def _execute_tool(self, name: str, arguments: dict) -> str:
        """Route tool execution to built-in, MCP, or skill."""
        if name == "use_skill":
            return execute_skill(
                self.skills,
                arguments.get("skill_name", ""),
                arguments.get("context", ""),
            )
        elif self.mcp_client.is_mcp_tool(name):
            return await self.mcp_client.call_tool(name, arguments)
        else:
            return execute_builtin_tool(name, arguments)

    def clear_history(self):
        """Reset conversation history."""
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def _message_to_dict(self, message) -> dict:
        """Convert OpenAI message object to dict for storage."""
        d = {"role": message.role, "content": message.content}
        if message.tool_calls:
            d["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]
        return d

    def _truncate_args(self, args: dict) -> str:
        """Truncate arguments for display."""
        s = json.dumps(args, ensure_ascii=False)
        if len(s) > 80:
            return s[:77] + "..."
        return s

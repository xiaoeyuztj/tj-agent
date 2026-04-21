"""tj-agent: A lightweight terminal AI coding agent with MCP support."""

import asyncio
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from pathlib import Path

from src.config import load_config, CONFIG_DIR
from src.llm import LLM
from src.mcp_client import MCPClient
from src.agent import Agent
from src.skills import load_skills

console = Console()


BANNER = """[bold cyan]tj-agent[/bold cyan] [dim]v0.1.0[/dim]
[dim]Type your message to chat. Commands: /clear /model /exit[/dim]
"""


async def async_main():
    config = load_config()

    if not config.llm.api_key:
        console.print("[red]Error:[/red] No API key configured.")
        console.print(f"Set OPENAI_API_KEY env var or edit {CONFIG_DIR / 'config.json'}")
        sys.exit(1)

    console.print(BANNER)
    console.print(f"[dim]Model: {config.llm.model} | Base: {config.llm.base_url}[/dim]")

    # Init LLM
    llm = LLM(config.llm)

    # Init MCP client
    mcp_client = MCPClient()
    if config.mcp_servers:
        console.print("[dim]Connecting to MCP servers...[/dim]")
        await mcp_client.connect(config.mcp_servers)
        mcp_tools = mcp_client.get_tool_definitions()
        if mcp_tools:
            tool_names = [t["function"]["name"] for t in mcp_tools]
            console.print(f"[green]MCP tools loaded:[/green] {', '.join(tool_names)}")

    # Load skills
    skills = load_skills()
    if skills:
        console.print(f"[green]Skills loaded:[/green] {', '.join(skills.keys())}")

    # Init Agent
    agent = Agent(llm, mcp_client, skills, config.system_prompt)

    # Setup prompt with history
    history_file = CONFIG_DIR / "history.txt"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    session = PromptSession(history=FileHistory(str(history_file)))

    try:
        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: session.prompt("\n> ")
                )
            except (EOFError, KeyboardInterrupt):
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            # Handle slash commands
            if user_input.startswith("/"):
                handled = handle_command(user_input, agent, config)
                if handled == "exit":
                    break
                continue

            # Run agent
            try:
                with console.status("[bold green]Thinking...", spinner="dots"):
                    response = await agent.run(user_input)
                console.print()
                console.print(Markdown(response))
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted[/yellow]")
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")

    finally:
        await mcp_client.close()
        console.print("\n[dim]Bye![/dim]")


def handle_command(cmd: str, agent: Agent, config) -> str | None:
    """Handle slash commands. Returns 'exit' to quit."""
    parts = cmd.split(maxsplit=1)
    command = parts[0].lower()

    if command in ("/exit", "/quit", "/q"):
        return "exit"
    elif command == "/clear":
        agent.clear_history()
        console.print("[dim]Conversation cleared.[/dim]")
    elif command == "/model":
        if len(parts) > 1:
            agent.llm.model = parts[1]
            console.print(f"[dim]Model switched to: {parts[1]}[/dim]")
        else:
            console.print(f"[dim]Current model: {agent.llm.model}[/dim]")
    elif command == "/tools":
        tools = agent.get_all_tools()
        for t in tools:
            name = t["function"]["name"]
            desc = t["function"].get("description", "")[:60]
            console.print(f"  [cyan]{name}[/cyan] - {desc}")
    elif command == "/help":
        console.print("[dim]/clear - Clear conversation[/dim]")
        console.print("[dim]/model [name] - Show/switch model[/dim]")
        console.print("[dim]/tools - List available tools[/dim]")
        console.print("[dim]/exit - Quit[/dim]")
    else:
        console.print(f"[dim]Unknown command: {command}. Type /help[/dim]")

    return None


def main():
    """Entry point."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

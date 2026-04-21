"""Built-in tools for tj-agent."""

import os
import subprocess
from pathlib import Path


# Tool definitions in OpenAI function calling format
BUILTIN_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file at the given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative file path to read.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates the file if it doesn't exist, overwrites if it does.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative file path to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command and return its output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory for the command. Defaults to current directory.",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories at the given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list. Defaults to current directory.",
                    }
                },
                "required": [],
            },
        },
    },
]


def execute_builtin_tool(name: str, arguments: dict) -> str:
    """Execute a built-in tool and return the result as string."""
    try:
        if name == "read_file":
            return _read_file(arguments["path"])
        elif name == "write_file":
            return _write_file(arguments["path"], arguments["content"])
        elif name == "run_command":
            return _run_command(arguments["command"], arguments.get("cwd"))
        elif name == "list_dir":
            return _list_dir(arguments.get("path", "."))
        else:
            return f"Error: Unknown built-in tool '{name}'"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


def _read_file(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"Error: File not found: {path}"
    if not p.is_file():
        return f"Error: Not a file: {path}"
    return p.read_text(encoding="utf-8")


def _write_file(path: str, content: str) -> str:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Successfully wrote {len(content)} bytes to {path}"


def _run_command(command: str, cwd: str | None = None) -> str:
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=60,
        cwd=cwd,
    )
    output = ""
    if result.stdout:
        output += result.stdout
    if result.stderr:
        output += f"\n[stderr]\n{result.stderr}"
    if result.returncode != 0:
        output += f"\n[exit code: {result.returncode}]"
    return output.strip() or "(no output)"


def _list_dir(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"Error: Directory not found: {path}"
    if not p.is_dir():
        return f"Error: Not a directory: {path}"
    entries = sorted(p.iterdir())
    lines = []
    for entry in entries:
        prefix = "📁 " if entry.is_dir() else "📄 "
        lines.append(f"{prefix}{entry.name}")
    return "\n".join(lines) or "(empty directory)"

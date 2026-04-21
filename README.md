# tj-agent

A lightweight terminal AI coding agent with **MCP (Model Context Protocol)** and **Skills** support. Works with any OpenAI-compatible API (OpenAI, DeepSeek, SiliconFlow, Ollama, etc.).

## Features

- **Interactive REPL** - Claude Code-style terminal interaction with conversation history
- **OpenAI-compatible** - Works with any API that implements the OpenAI chat completions format
- **MCP Support** - Connect to multiple MCP servers and use their tools seamlessly
- **Skills System** - Load reusable prompt templates from markdown files, organized in nested directories
- **Built-in Tools** - File read/write, shell command execution, directory listing
- **Function Calling** - Full support for LLM tool/function calling with automatic routing

## Architecture

```
tj-agent/
├── src/
│   ├── main.py           # Entry point + REPL loop + slash commands
│   ├── agent.py           # Agent core loop (user → LLM → tool calls → results → LLM)
│   ├── llm.py             # OpenAI-compatible API wrapper
│   ├── mcp_client.py      # MCP client for connecting to multiple MCP servers
│   ├── skills.py          # Skills loader (markdown-based prompt templates)
│   ├── tools.py           # Built-in tools (read_file, write_file, run_command, list_dir)
│   └── config.py          # Configuration loading
├── skills/                # Skill definitions (markdown files)
├── config.json            # Runtime config (git-ignored)
├── config.example.json    # Example config template
└── pyproject.toml
```

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Installation

```bash
# Clone the repo
git clone https://github.com/xiaoeyuztj/tj-agent.git
cd tj-agent

# Create venv and install (with uv)
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e .

# Or with pip
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

Copy the example config and fill in your API key:

```bash
cp config.example.json config.json
```

Edit `config.json`:

```json
{
  "llm": {
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-your-api-key-here",
    "model": "gpt-4o"
  },
  "mcp_servers": {},
  "system_prompt": "You are a helpful AI coding assistant."
}
```

### LLM Configuration

| Field | Description | Example |
|-------|-------------|---------|
| `base_url` | API endpoint URL | `https://api.openai.com/v1` |
| `api_key` | API key (also supports `OPENAI_API_KEY` env var) | `sk-xxx` |
| `model` | Model name | `gpt-4o`, `deepseek-chat`, etc. |

**Provider examples:**

```json
// OpenAI
{ "base_url": "https://api.openai.com/v1", "model": "gpt-4o" }

// DeepSeek
{ "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat" }

// SiliconFlow
{ "base_url": "https://api.siliconflow.cn/v1/", "model": "Pro/zai-org/GLM-4.7" }

// Local Ollama
{ "base_url": "http://localhost:11434/v1", "model": "llama3" }
```

### MCP Server Configuration

Add MCP servers in `config.json` to extend the agent with external tools:

```json
{
  "mcp_servers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "ghp_xxx"
      }
    }
  }
}
```

Each MCP server entry supports:

| Field | Description |
|-------|-------------|
| `command` | The command to start the MCP server |
| `args` | Command-line arguments |
| `env` | Optional environment variables |

The agent automatically discovers and registers all tools exposed by connected MCP servers at startup.

## Usage

```bash
# Activate venv
source .venv/bin/activate

# Run the agent
tj-agent
# or
python -m src.main
```

### Interactive Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/clear` | Clear conversation history |
| `/model [name]` | Show or switch the current model |
| `/tools` | List all available tools (built-in + MCP + skills) |
| `/exit` | Quit the agent |

### Example Session

```
tj-agent v0.1.0
Type your message to chat. Commands: /clear /model /exit

Model: gpt-4o | Base: https://api.openai.com/v1

> List all Python files in the current directory

  ⚡ list_dir({"path": "."})
  ⚡ run_command({"command": "find . -name '*.py' -type f"})

Here are the Python files found:
- ./src/main.py
- ./src/agent.py
- ./src/llm.py
...

> /tools
  read_file - Read the contents of a file at the given path.
  write_file - Write content to a file.
  run_command - Execute a shell command and return its output.
  list_dir - List files and directories at the given path.
  use_skill - Invoke a predefined skill/prompt template.
```

## Built-in Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read the contents of a file (supports absolute and relative paths) |
| `write_file` | Write content to a file (creates parent directories if needed) |
| `run_command` | Execute a shell command with optional working directory (60s timeout) |
| `list_dir` | List files and directories at a given path |

## Skills System

Skills are reusable prompt templates stored as markdown files in the `skills/` directory. The LLM can invoke them via the `use_skill` tool during a conversation.

### Creating a Skill

Create a `.md` file in the `skills/` directory:

```markdown
# Code Review

You are a code reviewer. Analyze the provided code and give feedback on:

1. **Bugs & Issues** - Logic errors, potential crashes, edge cases
2. **Code Quality** - Readability, naming, structure
3. **Performance** - Unnecessary allocations, O(n^2) patterns
4. **Security** - Input validation, injection risks

Be concise. Prioritize actionable suggestions.
```

### Nested Skills

Skills can be organized in subdirectories. The directory structure is reflected in the skill name:

```
skills/
├── code-review.md              → "code-review"
├── coding/
│   ├── refactor.md             → "coding/refactor"
│   └── optimize.md             → "coding/optimize"
└── devops/
    └── docker.md               → "devops/docker"
```

### How Skills Work

1. At startup, all `.md` files under `skills/` are loaded recursively
2. The first `# Heading` or first line of each file becomes the skill description
3. Skills are exposed to the LLM as a `use_skill` function tool
4. When the LLM decides to invoke a skill, its markdown content is injected into the conversation as instructions
5. The LLM then follows the skill instructions to complete the task

## Agent Loop

The agent follows a standard ReAct-style loop:

```
User Input
    ↓
Append to messages
    ↓
Call LLM (with all tool definitions)
    ↓
┌─ Has tool_calls? ──→ Execute tools (built-in / MCP / skill)
│       ↓                      ↓
│   Append results         Append results to messages
│       ↓                      ↓
│   Call LLM again ←───────────┘
│
└─ No tool_calls ──→ Return text response
                          ↓
                     Display to user
```

## Development

```bash
# Install in development mode
source .venv/bin/activate
uv pip install -e .

# Run directly
python -m src.main

# Check imports
python -c "from src.agent import Agent; print('OK')"
```

## License

MIT

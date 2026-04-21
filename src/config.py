"""Configuration loading for tj-agent."""

import json
import os
from pathlib import Path
from dataclasses import dataclass, field


CONFIG_DIR = Path(__file__).parent.parent
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "llm": {
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4o",
    },
    "mcp_servers": {},
    "system_prompt": "You are a helpful AI coding assistant. You have access to tools for reading/writing files, running commands, and interacting with MCP servers.",
}


@dataclass
class LLMConfig:
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o"


@dataclass
class MCPServerConfig:
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    mcp_servers: dict[str, MCPServerConfig] = field(default_factory=dict)
    system_prompt: str = DEFAULT_CONFIG["system_prompt"]


def load_config() -> AppConfig:
    """Load config from ~/.tj-agent/config.json, create default if not exists."""
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True)

    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
        return AppConfig()

    raw = json.loads(CONFIG_FILE.read_text())

    llm_raw = raw.get("llm", {})
    # Support env var override for api_key
    api_key = llm_raw.get("api_key", "") or os.environ.get("OPENAI_API_KEY", "")
    llm = LLMConfig(
        base_url=llm_raw.get("base_url", "https://api.openai.com/v1"),
        api_key=api_key,
        model=llm_raw.get("model", "gpt-4o"),
    )

    mcp_servers = {}
    for name, srv in raw.get("mcp_servers", {}).items():
        mcp_servers[name] = MCPServerConfig(
            command=srv.get("command", ""),
            args=srv.get("args", []),
            env=srv.get("env", {}),
        )

    return AppConfig(
        llm=llm,
        mcp_servers=mcp_servers,
        system_prompt=raw.get("system_prompt", DEFAULT_CONFIG["system_prompt"]),
    )

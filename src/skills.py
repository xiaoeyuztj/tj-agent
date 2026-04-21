"""Skills loader - loads markdown skill files as callable prompts."""

import os
from pathlib import Path
from dataclasses import dataclass


SKILLS_DIR = Path(__file__).parent.parent / "skills"


@dataclass
class Skill:
    name: str
    description: str
    content: str


def load_skills() -> dict[str, Skill]:
    """Load all .md files from the skills/ directory, including nested folders.
    
    Nested skills are named with '/' separator, e.g. 'coding/refactor'.
    """
    skills = {}

    if not SKILLS_DIR.exists():
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        return skills

    for file in sorted(SKILLS_DIR.rglob("*.md")):
        # Build skill name from relative path, e.g. coding/refactor
        rel = file.relative_to(SKILLS_DIR)
        name = str(rel.with_suffix("")).replace(os.sep, "/")
        content = file.read_text(encoding="utf-8").strip()

        # Extract description from first line (# Title) or first paragraph
        lines = content.splitlines()
        description = ""
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                description = line.lstrip("#").strip()
                break
            elif line:
                description = line[:100]
                break

        skills[name] = Skill(
            name=name,
            description=description or f"Skill: {name}",
            content=content,
        )

    return skills


def get_skill_tool_definitions(skills: dict[str, Skill]) -> list[dict]:
    """Convert skills to OpenAI function calling format so LLM can invoke them."""
    if not skills:
        return []

    skill_list = "\n".join(f"- {name}: {s.description}" for name, s in skills.items())

    return [
        {
            "type": "function",
            "function": {
                "name": "use_skill",
                "description": f"Invoke a predefined skill/prompt template. Available skills:\n{skill_list}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_name": {
                            "type": "string",
                            "description": "Name of the skill to invoke.",
                            "enum": list(skills.keys()),
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context or input to provide to the skill.",
                        },
                    },
                    "required": ["skill_name"],
                },
            },
        }
    ]


def execute_skill(skills: dict[str, Skill], skill_name: str, context: str = "") -> str:
    """Execute a skill by injecting its content as instructions."""
    skill = skills.get(skill_name)
    if not skill:
        available = ", ".join(skills.keys()) if skills else "(none)"
        return f"Error: Skill '{skill_name}' not found. Available: {available}"

    result = f"[Skill: {skill.name}]\n\n{skill.content}"
    if context:
        result += f"\n\n[User Context]\n{context}"
    return result

"""Load and format prompts from config files."""

from pathlib import Path


def get_prompts_dir() -> Path:
    """Return path to prompts directory."""
    return Path(__file__).resolve().parent.parent.parent / "config" / "prompts"


def load_prompt(name: str) -> str:
    """Load prompt template by name (without .txt)."""
    path = get_prompts_dir() / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def format_prompt(name: str, **kwargs: str) -> str:
    """Load and format prompt with given variables."""
    template = load_prompt(name)
    return template.format(**kwargs)

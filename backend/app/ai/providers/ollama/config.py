from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OllamaConfig:
    name: str = "ollama"
    priority: int = 0
    enabled: bool = True
    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5-coder:7b"
    keep_alive: str = "5m"


ollama_config = OllamaConfig()

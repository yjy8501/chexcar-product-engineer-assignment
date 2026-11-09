"""지식 문서(용어집, 규칙, 말투 사전) 읽기. 문서를 고치면 해석이 달라진다 (FR-014)."""
import json
from dataclasses import dataclass
from pathlib import Path

from .config import KNOWLEDGE


@dataclass
class Knowledge:
    name: str
    glossary: dict
    rules: dict
    tone: dict


def available_knowledge(root: Path | str = KNOWLEDGE) -> list[str]:
    return sorted(p.name for p in Path(root).iterdir() if p.is_dir())


def load_knowledge(name: str = "base", root: Path | str = KNOWLEDGE) -> Knowledge:
    base = Path(root) / name

    def read(file: str) -> dict:
        with open(base / file, encoding="utf-8") as f:
            return json.load(f)

    return Knowledge(name=name, glossary=read("glossary.json"), rules=read("rules.json"), tone=read("tone.json"))

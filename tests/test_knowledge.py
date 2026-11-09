"""T017: 지식 문서를 고치면 해석 프롬프트가 달라진다 (FR-014)."""
import json
import shutil

from src.config import KNOWLEDGE
from src.interpret import build_system_prompt
from src.knowledge import load_knowledge


def test_glossary_entry_changes_prompt(tmp_path):
    shutil.copytree(KNOWLEDGE / "base", tmp_path / "base")
    before = build_system_prompt(load_knowledge("base", root=tmp_path))
    assert "테스트약어" not in before

    gl = tmp_path / "base" / "glossary.json"
    data = json.loads(gl.read_text(encoding="utf-8"))
    data["terms"].append({"term": "테스트약어", "means": "프론트범퍼", "source": "시험"})
    gl.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    after = build_system_prompt(load_knowledge("base", root=tmp_path))
    assert "테스트약어" in after


def test_extended_knowledge_adds_assumptions():
    base = build_system_prompt(load_knowledge("base"))
    ext = build_system_prompt(load_knowledge("extended"))
    assert "프싸" not in base
    assert "프싸" in ext


def test_tone_dictionary_is_loaded():
    k = load_knowledge("base")
    assert "권장" in k.tone["약한말투"]
    assert "교체" in k.tone["교환_근거어"]
    assert "봐주세요" in k.tone["약한말투"]
    assert "봐주세요" in load_knowledge("extended").tone["지시어"]

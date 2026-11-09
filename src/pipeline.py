"""메모 한 건 -> 오더 초안. 해석(LLM) -> 검사(프로그램) -> 문장 역할 계산. 해석이 실패하면 FR-022 초안을 낸다."""
from typing import Callable

from .catalog import load_catalog
from .config import MODEL
from .interpret import interpret
from .knowledge import Knowledge
from .llm import LLMFailure
from .models import Draft, Excluded, Item, Meta, Sentence
from .sentences import split_sentences
from .validator import _hits, _terms, validate


def _roles(sentences: list[str], items: list[dict], excluded: list[dict], knowledge: Knowledge) -> list[Sentence]:
    """문장마다 반영, 제외, 애매, 연결없음을 정한다. 애매한 항목에 걸리면 애매가 가장 우선이다."""
    none_needed = _terms(knowledge.tone.get("제외_표현"))
    out = []
    for idx, text in enumerate(sentences):
        mine = [i for i in items if idx in i["evidence"]]
        if any(i["status"] != "제안" for i in mine):
            role = "애매"
        elif mine:
            role = "반영"
        elif any(idx in e["evidence"] for e in excluded) or _hits(text, none_needed):
            role = "제외"
        else:
            role = "연결없음"
        out.append(Sentence(idx=idx, text=text, role=role))
    return out


def _fallback(inspection: dict, sentences: list[str], knowledge: Knowledge, reason: str, attempts: int) -> Draft:
    """FR-022: 해석 없이 메모 문장만 나열하고 모든 항목을 확인필요로 둔다. 코드는 제안하지 않는다."""
    items = [Item(id=i + 1, status="확인필요", code=None, qty=None, evidence=[i],
                  issue="해석에 실패해 이 문장을 정리하지 못했다. 직접 확인이 필요하다",
                  recommended=None, alternatives=[], downgraded_by=None)
             for i in range(len(sentences))]
    return Draft(
        inspection_id=inspection["inspection_id"], memo=inspection["memo"],
        sentences=[Sentence(idx=i, text=s, role="애매") for i, s in enumerate(sentences)],
        overall="판단불가", items=items, excluded=[],
        warnings=[f"해석 실패: {reason}"],
        meta=Meta(model=MODEL, knowledge=knowledge.name, attempts=attempts, failure=reason),
    )


def map_memo(inspection: dict, knowledge: Knowledge, *, runner: Callable | None = None,
             catalog: dict | None = None) -> Draft:
    catalog = catalog if catalog is not None else load_catalog()
    sentences = split_sentences(inspection["memo"])
    if not sentences:
        return Draft(inspection_id=inspection["inspection_id"], memo=inspection["memo"], sentences=[],
                     overall="작업없음", items=[], excluded=[], warnings=[],
                     meta=Meta(model=MODEL, knowledge=knowledge.name, attempts=1, failure=None))
    attempts = 1
    try:
        raw, attempts = interpret(sentences, knowledge, runner=runner, catalog=catalog)
        cost = raw.pop("_cost_usd", None)
        v = validate(raw, sentences, knowledge, catalog)
        return Draft(
            inspection_id=inspection["inspection_id"], memo=inspection["memo"],
            sentences=_roles(sentences, v["items"], v["excluded"], knowledge),
            overall=v["overall"],
            items=[Item(**i) for i in v["items"]],
            excluded=[Excluded(**e) for e in v["excluded"]],
            warnings=v["warnings"],
            meta=Meta(model=MODEL, knowledge=knowledge.name, attempts=attempts, failure=None, cost_usd=cost),
        )
    except LLMFailure as e:
        return _fallback(inspection, sentences, knowledge, e.reason, e.attempts)
    except (KeyError, TypeError, ValueError, AttributeError) as e:  # 형식이 틀린 결과(pydantic 오류 포함)
        return _fallback(inspection, sentences, knowledge, f"해석 결과 형식 오류: {type(e).__name__}: {str(e)[:150]}", attempts)

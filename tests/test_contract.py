"""T016: 결과 데이터 구조 (FR-001, FR-002, FR-006, FR-010).

2단계에서는 모델 제약 시험만 있고, 파이프라인이 만든 초안 시험은 3단계에서 더한다.
"""
import pytest
from pydantic import ValidationError

from src.models import Draft, Item, Meta


def item(**kw):
    base = dict(id=1, status="확인필요", code=None, qty=None, evidence=[0], issue="쟁점",
                recommended=None, alternatives=[], downgraded_by=None)
    base.update(kw)
    return Item(**base)


def test_suggestion_needs_code_and_qty():
    with pytest.raises(ValidationError):
        item(status="제안", code=None, qty=1)
    with pytest.raises(ValidationError):
        item(status="제안", code="BP-FR-PT", qty=None)
    assert item(status="제안", code="BP-FR-PT", qty=1).status == "제안"


def test_suggestion_code_must_be_in_catalog():
    with pytest.raises(ValidationError):
        item(status="제안", code="XX-00-ZZ", qty=1)


def test_evidence_must_not_be_empty():
    with pytest.raises(ValidationError):
        item(evidence=[])


def test_qty_minimum_is_one_or_null():
    with pytest.raises(ValidationError):
        item(status="제안", code="BP-FR-PT", qty=0)
    assert item(qty=None).qty is None


def test_status_must_be_one_of_three():
    with pytest.raises(ValidationError):
        item(status="확정")


def draft(overall, items):
    return Draft(inspection_id="INS-X", memo="m", sentences=[], overall=overall, items=items,
                 excluded=[], warnings=[], meta=Meta(model="m", knowledge="base", attempts=1, failure=None))


def test_unfit_overall_cannot_hold_a_suggestion():
    with pytest.raises(ValidationError):
        draft("판단불가", [item(status="제안", code="BP-FR-PT", qty=1)])


def test_overall_must_be_one_of_three():
    with pytest.raises(ValidationError):
        draft("완료", [])


def test_attempts_minimum_is_one():
    with pytest.raises(ValidationError):
        Meta(model="m", knowledge="base", attempts=0, failure=None)


# ---- 3단계: 파이프라인이 만든 초안이 계약(JSON Schema)을 따르는가 ----
import json

from jsonschema import validate as js_validate

from src.config import ROOT
from src.knowledge import load_knowledge
from src.llm import LLMError
from src.pipeline import map_memo

SCHEMA = json.loads((ROOT / "specs/001-memo-to-work-order/contracts/draft.schema.json").read_text(encoding="utf-8"))
K = load_knowledge("base")
INS = {"inspection_id": "INS-T2", "memo": "프론트범퍼 도색 필요. 사이드미러 커버는 교환이 나을 것 같음. 이전 오너가 앞유리를 교체했다고 함."}
RAW = {
    "overall": "정상",
    "items": [
        {"status": "제안", "code": "BP-FR-PT", "qty": 1, "evidence": [0], "issue": None, "recommended": None, "alternatives": []},
        {"status": "확인필요", "code": None, "qty": None, "evidence": [1], "issue": "도색과 교환 중 무엇인지 모른다",
         "recommended": {"code": "MR-00-EX", "qty": 1}, "alternatives": [{"code": "MR-00-PT", "qty": 1}]},
    ],
    "excluded": [{"evidence": [2], "reason": "이전 오너가 이미 교체했다"}],
}


def fake(raw):
    return lambda system, user, schema, model: json.loads(json.dumps(raw))


def failing(system, user, schema, model):
    raise LLMError("시험용 실패")


def test_drafts_match_schema():
    for runner in (fake(RAW), failing):
        d = map_memo(INS, K, runner=runner)
        js_validate(json.loads(d.model_dump_json()), SCHEMA)


def test_confirm_item_has_issue_and_recommendation():
    d = map_memo(INS, K, runner=fake(RAW))
    confirm = [i for i in d.items if i.status == "확인필요"]
    assert confirm
    for i in confirm:
        assert i.issue
    assert confirm[0].recommended.code == "MR-00-EX"
    assert [a.code for a in confirm[0].alternatives] == ["MR-00-PT"]


def test_excluded_item_has_reason():
    d = map_memo(INS, K, runner=fake(RAW))
    assert d.excluded and all(e.reason for e in d.excluded)
    assert {s.idx: s.role for s in d.sentences} == {0: "반영", 1: "애매", 2: "제외"}

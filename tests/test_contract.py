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

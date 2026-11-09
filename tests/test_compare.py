"""T033: 기본 문서와 보강 문서 결과 비교 (FR-014, SC-004, SC-005)."""
from src.compare import compare


def item(status, code=None):
    return {"id": 1, "status": status, "code": code, "evidence": [0]}


def payload(name, drafts):
    return {"knowledge": name, "results": drafts}


BASE = payload("base", [
    {"inspection_id": "A", "overall": "정상", "items": [item("확인필요"), item("확인필요")]},
    {"inspection_id": "B", "overall": "정상", "items": [item("제안", "BP-FR-PT")]},
])
EXT = payload("extended", [
    {"inspection_id": "A", "overall": "정상", "items": [item("제안", "FD-FR-SP"), item("확인필요")]},
    {"inspection_id": "B", "overall": "정상", "items": [item("제안", "BP-FR-PT")]},
])


def test_compare_counts_per_status():
    c = compare(BASE, EXT)
    assert c["totals"]["base"] == {"제안": 1, "확인필요": 2, "코드없음": 0}
    assert c["totals"]["extended"] == {"제안": 2, "확인필요": 1, "코드없음": 0}
    assert c["totals"]["제안_증가"] == 1


def test_per_inspection_counts_reported():
    c = compare(BASE, EXT)
    rows = {r["inspection_id"]: r for r in c["rows"]}
    assert rows["A"]["base"] == {"제안": 0, "확인필요": 2, "코드없음": 0}
    assert rows["A"]["extended"] == {"제안": 1, "확인필요": 1, "코드없음": 0}
    assert rows["A"]["changed"] is True and rows["B"]["changed"] is False
    assert c["changed"] == ["A"]

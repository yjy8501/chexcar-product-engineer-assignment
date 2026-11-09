"""T027: 승인 규칙 (FR-012, FR-022). 저장 폴더는 임시 폴더를 쓴다."""
import json

import pytest
from fastapi.testclient import TestClient

from src import config
from src.app import app
from src.knowledge import load_knowledge
from src.llm import LLMError
from src.pipeline import map_memo

K = load_knowledge("base")

MEMO = "프론트범퍼 도색 필요. 사이드미러 커버는 교환이 나을 것 같음. 썬루프 모터에서 소음 발생."
RAW = {
    "overall": "정상",
    "items": [
        {"status": "제안", "code": "BP-FR-PT", "qty": 1, "evidence": [0], "issue": None, "recommended": None, "alternatives": []},
        {"status": "확인필요", "code": None, "qty": None, "evidence": [1], "issue": "도색과 교환 중 무엇인지 모른다",
         "recommended": {"code": "MR-00-EX", "qty": 1}, "alternatives": [{"code": "MR-00-PT", "qty": 1}]},
        {"status": "코드없음", "code": None, "qty": None, "evidence": [2], "issue": "코드표에 해당 작업이 없다",
         "recommended": None, "alternatives": []},
    ],
    "excluded": [],
}


def failing(system, user, schema, model):
    raise LLMError("시험용 실패")


def make_draft(inspection_id, memo, runner):
    return map_memo({"inspection_id": inspection_id, "memo": memo}, K, runner=runner).model_dump()


@pytest.fixture
def client(tmp_path, monkeypatch):
    results, orders = tmp_path / "results", tmp_path / "orders"
    results.mkdir(), orders.mkdir()
    monkeypatch.setattr(config, "RESULTS", results)
    monkeypatch.setattr(config, "ORDERS", orders)
    drafts = [
        make_draft("INS-T3", MEMO, lambda *a: json.loads(json.dumps(RAW))),
        make_draft("INS-T4", "프론트범퍼 도색 필요. 본넷 탈부착 요망.", failing),  # 해석 실패 -> 추천 없는 확인필요
        make_draft("INS-T5", "프론트범퍼 도색 필요. 썬루프 모터에서 소음 발생.", lambda *a: {
            "overall": "정상", "excluded": [], "items": [RAW["items"][0], {**RAW["items"][2], "evidence": [1]}]}),
    ]
    (results / "results_base.json").write_text(json.dumps({"model": "m", "knowledge": "base", "generated_at": "x",
                                                           "catalog": {}, "results": drafts}), encoding="utf-8")
    app.state.runner = None
    c = TestClient(app)
    c.orders_dir = orders
    return c


def post(c, inspection_id, selections):
    return c.post("/api/orders", json={"inspection_id": inspection_id, "knowledge": "base", "selections": selections})


def test_approve_blocked_when_confirm_remains(client):
    r = post(client, "INS-T3", [])
    assert r.status_code == 409
    assert r.json()["detail"]["remaining"] == [2]
    assert not list(client.orders_dir.glob("*.json"))


def test_approve_saves_confirmed_order(client):
    r = post(client, "INS-T3", [{"item_id": 2, "choice": "MR-00-EX"}])
    assert r.status_code == 200, r.text
    body = r.json()
    lines = {(l["code"], l["qty"], l["source"]) for l in body["lines"]}
    assert lines == {("BP-FR-PT", 1, "제안승인"), ("MR-00-EX", 1, "직접선택")}
    assert body["manual"] == [3] and body["approved_at"]
    saved = json.loads((client.orders_dir / "INS-T3.json").read_text(encoding="utf-8"))
    assert saved["inspection_id"] == "INS-T3"


def test_skip_choice_excluded_from_order(client):
    r = post(client, "INS-T3", [{"item_id": 2, "choice": "skip"}])
    assert r.status_code == 200
    body = r.json()
    assert [l["code"] for l in body["lines"]] == ["BP-FR-PT"]
    assert [s["item_id"] for s in body["skipped"]] == [2]


def test_unknown_code_rejected(client):
    r = post(client, "INS-T3", [{"item_id": 2, "choice": "ZZ-99-XX"}])
    assert r.status_code == 422
    assert not list(client.orders_dir.glob("*.json"))


def test_choose_any_catalog_code_when_no_recommendation(client):
    # 해석 실패 초안: 항목마다 추천이 없다. 코드표의 아무 코드를 고를 수 있다.
    r = post(client, "INS-T4", [{"item_id": 1, "choice": "BP-FR-PT"}, {"item_id": 2, "choice": "skip"}])
    assert r.status_code == 200, r.text
    assert [(l["code"], l["source"]) for l in r.json()["lines"]] == [("BP-FR-PT", "직접선택")]


def test_no_code_item_does_not_block_approval(client):
    r = post(client, "INS-T5", [])
    assert r.status_code == 200, r.text
    body = r.json()
    assert [l["code"] for l in body["lines"]] == ["BP-FR-PT"]
    assert body["manual"] == [2]


def test_selection_for_non_confirm_item_rejected(client):
    r = post(client, "INS-T3", [{"item_id": 1, "choice": "BP-FR-PT"}, {"item_id": 2, "choice": "skip"}])
    assert r.status_code == 422


def test_missing_draft_404(client):
    assert post(client, "INS-NOPE", []).status_code == 404


def test_path_traversal_id_rejected(client):
    r = post(client, "../evil", [])
    assert r.status_code in (404, 422)
    assert not list(client.orders_dir.parent.glob("evil*"))


def test_list_orders_returns_saved(client):
    post(client, "INS-T3", [{"item_id": 2, "choice": "skip"}])
    r = client.get("/api/orders")
    assert r.status_code == 200 and [o["inspection_id"] for o in r.json()["orders"]] == ["INS-T3"]


def test_map_failure_returns_fallback_draft(client):
    app.state.runner = failing
    try:
        r = client.post("/api/map", json={"memo": "프론트범퍼 도색 필요. 본넷 탈부착 요망.", "knowledge": "base"})
    finally:
        app.state.runner = None
    assert r.status_code == 200
    d = r.json()
    assert d["overall"] == "판단불가" and d["meta"]["failure"]
    assert all(i["status"] == "확인필요" and i["code"] is None for i in d["items"])


def test_map_requires_inspection_id_or_memo(client):
    assert client.post("/api/map", json={"knowledge": "base"}).status_code == 422

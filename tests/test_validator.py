"""T014: 프로그램 검사 규칙 V1~V11 (FR-002~FR-005, FR-007~FR-009, FR-011, FR-013).

validate(raw, sentences, knowledge)는 LLM의 날것 결과를 받아 틀린 것을 확인필요로 내린 결과를 낸다.
"""
from src.knowledge import load_knowledge
from src.validator import validate

K = load_knowledge("base")


def it(code, qty=1, evidence=(0,), status="제안", **kw):
    base = dict(status=status, code=code, qty=qty, evidence=list(evidence), issue=None,
                recommended=None, alternatives=[])
    base.update(kw)
    return base


def run(sentences, items, overall="정상", excluded=()):
    raw = dict(overall=overall, items=items, excluded=list(excluded))
    return validate(raw, sentences, K)


def only(out):
    assert len(out["items"]) == 1, out["items"]
    return out["items"][0]


def test_v1_unknown_code_becomes_confirm():
    out = run(["프론트범퍼 도색 필요."], [it("ZZ-99-XX")])
    i = only(out)
    assert i["status"] == "확인필요" and i["code"] is None and i["downgraded_by"] == "V1"
    assert i["issue"]


def test_v1_unknown_alternative_is_dropped():
    out = run(["프론트범퍼 도색 필요."],
              [it(None, None, status="확인필요", alternatives=[{"code": "ZZ-99-XX", "qty": 1}, {"code": "BP-FR-PT", "qty": 1}])])
    assert [a["code"] for a in only(out)["alternatives"]] == ["BP-FR-PT"]


def test_v2_missing_evidence_becomes_confirm():
    out = run(["프론트범퍼 도색 필요."], [it("BP-FR-PT", evidence=(5,))])
    i = only(out)
    assert i["status"] == "확인필요" and i["downgraded_by"] == "V2"
    assert i["evidence"] == [0]  # 근거를 알 수 없으면 메모 전체를 근거로 둔다


def test_v2_empty_evidence_becomes_confirm():
    out = run(["프론트범퍼 도색 필요.", "본넷 탈부착 요망."], [it("BP-FR-PT", evidence=())])
    i = only(out)
    assert i["downgraded_by"] == "V2" and i["evidence"] == [0, 1]


def test_v3_weak_tone_becomes_confirm():
    out = run(["브레이크 패드 앞쪽 교체 권장."], [it("BR-00-EX")])
    i = only(out)
    assert i["status"] == "확인필요" and i["downgraded_by"] == "V3"
    assert i["recommended"] == {"code": "BR-00-EX", "qty": 1}


def test_v3_directive_tone_stays_suggestion():
    out = run(["프론트범퍼 도색 필요."], [it("BP-FR-PT")])
    assert only(out)["status"] == "제안"


def test_v4_exchange_without_word_becomes_confirm():
    out = run(["사이드미러 커버 기스."], [it("MR-00-EX")])
    assert only(out)["downgraded_by"] == "V4"


def test_v4_exchange_with_word_stays_suggestion():
    out = run(["사이드미러 커버 교환 필요."], [it("MR-00-EX")])
    assert only(out)["status"] == "제안"


def test_v5_tire_qty_over_2_becomes_confirm():
    out = run(["타이어 교환 필요."], [it("TY-00-EX", qty=4)])
    assert only(out)["downgraded_by"] == "V5"


def test_v5_tire_qty_2_is_allowed():
    out = run(["앞타이어 양쪽 교환 필요."], [it("TY-00-EX", qty=2)])
    assert only(out)["status"] == "제안"


def test_v5_brake_front_rear_unknown_becomes_confirm():
    out = run(["브레이크 패드 교환 필요."], [it("BR-00-EX")])
    assert only(out)["downgraded_by"] == "V5"


def test_v5_brake_with_front_is_allowed():
    out = run(["앞 브레이크 패드 교환 필요."], [it("BR-00-EX")])
    assert only(out)["status"] == "제안"


def test_v5_missing_qty_becomes_confirm():
    out = run(["프론트범퍼 도색 필요."], [it("BP-FR-PT", qty=None)])
    assert only(out)["downgraded_by"] == "V5"


def test_v6_duplicate_codes_merged():
    out = run(["앞범퍼 도색.", "프론트범퍼 좌측에도 스크래치 있어 같이 진행."],
              [it("BP-FR-PT", evidence=(0,)), it("BP-FR-PT", evidence=(1,))])
    i = only(out)
    assert i["evidence"] == [0, 1] and i["qty"] == 1
    assert any("중복" in w for w in out["warnings"])


def test_v6_merge_keeps_weaker_status():
    out = run(["앞범퍼 도색 필요.", "앞범퍼 도색 권장."],
              [it("BP-FR-PT", evidence=(0,)), it("BP-FR-PT", evidence=(1,))])
    assert only(out)["status"] == "확인필요"


def test_v7_unfit_overall_has_no_suggestion():
    out = run(["외판 여러 군데 손봐야 함."], [it("BP-FR-PT")], overall="판단불가")
    assert all(i["status"] != "제안" for i in out["items"])
    assert out["overall"] == "판단불가"
    assert out["items"][0]["downgraded_by"] == "V7"


def test_v7_no_work_with_items_becomes_normal():
    out = run(["프론트범퍼 도색 필요."], [it("BP-FR-PT")], overall="작업없음")
    assert out["overall"] == "정상"


def test_v7_normal_without_items_becomes_no_work():
    out = run(["특이사항 없음."], [], overall="정상")
    assert out["overall"] == "작업없음"


def test_v8_unlinked_sentence_warns():
    out = run(["프론트범퍼 도색 필요.", "배기구 색이 다름."], [it("BP-FR-PT")])
    assert any("1" in w and "배기구" in w for w in out["warnings"])


def test_v8_no_issue_sentence_does_not_warn():
    out = run(["프론트범퍼 도색 필요.", "실내 상태 양호."], [it("BP-FR-PT")])
    assert out["warnings"] == []


def test_v9_lost_work_becomes_no_code():
    out = run(["썬루프 모터에서 소음 발생.", "개폐는 정상."], [], overall="작업없음")
    i = only(out)
    assert i["status"] == "코드없음" and i["code"] is None and i["evidence"] == [0]
    assert i["downgraded_by"] == "V9"
    assert out["overall"] == "정상"


def test_v9_unlinked_work_word_sentence_becomes_no_code():
    out = run(["프론트범퍼 도색 필요.", "와이퍼 점검 필요."], [it("BP-FR-PT")])
    assert [i["status"] for i in out["items"]] == ["제안", "코드없음"]


def test_v10_null_code_with_alternatives_becomes_confirm():
    out = run(["휀다 찍힘 판금 후 도색."],
              [it(None, None, status="코드없음", alternatives=[{"code": "FD-FL-SP", "qty": 1}, {"code": "FD-FR-SP", "qty": 1}])])
    i = only(out)
    assert i["status"] == "확인필요" and i["downgraded_by"] == "V10"
    assert i["recommended"] == {"code": "FD-FL-SP", "qty": 1}


def test_v11_panel_paint_needs_panel_word():
    out = run(["본넷 도색 필요."], [it("HD-00-SP")])
    i = only(out)
    assert i["downgraded_by"] == "V11"
    assert {"code": "HD-00-PT", "qty": 1} in i["alternatives"]


def test_v11_panel_word_present_stays_suggestion():
    out = run(["본넷 판금 후 도색."], [it("HD-00-SP")])
    assert only(out)["status"] == "제안"


def test_confirm_item_always_has_issue():
    out = run(["프론트범퍼 도색 필요."], [it(None, None, status="확인필요", issue=None)])
    assert only(out)["issue"]


def test_ids_are_sequential_from_one():
    out = run(["프론트범퍼 도색 필요.", "본넷 탈부착 요망."], [it("BP-FR-PT"), it("HD-00-RM", evidence=(1,))])
    assert [i["id"] for i in out["items"]] == [1, 2]

"""T032: 정답표 비교 평가 (FR-015, SC-001, SC-002, SC-003).

정답표는 우리가 만든 해석이다. 평가 결과는 "회사의 정답과 일치"가 아니라 "우리 해석과 일치"로 읽는다.
"""
import json

from src.evaluate import evaluate, main


def item(status, code=None, qty=None, rec=None, alts=()):
    return {"id": 1, "status": status, "code": code, "qty": qty, "evidence": [0], "issue": "x",
            "recommended": {"code": rec, "qty": 1} if rec else None,
            "alternatives": [{"code": a, "qty": 1} for a in alts], "downgraded_by": None}


def draft(iid, overall="정상", items=()):
    return {"inspection_id": iid, "overall": overall, "items": list(items)}


def payload(drafts, knowledge="base"):
    return {"knowledge": knowledge, "results": drafts}


def key(iid, overall="정상", suggest=(), confirm=(), no_code=0, forbidden=()):
    return {"inspection_id": iid, "overall": overall, "suggest": [{"code": c, "qty": q} for c, q in suggest],
            "confirm": [list(g) for g in confirm], "no_code": no_code,
            "forbidden": [{"code": c, "max_qty": m} for c, m in forbidden]}


def total(report, name):
    return report["totals"][name]


def test_wrong_confirm_counted_for_forbidden_code():
    k = [key("A", suggest=[("BP-FR-PT", 1)], forbidden=[("BP-RR-PT", None)])]
    r = evaluate(payload([draft("A", items=[item("제안", "BP-FR-PT", 1), item("제안", "BP-RR-PT", 1)])]), k)
    assert total(r, "잘못_확정") == 1


def test_wrong_confirm_counted_when_qty_exceeds_max():
    k = [key("A", confirm=[["TY-00-EX"]], forbidden=[("TY-00-EX", 2)])]
    over = evaluate(payload([draft("A", items=[item("제안", "TY-00-EX", 4)])]), k)
    assert total(over, "잘못_확정") == 1
    within = evaluate(payload([draft("A", items=[item("확인필요", rec="TY-00-EX")])]), k)
    assert total(within, "잘못_확정") == 0


def test_unexpected_suggestion_counted_as_wrong():
    k = [key("A", suggest=[("BP-FR-PT", 1)])]
    r = evaluate(payload([draft("A", items=[item("제안", "BP-FR-PT", 1), item("제안", "HD-00-RM", 1)])]), k)
    assert total(r, "잘못_확정") == 1


def test_suggested_code_that_should_be_confirmed_is_wrong():
    k = [key("A", confirm=[["BR-00-EX"]])]
    r = evaluate(payload([draft("A", items=[item("제안", "BR-00-EX", 1)])]), k)
    assert total(r, "잘못_확정") == 1


def test_missing_suggestion_counted():
    k = [key("A", suggest=[("BP-FR-PT", 1)])]
    r = evaluate(payload([draft("A", items=[])]), k)
    assert total(r, "빠뜨린_제안") == 1 and total(r, "지나친_확인필요") == 0


def test_over_confirm_counted():
    k = [key("A", suggest=[("BP-FR-PT", 1)])]
    r = evaluate(payload([draft("A", items=[item("확인필요", rec="BP-FR-PT")])]), k)
    assert total(r, "지나친_확인필요") == 1 and total(r, "빠뜨린_제안") == 0


def test_buried_issue_counted_when_confirm_group_is_absent():
    k = [key("A", confirm=[["FD-FL-SP", "FD-FR-SP"]])]
    absent = evaluate(payload([draft("A", items=[])]), k)
    assert total(absent, "묻힌_쟁점") == 1
    present = evaluate(payload([draft("A", items=[item("확인필요", rec="FD-FR-SP")])]), k)
    assert total(present, "묻힌_쟁점") == 0


def test_overall_mismatch_counted():
    k = [key("A", overall="판단불가")]
    r = evaluate(payload([draft("A", overall="정상")]), k)
    assert total(r, "전체판정_불일치") == 1
    assert total(evaluate(payload([draft("A", overall="판단불가")]), k), "전체판정_불일치") == 0


def test_no_code_mismatch_counted():
    k = [key("A", no_code=1)]
    r = evaluate(payload([draft("A", items=[item("코드없음")]), ]), k)
    assert total(r, "코드없음_불일치") == 0
    r = evaluate(payload([draft("A", items=[])]), k)
    assert total(r, "코드없음_불일치") == 1


def test_extended_results_are_not_scored():
    k = [key("A", forbidden=[("BP-RR-PT", None)])]
    r = evaluate(payload([draft("A", items=[item("제안", "BP-RR-PT", 1)])], knowledge="extended"), k)
    assert r["scored"] is False and r["totals"] is None


def write(tmp_path, results, keys):
    rp, kp = tmp_path / "r.json", tmp_path / "k.json"
    rp.write_text(json.dumps(results), encoding="utf-8")
    kp.write_text(json.dumps(keys), encoding="utf-8")
    return ["--results", str(rp), "--key", str(kp)]


def test_exit_code_nonzero_when_wrong_confirm(tmp_path, capsys):
    k = [key("A", forbidden=[("BP-RR-PT", None)])]
    args = write(tmp_path, payload([draft("A", items=[item("제안", "BP-RR-PT", 1)])]), k)
    assert main(args) == 1
    assert "잘못 확정" in capsys.readouterr().out


def test_exit_code_zero_when_no_wrong_confirm(tmp_path):
    k = [key("A", suggest=[("BP-FR-PT", 1)])]
    args = write(tmp_path, payload([draft("A", items=[item("제안", "BP-FR-PT", 1)])]), k)
    assert main(args) == 0

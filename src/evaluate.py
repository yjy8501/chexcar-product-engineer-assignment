"""정답표와 결과를 비교한다. `python -m src.evaluate [--results ...] [--key ...]`

정답표는 우리가 메모를 읽고 만든 해석이다. 이 평가는 "회사의 정답과 일치"가 아니라 "우리 해석과 일치"를 본다.
기본 문서(base) 결과만 점수로 계산하고, 보강 문서(extended)는 가정이 들어 있어 점수에 넣지 않는다.
잘못 확정이 1건이라도 있으면 종료 코드 1을 낸다.
"""
import argparse
import json

from .config import ANSWER_KEY, RESULTS

METRICS = ["잘못_확정", "빠뜨린_제안", "지나친_확인필요", "묻힌_쟁점", "전체판정_불일치", "코드없음_불일치"]


def _asked_codes(items: list[dict]) -> set[str]:
    """확인필요 항목에서 관리자에게 보여 주는 코드(추천과 대안)."""
    codes = set()
    for i in items:
        if i["status"] != "확인필요":
            continue
        if i.get("recommended"):
            codes.add(i["recommended"]["code"])
        codes |= {a["code"] for a in i.get("alternatives") or []}
    return codes


def _row(d: dict, k: dict) -> dict:
    items = d["items"]
    suggested = [i for i in items if i["status"] == "제안"]
    asked = _asked_codes(items)
    allowed = {s["code"]: s.get("qty") for s in k.get("suggest", [])}
    forbidden = {f["code"]: f.get("max_qty") for f in k.get("forbidden", [])}
    detail, wrong = [], 0

    for i in suggested:  # 잘못 확정: 확정해서는 안 되는데 제안으로 낸 것
        c, q = i["code"], i["qty"]
        if c in forbidden and (forbidden[c] is None or q > forbidden[c]):
            wrong += 1; detail.append(f"잘못 확정: {c} 수량 {q}는 나오면 안 된다")
        elif c not in allowed:
            wrong += 1; detail.append(f"잘못 확정: {c}는 정답표에 제안으로 없다")
        elif allowed[c] and q != allowed[c]:
            wrong += 1; detail.append(f"잘못 확정: {c} 수량 {q} (정답표 {allowed[c]})")

    suggested_codes = {i["code"] for i in suggested}
    missed = over = 0
    for code in allowed:
        if code in suggested_codes:
            continue
        if code in asked:
            over += 1; detail.append(f"지나친 확인필요: {code}는 제안이어야 하는데 확인필요로 넘겼다")
        else:
            missed += 1; detail.append(f"빠뜨린 제안: {code}")

    buried = 0
    for group in k.get("confirm", []):
        if set(group) & suggested_codes or set(group) & asked:
            continue
        buried += 1; detail.append(f"묻힌 쟁점: {'/'.join(group)}가 확인필요로 올라오지 않았다")

    no_code_n = sum(1 for i in items if i["status"] == "코드없음")
    no_code_bad = int(no_code_n != k.get("no_code", 0))
    if no_code_bad:
        detail.append(f"코드없음 {no_code_n}개 (정답표 {k.get('no_code', 0)}개)")
    overall_bad = int(d["overall"] != k.get("overall", "정상"))
    if overall_bad:
        detail.append(f"전체 판정 {d['overall']} (정답표 {k.get('overall', '정상')})")

    return {"inspection_id": d["inspection_id"], "overall": d["overall"],
            "잘못_확정": wrong, "빠뜨린_제안": missed, "지나친_확인필요": over, "묻힌_쟁점": buried,
            "전체판정_불일치": overall_bad, "코드없음_불일치": no_code_bad, "detail": detail}


def evaluate(payload: dict, key: list[dict]) -> dict:
    note = "정답표는 우리가 만든 해석이다. '회사의 정답과 일치'가 아니라 '우리 해석과 일치'를 본다."
    if payload.get("knowledge") != "base":
        return {"scored": False, "totals": None, "rows": [], "knowledge": payload.get("knowledge"),
                "note": "보강 문서(가정 포함) 결과는 점수에 넣지 않는다. " + note}
    keys = {k["inspection_id"]: k for k in key}
    rows = [_row(d, keys[d["inspection_id"]]) for d in payload["results"] if d["inspection_id"] in keys]
    totals = {m: sum(r[m] for r in rows) for m in METRICS}
    return {"scored": True, "knowledge": "base", "totals": totals, "rows": rows, "note": note,
            "missing_key": [d["inspection_id"] for d in payload["results"] if d["inspection_id"] not in keys]}


def format_report(rep: dict) -> str:
    if not rep["scored"]:
        return rep["note"]
    out = [f"{'건':<8}{'판정':<6}{'잘못 확정':>9}{'빠뜨린 제안':>11}{'지나친 확인필요':>13}{'묻힌 쟁점':>9}{'코드없음':>9}{'판정':>5}"]
    for r in rep["rows"]:
        out.append(f"{r['inspection_id']:<8}{r['overall']:<6}{r['잘못_확정']:>9}{r['빠뜨린_제안']:>11}{r['지나친_확인필요']:>13}"
                   f"{r['묻힌_쟁점']:>9}{r['코드없음_불일치']:>9}{r['전체판정_불일치']:>5}")
        out += [f"          - {t}" for t in r["detail"]]
    t = rep["totals"]
    out.append(f"{'합계':<14}{t['잘못_확정']:>9}{t['빠뜨린_제안']:>11}{t['지나친_확인필요']:>13}{t['묻힌_쟁점']:>9}{t['코드없음_불일치']:>9}{t['전체판정_불일치']:>5}")
    out.append(f"잘못 확정 합계: {t['잘못_확정']}건")
    out.append(rep["note"])
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="정답표와 결과를 비교한다")
    ap.add_argument("--results", default=str(RESULTS / "results_base.json"))
    ap.add_argument("--key", default=str(ANSWER_KEY))
    args = ap.parse_args(argv)
    payload = json.load(open(args.results, encoding="utf-8"))
    key = json.load(open(args.key, encoding="utf-8"))
    rep = evaluate(payload, key)
    print(format_report(rep))
    return 1 if rep["scored"] and rep["totals"]["잘못_확정"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())

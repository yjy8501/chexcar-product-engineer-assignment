"""기본 문서(base)와 보강 문서(extended)의 결과를 비교한다. `python -m src.compare` (FR-014, SC-004, SC-005)

보강 문서는 가정이 들어 있는 것이라 점수가 아니라 "문서를 보강하면 제안이 얼마나 늘어나는가"를 보여 주는 용도다.
"""
import json

from .config import RESULTS

STATUSES = ["제안", "확인필요", "코드없음"]


def _counts(draft: dict) -> dict:
    c = {s: 0 for s in STATUSES}
    for i in draft["items"]:
        c[i["status"]] += 1
    return c


def compare(base: dict, ext: dict) -> dict:
    ext_by_id = {d["inspection_id"]: d for d in ext["results"]}
    rows = []
    for d in base["results"]:
        e = ext_by_id.get(d["inspection_id"])
        if e is None:
            continue
        b_c, e_c = _counts(d), _counts(e)
        rows.append({"inspection_id": d["inspection_id"], "base": b_c, "extended": e_c, "changed": b_c != e_c})
    tot = {name: {s: sum(r[name][s] for r in rows) for s in STATUSES} for name in ("base", "extended")}
    tot["제안_증가"] = tot["extended"]["제안"] - tot["base"]["제안"]
    return {"rows": rows, "totals": tot, "changed": [r["inspection_id"] for r in rows if r["changed"]]}


def format_report(c: dict) -> str:
    out = [f"{'건':<8}{'기본 제안/확인/코드없음':<22}{'보강 제안/확인/코드없음':<22}변화"]
    for r in c["rows"]:
        b, e = r["base"], r["extended"]
        out.append(f"{r['inspection_id']:<8}{b['제안']}/{b['확인필요']}/{b['코드없음']:<20}{e['제안']}/{e['확인필요']}/{e['코드없음']:<20}{'달라짐' if r['changed'] else ''}")
    t = c["totals"]
    out.append(f"합계    기본 {t['base']['제안']}/{t['base']['확인필요']}/{t['base']['코드없음']}   보강 {t['extended']['제안']}/{t['extended']['확인필요']}/{t['extended']['코드없음']}   제안 {t['제안_증가']:+d}")
    out.append("보강 문서는 가정이 들어 있어 점수에 넣지 않는다. 증가 폭은 보고만 한다.")
    return "\n".join(out)


def main(argv=None) -> int:
    base = json.load(open(RESULTS / "results_base.json", encoding="utf-8"))
    ext = json.load(open(RESULTS / "results_extended.json", encoding="utf-8"))
    print(format_report(compare(base, ext)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

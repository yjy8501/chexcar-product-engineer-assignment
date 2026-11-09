"""10건을 실행해 결과를 파일로 저장한다. `python -m src.run --knowledge base|extended [--only INS-001 ...]`

저장된 결과가 있으면 API 키나 CLI 없이도 결과 화면을 열 수 있다 (FR-016).
"""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .catalog import load_catalog
from .config import INSPECTIONS, MODEL, RESULTS
from .knowledge import load_knowledge
from .pipeline import map_memo


def counts(draft: dict) -> dict:
    c = {"제안": 0, "확인필요": 0, "코드없음": 0}
    for i in draft["items"]:
        c[i["status"]] += 1
    return c


def run_all(knowledge_name: str, only: list[str] | None = None, workers: int = 4) -> dict:
    knowledge = load_knowledge(knowledge_name)
    inspections = json.loads(INSPECTIONS.read_text(encoding="utf-8"))
    if only:
        inspections = [i for i in inspections if i["inspection_id"] in only]

    def one(ins):
        d = map_memo(ins, knowledge).model_dump()
        c = counts(d)
        print(f"{ins['inspection_id']}  {d['overall']:<4}  제안 {c['제안']} 확인필요 {c['확인필요']} 코드없음 {c['코드없음']}"
              f"  시도 {d['meta']['attempts']}" + (f"  실패: {d['meta']['failure']}" if d["meta"]["failure"] else ""), flush=True)
        return d

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, inspections))
    catalog = {c["code"]: {"name": c["name"], "part": c["part"], "price": int(c["price"]), "note": c["note"]}
               for c in load_catalog().values()}
    return {
        "model": MODEL,
        "knowledge": knowledge_name,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cost_usd": round(sum((r["meta"].get("cost_usd") or 0) for r in results), 4),
        "catalog": catalog,
        "results": results,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="검수 메모 10건을 오더 초안으로 바꾸고 결과를 저장한다")
    ap.add_argument("--knowledge", default="base", help="지식 문서 이름 (base 또는 extended)")
    ap.add_argument("--only", nargs="*", help="일부 메모만 실행(저장하지 않고 출력만 한다)")
    args = ap.parse_args(argv)
    payload = run_all(args.knowledge, args.only)
    total = {"제안": 0, "확인필요": 0, "코드없음": 0}
    for r in payload["results"]:
        for k, v in counts(r).items():
            total[k] += v
    print(f"합계  제안 {total['제안']}  확인필요 {total['확인필요']}  코드없음 {total['코드없음']}  비용 약 {payload['cost_usd']}달러")
    if args.only:
        return 0
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"results_{args.knowledge}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"저장: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

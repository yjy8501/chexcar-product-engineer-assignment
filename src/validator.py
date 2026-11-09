"""LLM의 날것 결과를 프로그램이 검사한다. 틀렸거나 애매한 것은 확인필요로 내린다 (헌법 원칙 IV).

규칙 (specs/001-memo-to-work-order/research.md D2):
  V1 코드표에 없는 코드          V2 근거 문장 번호가 없거나 메모 밖
  V3 약한 말투                   V4 교환 코드인데 교환 근거어 없음
  V5 수량 또는 앞뒤 단위 어긋남   V6 같은 코드 중복 병합
  V7 전체 결과와 항목의 모순      V8 어떤 항목에도 연결되지 않은 문장 경고
  V9 사라진 작업 되살리기        V10 코드 없는데 대안 있음
  V11 판금도색인데 판금 근거 없음
"""
from .catalog import load_catalog

DIRECTION_WORDS = ["앞", "전륜", "프론트", "뒤", "후륜", "리어", "뒷"]
TIRE_CODES = ("TY-00-EX", "TY-00-BL")
BRAKE_CODE = "BR-00-EX"


def _terms(words) -> list[str]:
    out = [str(w).lstrip("~").strip() for w in (words or [])]
    return [w for w in out if w]


def _hits(text: str, terms: list[str]) -> list[str]:
    return [t for t in terms if t in text]


def _cq(d, catalog) -> dict | None:
    if not isinstance(d, dict) or d.get("code") not in catalog:
        return None
    return {"code": d["code"], "qty": d.get("qty")}


def _norm(item: dict) -> dict:
    return {
        "status": item.get("status"),
        "code": item.get("code"),
        "qty": item.get("qty"),
        "evidence": [e for e in (item.get("evidence") or [])],
        "issue": item.get("issue"),
        "recommended": item.get("recommended"),
        "alternatives": list(item.get("alternatives") or []),
        "downgraded_by": None,
    }


def _down(it: dict, rule: str, issue: str, add_alt: dict | None = None) -> None:
    """제안을 확인필요로 내린다. 원래 코드는 추천으로 남긴다."""
    if it["code"]:
        it["recommended"] = {"code": it["code"], "qty": it["qty"]}
    if add_alt and add_alt["code"] != (it["recommended"] or {}).get("code") \
            and add_alt["code"] not in [a["code"] for a in it["alternatives"]]:
        it["alternatives"].append(add_alt)
    it["status"], it["code"], it["qty"] = "확인필요", None, None
    it["issue"] = f"{issue} ({it['issue']})" if it.get("issue") else issue
    it["downgraded_by"] = rule


def validate(raw: dict, sentences: list[str], knowledge, catalog: dict | None = None) -> dict:
    catalog = catalog if catalog is not None else load_catalog()
    tone = knowledge.tone
    weak = _terms(tone.get("약한말투"))
    exch = _terms(tone.get("교환_근거어"))
    none_needed = _terms(tone.get("제외_표현"))
    work_words = _terms(tone.get("지시어")) + weak + exch
    n = len(sentences)
    warnings: list[str] = []
    overall = raw["overall"]
    items = [_norm(i) for i in raw["items"]]

    def text_of(it):
        return " ".join(sentences[e] for e in it["evidence"])

    for it in items:
        # V2: 근거 문장 번호
        valid = [e for e in it["evidence"] if isinstance(e, int) and 0 <= e < n]
        bad_evidence = len(valid) != len(it["evidence"]) or not valid
        it["evidence"] = sorted(set(valid)) or list(range(n))

        # V1: 코드표에 없는 코드
        dropped = [a for a in it["alternatives"] if _cq(a, catalog) is None]
        it["alternatives"] = [c for c in (_cq(a, catalog) for a in it["alternatives"]) if c]
        if dropped:
            warnings.append(f"코드표에 없는 대안 {len(dropped)}개를 제거했다")
        if it["recommended"] is not None and _cq(it["recommended"], catalog) is None:
            it["recommended"] = None
        else:
            it["recommended"] = _cq(it["recommended"], catalog)
        unknown = it["code"] is not None and it["code"] not in catalog
        if unknown:
            bad_code = it["code"]
            it["code"] = None if it["status"] != "제안" else bad_code
            if it["status"] == "제안":
                _down(it, "V1", f"코드표에 없는 코드({bad_code})")
                it["code"] = None
        if it["status"] == "제안" and bad_evidence:
            _down(it, "V2", "근거 문장이 메모에 없거나 확인되지 않는다")

        if it["status"] == "제안":
            t = text_of(it)
            code = it["code"]
            if it["qty"] is None:
                _down(it, "V5", "수량을 알 수 없다")
            elif _hits(t, weak):
                _down(it, "V3", f"약한 말투('{_hits(t, weak)[0]}')라 지시인지 추천인지 알 수 없다")
            elif code.endswith("-EX") and not _hits(t, exch):
                _down(it, "V4", "교환이라고 적힌 근거가 없다")
            elif code.endswith("-SP") and "판금" not in t:
                pt = code[:-3] + "-PT"
                alt = {"code": pt, "qty": it["qty"]} if pt in catalog else None
                _down(it, "V11", "메모에 판금이 없고 도색만 적혀 있을 수 있다", add_alt=alt)
            elif code in TIRE_CODES and it["qty"] > 2:
                _down(it, "V5", "타이어 수량이 2를 넘는다. 1짝 단위와 맞는지 확인이 필요하다")
            elif code == BRAKE_CODE and not _hits(t, DIRECTION_WORDS):
                _down(it, "V5", "전륜인지 후륜인지 메모에 없다")

        # V10: 코드가 없거나 코드가 남은 확인필요/코드없음 항목 정리
        if it["status"] in ("확인필요", "코드없음"):
            if it["code"] is not None:  # 코드가 붙은 채 확인필요로 온 경우는 추천으로 옮긴다
                it["recommended"] = it["recommended"] or {"code": it["code"], "qty": it["qty"]}
                it["code"], it["qty"] = None, None
            if it["status"] == "코드없음" and (it["alternatives"] or it["recommended"]):
                it["status"] = "확인필요"
                it["downgraded_by"] = it["downgraded_by"] or "V10"
                it["recommended"] = it["recommended"] or it["alternatives"][0]
            elif it["status"] == "확인필요" and not it["recommended"] and it["alternatives"]:
                it["recommended"] = it["alternatives"][0]
            it["qty"] = None
            if not it["issue"]:
                it["issue"] = ("하나의 코드로 고를 수 없어 확인이 필요하다" if it["status"] == "확인필요"
                               else "코드표에 맞는 코드가 없다")

    # V6: 같은 코드는 한 항목으로 합친다
    merged: list[dict] = []
    by_code: dict[str, dict] = {}
    for it in items:
        eff = it["code"] or (it["recommended"] or {}).get("code")
        if eff is None:
            merged.append(it)
            continue
        if eff not in by_code:
            by_code[eff] = it
            it["_count"] = 1
            merged.append(it)
            continue
        base = by_code[eff]
        base["_count"] += 1
        base["evidence"] = sorted(set(base["evidence"]) | set(it["evidence"]))
        qtys = [q for q in (base["qty"] or (base["recommended"] or {}).get("qty"),
                            it["qty"] or (it["recommended"] or {}).get("qty")) if q]
        best = max(qtys) if qtys else None
        if it["status"] != "제안" and base["status"] == "제안":  # 더 약한 쪽을 따른다
            base.update(recommended={"code": eff, "qty": best}, code=None, status="확인필요",
                        issue=it["issue"], downgraded_by=it["downgraded_by"])
        if base["status"] == "제안":
            base["qty"] = best
        elif base["recommended"]:
            base["recommended"] = {"code": eff, "qty": best}
        base["alternatives"] += [a for a in it["alternatives"] if a["code"] not in [x["code"] for x in base["alternatives"]]]
    for it in merged:
        if it.pop("_count", 1) > 1:
            eff = it["code"] or it["recommended"]["code"]
            warnings.append(f"같은 코드({eff})가 여러 번 적혀 한 항목으로 합쳤다(중복)")
    items = merged

    excluded = []
    for e in raw.get("excluded") or []:
        ev = sorted({x for x in (e.get("evidence") or []) if isinstance(x, int) and 0 <= x < n})
        excluded.append({"evidence": ev, "reason": (e.get("reason") or "하지 않는다고 적혀 있다")})

    # V9: 어떤 항목에도 연결되지 않은 작업 문장은 코드없음으로 되살린다
    linked = {e for it in items for e in it["evidence"]} | {e for x in excluded for e in x["evidence"]}
    for idx in range(n):
        if idx in linked:
            continue
        s = sentences[idx]
        if _hits(s, none_needed):
            continue  # 작업이 필요 없다는 설명 문장
        if _hits(s, work_words) or overall == "작업없음":
            items.append({"status": "코드없음", "code": None, "qty": None, "evidence": [idx],
                          "issue": f"작업을 말하는 문장이지만 표준 코드에 연결되지 않았다: {s}",
                          "recommended": None, "alternatives": [], "downgraded_by": "V9"})
            linked.add(idx)

    # V7: 전체 결과와 항목이 모순되지 않게 한다
    if overall == "판단불가":
        for it in items:
            if it["status"] == "제안":
                _down(it, "V7", "메모만으로 작업을 고를 수 없어 제안하지 않는다")
    elif overall == "작업없음" and items:
        overall = "정상"
    elif overall == "정상" and not items:
        overall = "작업없음"

    # V8: 연결되지 않은 문장 경고
    for idx in range(n):
        if idx not in linked and not _hits(sentences[idx], none_needed):
            warnings.append(f"문장 {idx}이 어떤 항목에도 연결되지 않았다: {sentences[idx]}")

    for i, it in enumerate(items, 1):
        it["id"] = i
    return {"overall": overall, "items": items, "excluded": excluded, "warnings": warnings}

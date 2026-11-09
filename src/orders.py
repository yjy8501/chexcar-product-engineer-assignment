"""승인 검사와 확정 오더 저장 (FR-012). 최종 승인은 사람이 하고, 시스템은 규칙을 지키는지만 검사한다."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .catalog import has_code, load_catalog
from .models import ConfirmedOrder, OrderLine, Skipped

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
MAX_QTY = 99


class ApprovalBlocked(Exception):
    """확인필요 항목이 남아 있다 (409)."""

    def __init__(self, remaining: list[int]):
        super().__init__("확인필요 항목이 남아 있다")
        self.remaining = remaining


class OrderExists(Exception):
    """이미 승인된 오더라 덮어쓸 수 없다 (409). 확정 오더는 한 번 저장되면 바뀌지 않는다."""


class ApprovalInvalid(Exception):
    """선택이 규칙에 맞지 않는다 (422)."""


def safe_id(inspection_id: str) -> str:
    if not _SAFE_ID.match(inspection_id or ""):
        raise ApprovalInvalid(f"허용되지 않는 inspection_id: {inspection_id!r}")
    return inspection_id


def build_order(draft: dict, selections: list[dict], knowledge: str, catalog: dict | None = None) -> ConfirmedOrder:
    catalog = catalog if catalog is not None else load_catalog()
    items = {i["id"]: i for i in draft["items"]}
    confirm_ids = {i["id"] for i in draft["items"] if i["status"] == "확인필요"}

    chosen: dict[int, dict] = {}
    for s in selections:
        iid = s.get("item_id")
        if iid not in confirm_ids:
            raise ApprovalInvalid(f"확인필요 항목이 아닌 항목에 선택이 들어 있다: {iid}")
        choice = s.get("choice")
        if choice != "skip" and not has_code(choice, catalog):  # 코드표를 다시 검사한다
            raise ApprovalInvalid(f"코드표에 없는 코드: {choice}")
        qty = s.get("qty")
        if qty is not None and (not isinstance(qty, int) or not 1 <= qty <= MAX_QTY):
            raise ApprovalInvalid(f"수량은 1 이상 {MAX_QTY} 이하의 정수여야 한다: {qty}")
        chosen[iid] = s

    remaining = sorted(confirm_ids - set(chosen))
    if remaining:
        raise ApprovalBlocked(remaining)

    lines, skipped, manual = [], [], []
    for iid in sorted(items):
        it = items[iid]
        if it["status"] == "제안":
            lines.append(OrderLine(code=it["code"], qty=it["qty"], source="제안승인"))
        elif it["status"] == "코드없음":
            manual.append(iid)  # 승인을 막지 않고, 확정 오더에도 넣지 않는다
        else:
            s = chosen[iid]
            if s["choice"] == "skip":
                skipped.append(Skipped(item_id=iid))
                continue
            options = ([it["recommended"]] if it.get("recommended") else []) + list(it.get("alternatives") or [])
            hint = next((o["qty"] for o in options if o["code"] == s["choice"] and o.get("qty")), None)
            lines.append(OrderLine(code=s["choice"], qty=s.get("qty") or hint or 1, source="직접선택"))
    return ConfirmedOrder(inspection_id=draft["inspection_id"], knowledge=knowledge, lines=lines, skipped=skipped,
                          manual=manual, approved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))


def save_order(order: ConfirmedOrder, orders_dir: Path) -> Path:
    orders_dir = Path(orders_dir)
    orders_dir.mkdir(parents=True, exist_ok=True)
    path = orders_dir / f"{safe_id(order.inspection_id)}.json"
    try:
        with path.open("x", encoding="utf-8") as f:  # 이미 있으면 실패한다(덮어쓰기 금지)
            f.write(order.model_dump_json(indent=2) + "\n")
    except FileExistsError as e:
        raise OrderExists(f"이미 승인된 오더: {order.inspection_id}") from e
    return path


def load_orders(orders_dir: Path) -> list[dict]:
    orders_dir = Path(orders_dir)
    if not orders_dir.exists():
        return []
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(orders_dir.glob("*.json"))]

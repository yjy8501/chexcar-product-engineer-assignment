"""FastAPI 서버. 계약은 specs/001-memo-to-work-order/contracts/api.md."""
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import config
from .compare import compare
from .evaluate import evaluate
from .knowledge import available_knowledge, load_knowledge
from .orders import MAX_QTY, ApprovalBlocked, ApprovalInvalid, OrderExists, build_order, load_orders, safe_id, save_order
from .pipeline import map_memo

app = FastAPI(title="검수 메모 오더 초안")
app.state.runner = None  # 시험에서 가짜 해석기를 넣는 자리. None이면 claude CLI를 쓴다


def _check_knowledge(name: str) -> str:
    if name not in available_knowledge():  # 경로로 쓰이므로 목록에 있는 이름만 받는다
        raise HTTPException(404, f"알 수 없는 지식 문서: {name}")
    return name


def _saved_results(knowledge: str) -> dict:
    path = config.RESULTS / f"results_{_check_knowledge(knowledge)}.json"
    if not path.exists():
        raise HTTPException(404, "저장된 결과가 없다. `python -m src.run`으로 먼저 실행한다")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/")
def index():
    return FileResponse(config.WEB / "index.html")


@app.get("/api/knowledge")
def knowledge():
    return {"names": available_knowledge()}


@app.get("/api/results")
def results(knowledge: str = "base"):
    """저장된 실행 결과. API 키나 CLI가 필요 없다 (FR-016)."""
    return _saved_results(knowledge)


class MapRequest(BaseModel):
    inspection_id: str | None = None
    memo: str | None = Field(default=None, max_length=2000)  # 자유 입력은 길이를 제한한다
    knowledge: str = "base"


@app.post("/api/map")
def map_one(req: MapRequest):
    """메모 한 건을 새로 해석한다. 실패하면 FR-022 초안(판단불가, 문장별 확인필요)을 200으로 돌려준다."""
    if req.inspection_id:
        found = [i for i in json.loads(config.INSPECTIONS.read_text(encoding="utf-8")) if i["inspection_id"] == req.inspection_id]
        if not found:
            raise HTTPException(404, f"없는 inspection_id: {req.inspection_id}")
        inspection = found[0]
    elif req.memo:
        inspection = {"inspection_id": "ad-hoc", "memo": req.memo}  # 자유 입력은 해석만 보여주고 승인과 저장은 하지 않는다
    else:
        raise HTTPException(422, "inspection_id 또는 memo가 필요하다")
    draft = map_memo(inspection, load_knowledge(_check_knowledge(req.knowledge)), runner=app.state.runner)
    return draft.model_dump()


class Selection(BaseModel):
    item_id: int
    choice: str  # 코드 또는 "skip"
    qty: int | None = Field(default=None, ge=1, le=MAX_QTY)


class OrderRequest(BaseModel):
    inspection_id: str
    knowledge: str = "base"
    selections: list[Selection] = Field(default_factory=list)


@app.post("/api/orders")
def approve(req: OrderRequest):
    """승인한다. 확인필요가 남으면 409, 규칙에 어긋나면 422, 초안이 없으면 404."""
    try:
        iid = safe_id(req.inspection_id)
    except ApprovalInvalid as e:
        raise HTTPException(422, str(e))
    draft = next((d for d in _saved_results(req.knowledge)["results"] if d["inspection_id"] == iid), None)
    if draft is None:
        raise HTTPException(404, f"저장된 결과에 없는 초안: {iid}")
    try:
        order = build_order(draft, [s.model_dump() for s in req.selections], req.knowledge)
    except ApprovalBlocked as e:
        raise HTTPException(409, {"message": str(e), "remaining": e.remaining})
    except ApprovalInvalid as e:
        raise HTTPException(422, str(e))
    try:
        save_order(order, config.ORDERS)
    except OrderExists as e:
        raise HTTPException(409, {"message": str(e), "already_approved": True})
    return order.model_dump()


@app.get("/api/orders")
def orders():
    return {"orders": load_orders(config.ORDERS)}


def summary() -> dict:
    """정답표 평가와 기본/보강 비교. 저장된 결과와 정답표만 읽으므로 CLI가 필요 없다."""
    out: dict = {}
    base_path, ext_path = config.RESULTS / "results_base.json", config.RESULTS / "results_extended.json"
    if base_path.exists() and config.ANSWER_KEY.exists():
        out["evaluation"] = evaluate(json.loads(base_path.read_text(encoding="utf-8")),
                                     json.loads(config.ANSWER_KEY.read_text(encoding="utf-8")))
    if base_path.exists() and ext_path.exists():
        out["compare"] = compare(json.loads(base_path.read_text(encoding="utf-8")),
                                 json.loads(ext_path.read_text(encoding="utf-8")))
    return out


@app.get("/api/summary")
def summary_endpoint():
    return summary()

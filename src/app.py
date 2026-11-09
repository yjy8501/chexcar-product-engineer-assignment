"""FastAPI 서버. 계약은 specs/001-memo-to-work-order/contracts/api.md."""
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .config import RESULTS, WEB
from .knowledge import available_knowledge

app = FastAPI(title="검수 메모 오더 초안")


def _check_knowledge(name: str) -> str:
    if name not in available_knowledge():  # 경로로 쓰이므로 목록에 있는 이름만 받는다
        raise HTTPException(404, f"알 수 없는 지식 문서: {name}")
    return name


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/knowledge")
def knowledge():
    return {"names": available_knowledge()}


@app.get("/api/results")
def results(knowledge: str = "base"):
    """저장된 실행 결과. API 키나 CLI가 필요 없다 (FR-016)."""
    path = RESULTS / f"results_{_check_knowledge(knowledge)}.json"
    if not path.exists():
        raise HTTPException(404, "저장된 결과가 없다. `python -m src.run`으로 먼저 실행한다")
    return json.loads(path.read_text(encoding="utf-8"))

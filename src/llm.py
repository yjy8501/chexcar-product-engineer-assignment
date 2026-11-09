"""Claude Code CLI(`claude -p`) 호출. 실패하면 한 번 더 시도하고, 그래도 실패하면 사유를 담은 예외를 낸다 (FR-022)."""
import json
import subprocess
import tempfile
from typing import Callable

from .config import LLM_TIMEOUT_SEC, MAX_ATTEMPTS, MODEL


class LLMError(Exception):
    """한 번의 호출이 실패했다."""


class LLMFailure(Exception):
    """재시도까지 모두 실패했다."""

    def __init__(self, reason: str, attempts: int):
        super().__init__(reason)
        self.reason = reason
        self.attempts = attempts


def claude_cli_runner(system: str, user: str, schema: dict, model: str) -> dict:
    cmd = [
        "claude", "-p", "--model", model,
        "--output-format", "json",
        "--json-schema", json.dumps(schema, ensure_ascii=False),
        "--tools", "",
        "--no-session-persistence",
        "--setting-sources", "",
        "--system-prompt", system,
        user,
    ]
    try:
        # 프로젝트 파일을 읽지 않도록 빈 임시 폴더에서 실행한다
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=LLM_TIMEOUT_SEC, cwd=tmp)
    except FileNotFoundError as e:
        raise LLMError("claude CLI를 찾을 수 없다") from e
    except subprocess.TimeoutExpired as e:
        raise LLMError(f"시간 초과({LLM_TIMEOUT_SEC}초)") from e
    if proc.returncode != 0:
        raise LLMError(f"claude 종료 코드 {proc.returncode}: {proc.stderr.strip()[:200]}")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise LLMError(f"JSON이 아닌 응답: {proc.stdout[:200]}") from e
    if payload.get("is_error"):
        raise LLMError(f"claude 오류: {str(payload.get('result'))[:200]}")
    data = payload.get("structured_output")
    if not isinstance(data, dict):
        raise LLMError("structured_output이 없다")
    data["_cost_usd"] = payload.get("total_cost_usd", 0)
    return data


def complete_json(system: str, user: str, schema: dict, *, runner: Callable | None = None,
                  model: str = MODEL, max_attempts: int = MAX_ATTEMPTS) -> tuple[dict, int]:
    """(결과, 시도 횟수)를 낸다. 모두 실패하면 LLMFailure."""
    runner = runner or claude_cli_runner
    last = "알 수 없는 오류"
    for attempt in range(1, max_attempts + 1):
        try:
            return runner(system, user, schema, model), attempt
        except LLMError as e:
            last = str(e)
    raise LLMFailure(last, max_attempts)

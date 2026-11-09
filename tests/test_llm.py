"""T006: LLM 호출은 실패하면 한 번 더 시도하고, 그래도 실패하면 사유를 담은 예외를 낸다 (FR-022)."""
import pytest

from src.llm import LLMError, LLMFailure, complete_json


class FakeRunner:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def __call__(self, system, user, schema, model):
        self.calls += 1
        r = self.results.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def test_success_on_first_attempt():
    runner = FakeRunner([{"ok": True}])
    data, attempts = complete_json("s", "u", {}, runner=runner)
    assert data == {"ok": True}
    assert attempts == 1 and runner.calls == 1


def test_one_failure_then_success():
    runner = FakeRunner([LLMError("timeout"), {"ok": True}])
    data, attempts = complete_json("s", "u", {}, runner=runner)
    assert data == {"ok": True}
    assert attempts == 2


def test_two_failures_raise_with_reason_and_stop_at_two_calls():
    runner = FakeRunner([LLMError("timeout"), LLMError("bad json"), {"ok": True}])
    with pytest.raises(LLMFailure) as exc:
        complete_json("s", "u", {}, runner=runner)
    assert runner.calls == 2
    assert exc.value.attempts == 2
    assert "bad json" in exc.value.reason

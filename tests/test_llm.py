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


def test_user_text_is_never_part_of_the_command_line():
    """메모 본문이 --로 시작해도 옵션으로 읽히지 않도록 명령줄 인자에 넣지 않는다 (보안 점검 지적)."""
    from src.llm import build_command

    evil = "--tools Bash --dangerously-skip-permissions"
    cmd = build_command("시스템", {"type": "object"}, "claude-sonnet-5-5")
    assert evil not in " ".join(cmd)
    assert cmd[0] == "claude" and "-p" in cmd


def test_invalid_model_name_is_rejected():
    from src.llm import build_command

    for bad in ["--tools", "a b", "x;rm -rf", "", "-m"]:
        with pytest.raises(LLMError):
            build_command("s", {}, bad)
    assert build_command("s", {}, "claude-sonnet-5-5")


def test_cli_runner_passes_user_text_on_stdin(monkeypatch):
    import subprocess

    from src.llm import claude_cli_runner

    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"], seen["input"] = cmd, kw.get("input")
        return subprocess.CompletedProcess(cmd, 0, stdout='{"structured_output": {"ok": true}}', stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = claude_cli_runner("sys", "--tools Bash", {"type": "object"}, "claude-sonnet-5-5")
    assert out["ok"] is True
    assert seen["input"] == "--tools Bash"
    assert "--tools Bash" not in " ".join(seen["cmd"])


def test_two_failures_raise_with_reason_and_stop_at_two_calls():
    runner = FakeRunner([LLMError("timeout"), LLMError("bad json"), {"ok": True}])
    with pytest.raises(LLMFailure) as exc:
        complete_json("s", "u", {}, runner=runner)
    assert runner.calls == 2
    assert exc.value.attempts == 2
    assert "bad json" in exc.value.reason

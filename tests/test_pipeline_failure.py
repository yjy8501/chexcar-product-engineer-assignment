"""T015: 해석이 실패하면 코드 없이 문장만 나열하고 모두 확인필요 (FR-022, FR-008)."""
from src.knowledge import load_knowledge
from src.llm import LLMError
from src.pipeline import map_memo

K = load_knowledge("base")
INSPECTION = {"inspection_id": "INS-T1", "memo": "프론트범퍼 도색 필요. 본넷 탈부착 요망."}


class Runner:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def __call__(self, system, user, schema, model):
        self.calls += 1
        r = self.results.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


GOOD = {"overall": "정상", "excluded": [], "items": [
    {"status": "제안", "code": "BP-FR-PT", "qty": 1, "evidence": [0], "issue": None, "recommended": None, "alternatives": []},
    {"status": "제안", "code": "HD-00-RM", "qty": 1, "evidence": [1], "issue": None, "recommended": None, "alternatives": []},
]}


def test_failure_after_retry_lists_sentences_as_confirm():
    runner = Runner([LLMError("timeout"), LLMError("bad json")])
    d = map_memo(INSPECTION, K, runner=runner)
    assert runner.calls == 2
    assert d.overall == "판단불가"
    assert d.meta.attempts == 2 and "bad json" in d.meta.failure
    assert len(d.items) == 2
    assert all(i.status == "확인필요" and i.code is None for i in d.items)
    assert [i.evidence for i in d.items] == [[0], [1]]
    assert not any(i.status == "제안" for i in d.items)
    assert all(s.role == "애매" for s in d.sentences)


def test_one_failure_then_success_is_normal():
    runner = Runner([LLMError("timeout"), GOOD])
    d = map_memo(INSPECTION, K, runner=runner)
    assert d.meta.attempts == 2 and d.meta.failure is None
    assert d.overall == "정상"
    assert [i.code for i in d.items] == ["BP-FR-PT", "HD-00-RM"]


def test_malformed_result_is_treated_as_failure():
    runner = Runner([{"unexpected": 1}, {"unexpected": 2}])
    d = map_memo(INSPECTION, K, runner=runner)
    assert d.overall == "판단불가"
    assert d.meta.failure and not any(i.status == "제안" for i in d.items)

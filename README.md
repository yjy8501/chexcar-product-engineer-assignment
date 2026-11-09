채용 평가 목적으로만 제출합니다. 그 외의 이용은 협의가 필요합니다.

# 검수 메모를 작업 오더 초안으로

정비소 관리자가 검수 메모를 읽고 표준 작업 코드를 골라 오더를 만드는 일을 줄이기 위한 과제 제출물입니다. 메모를 읽어 코드, 수량, 근거 문장이 붙은 초안을 만들고, 애매한 항목은 추천과 함께 관리자에게 넘기며, 최종 승인은 항상 사람이 합니다.

## 보는 순서

1. `docs/design.md`: 설계 문서 (5분의 구성, 하지 않은 것, 틀렸을 때, 성공 측정, 가정, 현장에 물을 질문, 한계)
2. `report.html`: 브라우저로 열면 서버 없이 10건의 결과와 평가가 보입니다.
3. `docs/answer_key.md`: 정답표. 회사의 정답이 아니라 우리가 만든 해석입니다.

## 실행 방법

Python 3.11 이상과 [uv](https://docs.astral.sh/uv/)가 필요합니다.

```bash
uv venv && uv pip install -e ".[dev]"

.venv/bin/pytest                                  # 시험 (Claude 호출 없이 동작)
.venv/bin/python -m src.evaluate                  # 저장된 결과를 정답표와 비교
.venv/bin/python -m src.compare                   # 기본 문서와 보강 문서 비교
.venv/bin/uvicorn src.app:app --host 127.0.0.1    # 화면과 승인 (http://127.0.0.1:8000)
```

저장된 결과(`results/`)만 보는 데는 Claude가 필요 없습니다. 메모를 새로 해석하려면 로그인된 [Claude Code CLI](https://claude.com/claude-code)(`claude`)가 필요합니다.

```bash
.venv/bin/python -m src.run --knowledge base        # 10건을 해석해 results/results_base.json에 저장
.venv/bin/python -m src.run --knowledge extended    # 가정을 더한 보강 문서로 실행
.venv/bin/python -m src.build_static                # report.html 다시 만들기
```

10건을 한 번 돌리는 데 0.13~0.19달러가 들었습니다(캐시가 없던 첫 실행은 0.61달러).

서버에는 로그인이 없습니다. 로컬(127.0.0.1)에서만 켜 주세요.

## 어디까지 만들었나

| 만든 것 | 위치 |
|---|---|
| 메모를 문장으로 나누고 LLM이 해석, 프로그램이 검사해 오더 초안 만들기 | `src/pipeline.py`, `src/interpret.py`, `src/validator.py` |
| 해석 실패 시 문장만 나열하고 전부 확인필요로 두기 | `src/pipeline.py`, `src/llm.py` |
| 확인필요를 고르고 승인해 확정 오더 저장 (확인필요가 남으면 승인 불가) | `src/orders.py`, `src/app.py`, `web/index.html` |
| 정답표 평가, 기본/보강 문서 비교 | `src/evaluate.py`, `src/compare.py` |
| 용어집, 규칙, 말투 사전 (고치면 결과가 달라짐) | `knowledge/base/`, `knowledge/extended/` |
| 시험 91개 | `tests/` |

만들지 않은 것은 `docs/design.md` 2번에 이유와 함께 있습니다.

## 결과 데이터 구조

메모 한 건당 오더 초안 하나입니다. 문장 목록, 항목 목록(상태, 코드, 수량, 근거 문장 번호, 쟁점, 추천, 대안), 제외한 항목, 경고, 실행 정보로 이루어집니다. 자세한 정의는 `specs/001-memo-to-work-order/data-model.md`와 `specs/001-memo-to-work-order/contracts/draft.schema.json`에 있습니다.

## 폴더

```text
data/          받은 입력(inspections.json, work_codes.csv)과 정답표
knowledge/     용어집, 규칙, 말투 사전 (base: 문서에서 확인된 것, extended: 가정 포함)
src/           해석, 검사, 파이프라인, 서버, 평가
web/           결과 화면
results/       저장된 실행 결과
tests/         시험
docs/          설계 문서, 정답표
specs/         Spec Kit 산출물(spec, plan, tasks 등)
```

이 저장소는 Spec Kit으로 constitution, spec, clarify, plan, tasks, analyze, implement 순서를 거쳐 만들었고, 커밋 히스토리에 그 순서가 남아 있습니다.

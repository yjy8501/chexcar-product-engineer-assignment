# Quickstart: 검증 시나리오

이 문서는 spec의 검증 방법을 실행 절차로 옮긴 것이다. 명령은 구현이 끝난 뒤의 모양이며, 구현 전에는 아직 동작하지 않는다. 데이터 형식은 [data-model.md](data-model.md), 서버 형식은 [contracts/api.md](contracts/api.md)를 본다.

## 준비

```bash
uv venv && uv pip install -e ".[dev]"     # Python 3.14, FastAPI, Pydantic, pytest
claude --version                           # 새 메모를 해석할 때만 필요 (로그인된 Claude Code CLI)
```

## 시나리오

| # | 확인할 것 | 명령 | 기대 결과 | 연결 요구사항 |
|---|-----------|------|-----------|---------------|
| 1 | 검사 규칙과 승인 규칙이 동작한다 | `pytest` | 모두 통과. 가짜 근거, 코드표 밖 코드, 중복, 수량 어긋남, 해석 실패 재시도, 승인 거절(409, 422) 시험 포함 | FR-003, 004, 009, 011, 012, 022 |
| 2 | 10건을 실행해 결과를 저장한다 | `python -m src.run --knowledge base` | `results/results_base.json`이 만들어진다 | FR-001, 002, 016 |
| 3 | 정답표와 비교한다 | `python -m src.evaluate` | 건별 표와 합계가 나오고 "잘못 확정" 합계가 0이다 | FR-015, SC-001, 002, 003 |
| 4 | 보강 문서 전후를 비교한다 | `python -m src.run --knowledge extended` 후 `python -m src.compare` | 제안, 확인필요, 코드없음 개수와 달라진 건이 나온다 | FR-014, SC-004, 005 |
| 5 | 키 없이 결과를 본다 | `report.html`을 브라우저로 연다 | 서버와 CLI 없이 10건 결과와 문장 구분이 보인다 | FR-016, 017, SC-006 |
| 6 | 승인 흐름을 본다 | `uvicorn src.app:app` 후 화면에서 확인필요를 고르고 승인 | 확인필요가 남으면 승인이 막히고, 모두 고르면 `orders/`에 확정 오더가 저장된다 | FR-012 |
| 7 | 해석 실패를 만든다 | `pytest -k failure` | 재시도 1회 후 코드 제안 0개, 문장별 확인필요, 전체 판단불가 | FR-022 |
| 8 | 설계 문서를 읽는다 | `docs/design.md` | 네 질문의 답과 가정, 현장에 물을 질문, 성공 기준이 있다 | FR-018, 019, 021, SC-007 |
| 9 | README 대로 따라 한다 | `README.md`의 실행 방법을 처음부터 따라 한다 | 시나리오 5와 6이 된다 | FR-020 |

## 반복 실행 편차 측정 (Q11)

10건을 두 번 돌려 상태가 달라진 항목 수를 센다. 결과는 `docs/design.md`의 한계에 적는다.

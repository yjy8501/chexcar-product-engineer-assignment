# Implementation Plan: 검수 메모를 작업 오더 초안으로 바꾸기

**Branch**: `001-memo-to-work-order` | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-memo-to-work-order/spec.md`

## Summary

관리자가 읽던 자유 형식 검수 메모를 표준 작업 코드 오더 초안으로 바꾼다. LLM이 메모를 해석하고(항목 후보와 근거 문장 번호), 프로그램이 그 결과를 검사해서 틀린 것은 확인필요로 내린다. 확인필요가 남아 있으면 승인할 수 없고, 최종 승인은 사람이 한다. 효과와 한계는 정답표 평가와 보강 문서 비교로 숫자로 보인다. 근거는 [research.md](research.md)의 질문 원장에 있다.

## Technical Context

**Language/Version**: Python 3.14.7 (관찰: `python3 --version`)

**Primary Dependencies**: FastAPI, Pydantic, uvicorn, httpx(시험용). LLM은 `claude -p`(Claude Code CLI 2.1.318)

**Storage**: JSON 파일. 실행 결과 `results/`, 확정 오더 `orders/`

**Testing**: pytest

**Target Platform**: 개발자 노트북(macOS). 결과 화면은 브라우저

**Project Type**: 작은 웹 서비스(서버 하나와 정적 HTML 한 장)와 명령줄 실행기

**Performance Goals**: 없음. 과제 규모(메모 10건)이며 측정하지 않는다

**Constraints**: 처음 보는 메모를 새로 해석하려면 `claude` CLI 로그인이 필요하다. 저장된 결과를 보는 데는 필요 없다. 권장 소요 3시간이므로 작게 유지한다

**Scale/Scope**: 메모 10건, 표준 코드 35개

## Constitution Check

*GATE: Phase 0 전에 통과해야 하고, Phase 1 설계 뒤에 다시 확인한다.*

| 원칙 | 이 계획의 대응 | 결과 |
|------|----------------|------|
| I. 애매하면 확인필요 | 검사 규칙 V3, V4, V5, V10, V11이 모호한 항목을 확인필요로 내린다 (research D2) | 통과 |
| II. 잘못 확정 0 | 정답표 평가의 "잘못 확정" 합계를 성공 기준(SC-001)으로 둔다 | 통과 |
| III. 최종 승인은 사람 | `/api/orders`가 확인필요가 남으면 409, 코드표 밖 코드면 422를 낸다 | 통과 |
| IV. LLM 답은 프로그램이 검사 | 검사 규칙 V1~V11을 LLM 호출과 분리된 단계로 둔다 | 통과 |
| V. 모든 항목에 근거 | Item.evidence는 비어 있을 수 없고 V2가 검사한다. 제외 항목도 이유를 남긴다 | 통과 |
| 제품 제약: 일반 규칙, 정답표 한계, 작게 | 문서(지식 파일)로 분리하고 평가 결과를 "우리 해석과 일치"로 적는다 | 통과 |
| 작업 방식 | constitution, specify, clarify, plan 순서를 지켰다 | 통과 |

Phase 1 설계 뒤 재확인: 위반 없음. 새로 생긴 구조(데이터 모델, API 계약)가 원칙과 충돌하지 않는다.

## Project Structure

### Documentation (this feature)

```text
specs/001-memo-to-work-order/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── api.md
│   └── draft.schema.json
└── tasks.md             # /speckit-tasks 에서 만든다
```

### Source Code (repository root)

```text
data/
├── inspections.json     # 받은 입력
├── work_codes.csv       # 받은 입력
└── answer_key.json      # 정답표(우리 해석)
knowledge/
├── base/                # glossary.json, rules.json, tone.json
└── extended/            # 가정을 더한 문서
src/
├── config.py            # 경로, 모델 이름
├── models.py            # Pydantic 모델(Draft, Item 등. data-model.md)
├── catalog.py           # 코드표 읽기
├── sentences.py         # 메모를 문장으로 나누기
├── knowledge.py         # 지식 문서 읽기
├── llm.py               # claude CLI 호출, 재시도 1회
├── interpret.py         # 프롬프트와 LLM 출력 형식
├── validator.py         # 검사 규칙 V1~V11
├── pipeline.py          # 해석, 검사, 초안 만들기, 해석 실패 처리
├── run.py               # 10건 실행과 결과 저장
├── evaluate.py          # 정답표 비교
├── compare.py           # 기본본과 보강본 비교
├── orders.py            # 승인 검사와 확정 오더 저장
├── app.py               # FastAPI
└── build_static.py      # 서버 없이 보는 report.html 만들기
web/
└── index.html
tests/
├── test_validator.py
├── test_pipeline_failure.py
├── test_orders.py
└── test_evaluate.py
results/                 # 실행 결과 저장
orders/                  # 확정 오더 저장
docs/
└── design.md            # 설계 문서(네 가지 질문, 가정, 질문, 한계)
README.md
report.html
```

**Structure Decision**: 단일 프로젝트. 서버와 실행기가 같은 `src/`를 쓴다. 규모가 작아서 프론트와 백엔드를 나누지 않는다.

## Complexity Tracking

위반이 없어 비워 둔다.

## 근거 점검 (Evidence Gate, evidence-sdd)

*Phase 0 이후, Phase 1 이전에 확인한다.*

- [x] research.md가 질문 원장 형식이다 (질문 / 상태 / 결론 / 근거 / 확인 범위 / 남은 미확인)
- [x] `미해결` 질문이 없다. 남아 있다면 아래에 이유와 진행 여부를 적었다
- [x] 부재 주장("영향 없음", "사용처 없음")마다 확인 범위가 적혀 있다 (Q11: 온도 옵션이 없다는 주장은 도움말 일부 줄만 확인해 `부분 답변`)
- [x] spec의 `추정` 출처 MUST 요구사항을 이 계획이 그대로 확정하지 않는다 (research Q12에서 `추정`으로 유지하고 사용자 확인을 남김)

**남은 미해결 / 미확인**:

- 반복 실행 편차(Q11): 측정 전. 구현에서 10건을 두 번 돌려 확인한다.
- 정답표(Q9): 사용자의 최종 확인이 필요하다.
- 보강 문서의 가정(Q10)과 spec의 `추정` 요구사항(Q12): 사용자 확인이 필요하다.
- 처음 보는 메모에서의 정확도(Q1): 확인할 방법이 없어 설계 문서의 한계로 적는다.

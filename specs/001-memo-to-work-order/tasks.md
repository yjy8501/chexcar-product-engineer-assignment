---

description: "검수 메모를 작업 오더 초안으로 바꾸기 작업 목록"
---

# Tasks: 검수 메모를 작업 오더 초안으로 바꾸기

**Input**: `/specs/001-memo-to-work-order/`의 spec.md, plan.md, research.md, data-model.md, contracts/, quickstart.md

**Prerequisites**: plan.md, spec.md (모두 있음)

**Tests**: evidence-sdd 프리셋에 따라 모든 MUST 요구사항(FR)과 SC에 검증 태스크가 있다. 같은 요구사항의 검증 태스크가 구현 태스크보다 앞에 있다.

## Format: `[ID] [P?] [Story] Description (요구사항 ID)`

- **[P]**: 다른 파일이고 아직 끝나지 않은 태스크에 의존하지 않아 병렬로 할 수 있다
- 경로는 저장소 루트 기준이다 (단일 프로젝트: `src/`, `tests/`)
- 실제 LLM을 부르는 태스크는 로그인된 `claude` CLI가 필요하다. 나머지는 가짜 LLM으로 시험한다

---

## Phase 1: Setup

- [ ] T001 `pyproject.toml`을 만든다. 패키지는 `src`, 의존성은 fastapi, pydantic, uvicorn, 개발용 pytest, httpx, jsonschema (plan Technical Context)
- [ ] T002 [P] `uv venv`로 `.venv`를 만들고 `uv pip install -e ".[dev]"`를 실행한다. `python -c "import fastapi, pydantic"`와 `pytest --version`이 성공해야 한다 (research Q3의 남은 미확인 해소)
- [ ] T003 [P] 폴더 `tests/`, `results/`, `orders/`, `web/`, `knowledge/base/`, `knowledge/extended/`, `docs/`를 만든다. 빈 폴더에는 `.gitkeep`을 두고 `orders/*.json`은 `.gitignore`에 넣는다

---

## Phase 2: Foundational (모든 이야기가 기다리는 기반)

**Checkpoint**: 이 단계가 끝나야 US1~US3을 시작할 수 있다.

- [ ] T004 [P] 시험 작성: `tests/test_catalog.py` — `data/work_codes.csv`에서 코드 35개를 읽고, 없는 코드는 거절한다 (FR-003)
- [ ] T005 [P] 시험 작성: `tests/test_sentences.py` — 메모를 `(?<=[.!?])\s+|\n+` 기준으로 나누고 번호가 0부터 안정적으로 매겨진다 (FR-004, FR-013)
- [ ] T006 [P] 시험 작성: `tests/test_llm.py` — 가짜 실행기로 첫 호출 실패 후 두 번째 성공, 두 번 모두 실패하면 사유를 담은 예외를 낸다. 시도 횟수는 최대 2회다 (FR-022)
- [ ] T007 `src/config.py`를 만든다. 경로(data, knowledge, results, orders)와 모델 이름 `claude-sonnet-5-5`(환경변수로 바꿀 수 있음)
- [ ] T008 [P] `src/models.py`에 Pydantic 모델(Sentence, Item, Excluded, Draft, ConfirmedOrder)을 만든다. data-model.md 제약을 그대로 옮긴다: Item의 "상태가 제안이면 code와 qty가 있어야 하고, 코드는 코드표에 있어야 한다", evidence는 "비어 있으면 안 된다", qty는 minimum 1 또는 null, status는 제안, 확인필요, 코드없음 중 하나, Draft.overall은 정상, 작업없음, 판단불가 중 하나, meta.attempts는 minimum 1 (FR-001, FR-002)
- [ ] T009 [P] `src/catalog.py`를 만든다. 코드표 읽기와 코드 존재 확인 (FR-003; T004를 통과시킨다)
- [ ] T010 [P] `src/sentences.py`를 만든다 (FR-004, FR-013; T005를 통과시킨다)
- [ ] T011 `src/llm.py`를 만든다. `claude -p --model <모델> --output-format json --json-schema <스키마> --tools "" --no-session-persistence --setting-sources "" --system-prompt <...>`를 임시 폴더에서 실행하고 `structured_output`을 읽는다. 실패하면 자동으로 한 번 더 시도하고, 그래도 실패하면 사유를 담은 예외를 낸다 (FR-022; T006을 통과시킨다)
- [ ] T012 [P] `knowledge/base/glossary.json`, `rules.json`, `tone.json`을 만든다. 문서에서 근거를 찾은 것만 넣는다. 말투는 지시(도색, 탈부착 요망, 진행 부탁)와 확인필요(권장, ~할 듯, ~나을 것 같음, 점검 필요, 봐주세요)로 나눈다. "프싸", "휀다" 단독, 트레드 몇 mm, "1짝", 부분 광택은 넣지 않는다(문서에서 답을 찾지 못한 것) (FR-014, 명시 Assumptions 7번)
- [ ] T013 [P] `knowledge/extended/*.json`을 만든다. 기본본에 가정을 더한다(프싸=우측 앞휀다, 휀다 단독=앞휀다, 트레드 3mm 이하는 교환 대상, 1짝=타이어 1개, 광택만 적으면 전체 광택 등). 각 파일에 `"_note": "가정이며 점수에 넣지 않는다"`를 둔다 (FR-014)

---

## Phase 3: User Story 1 - 메모 한 건에서 오더 초안을 받는다 (Priority: P1) MVP

**Goal**: 메모 한 건을 넣으면 코드, 수량, 근거 문장, 상태가 붙은 초안이 나오고, 틀린 것은 확인필요로 내려간다.

**Independent Test**: 가짜 LLM으로 `pytest tests/test_validator.py tests/test_pipeline_failure.py tests/test_contract.py tests/test_knowledge.py`가 통과하고, 실제 `python -m src.run --knowledge base`가 `results/results_base.json`을 만든다.

### 시험을 먼저 쓴다 (구현 전에 실패하는 것을 확인한다)

- [ ] T014 [P] [US1] `tests/test_validator.py`에 규칙별 시험을 쓴다: `test_v1_unknown_code_becomes_confirm`, `test_v2_missing_evidence_becomes_confirm`, `test_v3_weak_tone_becomes_confirm`, `test_v4_exchange_without_word_becomes_confirm`, `test_v5_tire_qty_over_2_becomes_confirm`, `test_v5_brake_front_rear_unknown_becomes_confirm`, `test_v6_duplicate_codes_merged`, `test_v7_unfit_overall_has_no_suggestion`, `test_v8_unlinked_sentence_warns`, `test_v9_lost_work_becomes_no_code`, `test_v10_null_code_with_alternatives_becomes_confirm`, `test_v11_panel_paint_needs_panel_word` (FR-002, FR-003, FR-004, FR-005, FR-007, FR-008, FR-009, FR-011, FR-013)
- [ ] T015 [P] [US1] `tests/test_pipeline_failure.py`에 `test_failure_after_retry_lists_sentences_as_confirm`(두 번 실패하면 코드 제안 0개, 문장별 확인필요, overall 판단불가, meta.failure에 사유, attempts 2)와 `test_one_failure_then_success_is_normal`을 쓴다 (FR-022, FR-008)
- [ ] T016 [P] [US1] `tests/test_contract.py`에 `test_drafts_match_schema`(가짜 LLM 출력으로 만든 초안이 `specs/001-memo-to-work-order/contracts/draft.schema.json`을 통과), `test_confirm_item_has_issue_and_recommendation`(확인필요 항목에 issue와 추천/대안이 채워짐), `test_excluded_item_has_reason`을 쓴다 (FR-001, FR-002, FR-006, FR-010)
- [ ] T017 [P] [US1] `tests/test_knowledge.py`에 `test_glossary_entry_changes_prompt`(용어집에 약어를 추가하면 해석 프롬프트에 반영됨)를 쓴다 (FR-014)

### 구현

- [ ] T018 [US1] `src/knowledge.py`를 만든다. `knowledge/<이름>/`의 세 파일을 읽는다 (FR-014; T017)
- [ ] T019 [US1] `src/interpret.py`를 만든다. 시스템 프롬프트와 LLM 출력 스키마. 규칙: 하지 않는다는 문장은 제외 항목으로, 코드표에 없는 작업은 코드없음으로, 하나로 고를 수 없으면 확인필요로, 메모만으로 고를 수 없으면 판단불가로. 지식 문서의 내용을 프롬프트에 넣는다 (FR-005, FR-007, FR-008, FR-010, FR-014)
- [ ] T020 [US1] `src/validator.py`를 만든다. research D2의 V1~V11 (T014를 통과시킨다) (FR-002~FR-005, FR-007~FR-009, FR-011, FR-013)
- [ ] T021 [US1] `src/pipeline.py`를 만든다. 문장 나누기, LLM 호출, 검사, 문장 역할(반영, 제외, 애매, 연결없음) 계산, Draft 만들기. LLM 실패 시 FR-022 초안 (T015, T016을 통과시킨다) (FR-001, FR-002, FR-006, FR-022)
- [ ] T022 [US1] `src/run.py`를 만든다. `python -m src.run --knowledge base|extended [--only ids]`가 10건을 실행해 `results/results_<이름>.json`(모델, 지식 이름, 초안 목록)에 저장한다 (FR-001, FR-002, FR-016)
- [ ] T023 [US1] `src/app.py`에 읽기 전용 엔드포인트 `GET /`, `GET /api/knowledge`, `GET /api/results`를 만든다. contracts/api.md 형식을 따른다 (FR-016)
- [ ] T024 [US1] `web/index.html`에 결과 화면을 만든다. 메모 10건 목록, 문장을 반영/제외/애매로 색 구분, 제안/확인필요/코드없음 구분 표, 제외 항목, 경고, 지식 문서 선택 (FR-017, FR-001)
- [ ] T025 [US1] 실제 실행 검증: `python -m src.run --knowledge base`를 실행하고 `results/results_base.json`의 모든 코드가 코드표에 있는지 확인한 뒤 커밋한다. 상태별 개수를 기록한다 (FR-001, FR-002, FR-003)
- [ ] T026 [US1] 수동 검증: `uvicorn src.app:app`을 띄우고 브라우저에서 10건의 문장 색 구분과 상태 표를 본다. 자동화하지 못하는 이유: 색 구분은 눈으로 보는 요구사항이다 (FR-017)

**Checkpoint**: 이 시점에 US1만으로 "메모를 넣으면 초안이 나온다"가 동작하고 단독으로 시험할 수 있다.

---

## Phase 4: User Story 2 - 애매한 항목을 고르고 승인한다 (Priority: P2)

**Goal**: 확인필요를 모두 정리해야 승인되고, 승인하면 확정 오더가 저장된다.

**Independent Test**: `pytest tests/test_orders.py`가 통과하고, 화면에서 확인필요가 남으면 승인이 막힌다.

- [ ] T027 [P] [US2] `tests/test_orders.py`에 `test_approve_blocked_when_confirm_remains`(409와 남은 item id), `test_approve_saves_confirmed_order`(200과 `orders/<id>.json`), `test_skip_choice_excluded_from_order`, `test_unknown_code_rejected`(422), `test_missing_draft_404`, `test_map_failure_returns_fallback_draft`(`/api/map` 실패 시 FR-022 초안), `test_choose_any_catalog_code_when_no_recommendation`(추천이 없는 항목에 코드표의 코드를 고를 수 있다), `test_no_code_item_does_not_block_approval`(코드없음은 승인을 막지 않고 확정 오더에 들어가지 않는다)를 쓴다. 저장 폴더는 임시 폴더를 쓴다 (FR-012, FR-022)
- [ ] T028 [US2] `src/orders.py`를 만든다. 선택 검증(확인필요 모두 해결, 코드표 확인), 확정 오더 만들기와 저장 (data-model.md ConfirmedOrder: lines의 source는 제안승인 또는 직접선택, skipped, approved_at) (FR-012; T027)
- [ ] T029 [US2] `src/app.py`에 `POST /api/orders`, `GET /api/orders`, `POST /api/map`을 추가한다. 응답 코드는 contracts/api.md (FR-012, FR-022)
- [ ] T030 [US2] `web/index.html`에 승인 화면을 추가한다. 확인필요마다 추천과 대안을 고르거나 "이 작업은 하지 않음"을 고르고, 모두 정리되기 전에는 승인 버튼이 눌리지 않는다. 제안 항목은 한 번에 승인한다 (FR-012)
- [ ] T031 [US2] 수동 검증: 화면에서 확인필요를 남긴 채 승인이 막히는 것, 모두 고른 뒤 승인하면 `orders/`에 파일이 생기는 것을 본다. 자동화하지 못하는 이유: 화면 버튼의 막힘 상태는 눈으로 확인한다. 서버 쪽 규칙은 T027이 자동으로 검증한다 (FR-012)

**Checkpoint**: US1과 US2가 모두 동작한다.

---

## Phase 5: User Story 3 - 효과와 한계를 숫자로 확인한다 (Priority: P3)

**Goal**: 키와 CLI 없이 결과를 열고, 정답표와 비교한 평가와 기본/보강 비교를 본다.

**Independent Test**: `pytest tests/test_evaluate.py tests/test_compare.py tests/test_report.py`가 통과하고, `report.html`이 서버 없이 열린다.

- [ ] T032 [P] [US3] `tests/test_evaluate.py`에 `test_wrong_confirm_counted`(금지 코드 또는 max_qty 초과가 제안에 있으면 센다), `test_missing_suggestion_counted`, `test_over_confirm_counted`, `test_overall_mismatch_counted`, `test_exit_code_nonzero_when_wrong_confirm`을 쓴다 (FR-015, SC-001, SC-002, SC-003)
- [ ] T033 [P] [US3] `tests/test_compare.py`에 `test_compare_counts_per_status`(기본/보강 결과의 제안, 확인필요, 코드없음 개수와 달라진 건), `test_per_inspection_counts_reported`를 쓴다 (FR-014, SC-004, SC-005)
- [ ] T034 [P] [US3] `tests/test_report.py`에 `test_report_embeds_results_and_has_no_external_requests`(결과가 들어 있고 외부 주소 요청이 없다), `test_report_has_all_inspections`를 쓴다 (FR-016, SC-006)
- [ ] T035 [US3] `data/answer_key.json`을 만든다. data-model.md의 AnswerKeyEntry 형식(overall, suggest, confirm 묶음, no_code, forbidden)으로 10건. 이전 시도의 정답표 초안(저장소 밖 보관본)을 참고하되, 항목마다 근거를 다시 확인한다. 사람이 읽는 표 `docs/answer_key.md`도 같이 쓴다 (FR-015, SC-002, SC-003)
- [ ] T036 [US3] 사용자 확인: 정답표 초안을 사용자에게 보여주고 승인받는다. 확인 전에는 평가 결과를 "회사의 정답"으로 쓰지 않는다 (research Q9의 남은 미확인, spec Assumptions 3번)
- [ ] T037 [US3] `src/evaluate.py`를 만든다. 지표는 잘못 확정, 빠뜨린 제안, 지나친 확인필요, 묻힌 쟁점, 전체 판정 불일치. 기본본만 점수로 계산하고 보강본은 비교용으로만 표시한다. 잘못 확정이 1건이라도 있으면 종료 코드 1 (FR-015, SC-001~SC-003; T032)
- [ ] T038 [US3] `src/compare.py`를 만든다. 기본본과 보강본의 개수 비교와 달라진 건 (FR-014, SC-004, SC-005; T033)
- [ ] T039 [US3] `src/build_static.py`를 만든다. 저장된 결과를 `web/index.html`에 넣어 서버 없이 열리는 `report.html`을 만든다. raw 출력은 빼고, 승인 단계는 서버가 있을 때만 동작한다고 화면에 표시한다 (FR-016, FR-017, SC-006; T034)
- [ ] T040 [US3] 실제 실행 검증: `python -m src.run --knowledge extended` 후 `python -m src.evaluate`와 `python -m src.compare`를 실행한다. 잘못 확정 합계와 제안 개수 변화를 기록하고 커밋한다 (SC-001~SC-005)
- [ ] T041 [US3] 수동 검증: 서버를 끄고 `report.html`을 브라우저로 열어 10건과 평가 표가 보이는지 확인한다. 자동화하지 못하는 이유: 화면 렌더링은 눈으로 확인한다. 외부 요청 없음은 T034가 자동으로 검증한다 (FR-016, FR-017, SC-006)

**Checkpoint**: 세 이야기가 모두 동작한다.

---

## Phase 6: 문서와 마무리

- [ ] T042 [P] 수동 점검표(T043, T044가 끝난 뒤 실행): (1) 설계 문서에 5분의 구성, 공략과 포기, 틀렸을 때와 사람 확인 단계, 성공 측정 네 제목이 있다 (2) 가정 목록과 현장에 물을 질문이 있다 (3) 성공 기준에 "도입 전" 기준선과 "0건"이 있다 (4) LLM 선택 이유와 규칙 대비 판단이 있다 (5) README 첫 줄이 "채용 평가 목적으로만 제출합니다. 그 외의 이용은 협의가 필요합니다"이고 실행 방법 제목이 있다. 자동 시험으로 만들지 않는 이유: 문서가 설득력 있는지는 읽어야 판단되고, 제목 존재만 보는 시험은 효과가 작으며 과제가 테스트를 평가하지 않는다 (FR-018, FR-019, FR-020, FR-021, SC-007)
- [ ] T043 `docs/design.md`를 쓴다. 네 질문(5분의 구성과 병목, 공략하는 것과 하지 않는 것과 이유, 틀렸을 때와 사람 확인 단계, 성공 측정), 가정 목록, 현장에 물을 질문, 한계, LLM 선택 이유와 규칙 대비 판단. 성공 기준은 spec Clarifications Q3대로 "건당 시간이 도입 전 기준선보다 짧고, 틀린 오더가 현장까지 나간 건수 0건"이며 기준선은 도입 전 2주에 같은 방식으로 잰다. 측정 기능은 만들지 않았다고 적는다 (FR-018, FR-019, FR-021, SC-007)
- [ ] T044 `README.md`를 쓴다. 첫 줄은 "채용 평가 목적으로만 제출합니다. 그 외의 이용은 협의가 필요합니다". 실행 방법, 어디까지 만들었는지, 결과 데이터 구조(data-model.md 링크) (FR-020)
- [ ] T045 반복 실행 편차를 잰다 (FR-018). `python -m src.run --knowledge base`를 두 번 실행해 상태가 달라진 항목 수를 세고 `docs/design.md`의 한계에 적는다 (research Q11)
- [ ] T046 10건을 한 번 돌릴 때의 LLM 비용을 실행 결과의 `total_cost_usd` 합으로 재서 README에 적는다 (research D4)
- [ ] T047 `quickstart.md`의 시나리오 1~9를 처음부터 따라 한다. 모든 시험을 돌리고 아래 추적표의 상태와 실행 근거를 채운다. 사용자가 `docs/design.md`와 README를 읽고 내용을 확인한다
- [ ] T048 완료 보고에 research.md의 `부분 답변` 5개의 최종 상태와 spec의 `추정` 요구사항 11개(FR-002, 004, 013, 014, 015, 016, 017, 021과 SC-004, 005, 006)의 사용자 확인 결과를 적는다

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → (US1 → US2, US3). US2는 US1의 결과 화면과 서버를, US3은 US1의 저장된 결과를 쓴다. US2와 US3은 서로 독립이라 병렬로 할 수 있다.
- 같은 요구사항의 시험 태스크가 구현 태스크보다 앞선다. 시험이 실패하는 것을 확인한 뒤 구현한다.
- 실제 LLM을 쓰는 T025, T040, T045, T046은 `claude` CLI 로그인이 필요하다.

### Parallel 예

```text
Phase 2 시험: T004, T005, T006
US1 시험: T014, T015, T016, T017
US3 시험: T032, T033, T034
```

## Implementation Strategy

- MVP: Phase 1~3 (US1)만 끝나도 "메모를 넣으면 근거 붙은 초안이 나온다"를 보일 수 있다.
- 시간이 모자라면 US3의 보강 비교(T033, T038)와 반복 편차(T045)를 줄이고(문서 점검 T042는 처음부터 수동이다), 설계 문서(T043)는 줄이지 않는다. 과제 페이지가 "구현이 절반만 되어 있어도 설계가 탄탄하면 충분히 통과"한다고 했다.
- 단계마다 커밋한다. 커밋 히스토리는 지우지 않는다(Assumptions 11번).

---

## 요구사항-검증 추적표 (evidence-sdd)

상태는 모두 `미검증`이다. implement 단계에서만 갱신한다.

| 요구사항 | 구현 태스크 | 검증 태스크 | 검증 대상 | 상태 | 실행 근거 |
|----------|-------------|-------------|-----------|------|-----------|
| FR-001 | T008, T019, T021, T022, T024 | T016, T025 | tests/test_contract.py#test_drafts_match_schema, `python -m src.run --knowledge base` | 미검증 | |
| FR-002 | T008, T020, T021 | T014, T016 | tests/test_validator.py#test_v7_unfit_overall_has_no_suggestion, test_contract.py#test_drafts_match_schema | 미검증 | |
| FR-003 | T009, T020 | T004, T014, T025 | tests/test_catalog.py, test_validator.py#test_v1_unknown_code_becomes_confirm | 미검증 | |
| FR-004 | T010, T020 | T005, T014 | tests/test_validator.py#test_v2_missing_evidence_becomes_confirm | 미검증 | |
| FR-005 | T019, T020 | T014 | tests/test_validator.py#test_v3_weak_tone_becomes_confirm, test_v4_exchange_without_word_becomes_confirm, test_v11_panel_paint_needs_panel_word | 미검증 | |
| FR-006 | T019, T021 | T016 | tests/test_contract.py#test_confirm_item_has_issue_and_recommendation | 미검증 | |
| FR-007 | T019, T020 | T014 | tests/test_validator.py#test_v9_lost_work_becomes_no_code, test_v10_null_code_with_alternatives_becomes_confirm | 미검증 | |
| FR-008 | T019, T020, T021 | T014, T015 | tests/test_validator.py#test_v7_unfit_overall_has_no_suggestion, test_pipeline_failure.py | 미검증 | |
| FR-009 | T020 | T014 | tests/test_validator.py#test_v6_duplicate_codes_merged | 미검증 | |
| FR-010 | T019, T021 | T016 | tests/test_contract.py#test_excluded_item_has_reason | 미검증 | |
| FR-011 | T020 | T014 | tests/test_validator.py#test_v5_tire_qty_over_2_becomes_confirm, test_v5_brake_front_rear_unknown_becomes_confirm | 미검증 | |
| FR-012 | T028, T029, T030 | T027, T031 | tests/test_orders.py (409, 422, 저장, 추천 없는 항목의 코드 선택, 코드없음이 승인을 막지 않음), 수동 절차 T031 | 미검증 | |
| FR-013 | T010, T020 | T005, T014 | tests/test_validator.py#test_v8_unlinked_sentence_warns | 미검증 | |
| FR-014 | T012, T013, T018, T038 | T017, T033, T040 | tests/test_knowledge.py#test_glossary_entry_changes_prompt, test_compare.py | 미검증 | |
| FR-015 | T035, T037 | T032, T040 | tests/test_evaluate.py, `python -m src.evaluate` | 미검증 | |
| FR-016 | T022, T023, T039 | T034, T041 | tests/test_report.py#test_report_embeds_results_and_has_no_external_requests, 수동 절차 T041 | 미검증 | |
| FR-017 | T024, T039 | T026, T041 | 수동 절차 T026, T041 (색 구분은 눈으로 확인) | 미검증 | |
| FR-018 | T043 | T042, T047 | 수동 점검표 T042(1), 사용자가 읽는 절차 T047 | 미검증 | |
| FR-019 | T043 | T042 | 수동 점검표 T042(2) | 미검증 | |
| FR-020 | T044 | T042, T047 | 수동 점검표 T042(5), quickstart 시나리오 9 | 미검증 | |
| FR-021 | T043 | T042 | 수동 점검표 T042(4) | 미검증 | |
| FR-022 | T006, T011, T021, T029 | T006, T015, T027 | tests/test_llm.py, tests/test_pipeline_failure.py#test_failure_after_retry_lists_sentences_as_confirm, test_orders.py#test_map_failure_returns_fallback_draft | 미검증 | |
| SC-001 | T037 | T032, T040 | `python -m src.evaluate` 종료 코드 0과 잘못 확정 0 | 미검증 | |
| SC-002 | T035, T037 | T032, T040 | tests/test_evaluate.py#test_wrong_confirm_counted, `python -m src.evaluate` | 미검증 | |
| SC-003 | T035, T037 | T032, T040 | tests/test_evaluate.py#test_overall_mismatch_counted, `python -m src.evaluate` | 미검증 | |
| SC-004 | T038 | T033, T040 | tests/test_compare.py#test_compare_counts_per_status, `python -m src.compare` | 미검증 | |
| SC-005 | T038 | T033, T040 | tests/test_compare.py#test_per_inspection_counts_reported | 미검증 | |
| SC-006 | T039 | T034, T041 | tests/test_report.py, 수동 절차 T041 | 미검증 | |
| SC-007 | T043 | T042, T047 | 수동 점검표 T042(3), 사용자가 읽는 절차 T047 | 미검증 | |

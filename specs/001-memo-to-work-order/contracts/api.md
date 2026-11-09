# Contract: HTTP API

서버는 FastAPI 하나이고 화면은 정적 HTML이다. 결과 형식은 [draft.schema.json](draft.schema.json)을 따른다.

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 화면(`web/index.html`) |
| GET | `/api/knowledge` | 사용할 수 있는 지식 문서 이름 목록 (`base`, `extended`) |
| GET | `/api/results?knowledge=base` | 저장된 실행 결과(초안 목록)를 낸다. API 키나 CLI가 필요 없다 (FR-016) |
| POST | `/api/map` | 메모 한 건을 새로 해석한다. 본문 `{inspection_id 또는 memo, knowledge}`. `claude` CLI가 필요하다. 응답은 Draft |
| POST | `/api/orders` | 승인한다. 본문 `{inspection_id, knowledge, selections: [{item_id, choice, qty}]}`. `choice`는 코드 또는 `"skip"`. 추천이 없는 항목은 코드표의 아무 코드를 고를 수 있다(코드표 검사는 유지) |
| GET | `/api/orders` | 저장된 확정 오더 목록 |

## POST /api/orders 응답

| 코드 | 의미 |
|------|------|
| 200 | 확정 오더를 저장했다. 본문은 ConfirmedOrder |
| 409 | 확인필요 항목이 남아 있다. 본문에 남은 item id 목록 (FR-012) |
| 422 | 코드표에 없는 코드가 들어 있다 (FR-012) |
| 404 | 해당 초안이 저장된 결과에 없다 |

## 불변 조건

- 모든 응답의 코드는 코드표에 있다 (FR-003).
- 승인 흐름은 `inspection_id`가 있는 메모에서만 동작한다. `memo`만 넣은 자유 입력은 해석 결과만 보여주고 승인과 저장은 하지 않는다.
- `/api/map`이 실패하면 FR-022의 초안(판단불가, 문장별 확인필요)을 200으로 돌려주고 `meta.failure`에 사유를 담는다.

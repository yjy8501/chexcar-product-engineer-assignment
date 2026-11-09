# Data Model: 검수 메모를 작업 오더 초안으로 바꾸기

**Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

결과 데이터 구조는 직접 설계한다(과제 페이지 "결과 데이터 구조도 직접 설계해 주세요"). 형식 정의는 [contracts/draft.schema.json](contracts/draft.schema.json)에 둔다.

## 엔티티

### Inspection (검수 메모, 입력)
`data/inspections.json`의 한 건. 바꾸지 않는다.

| 필드 | 설명 |
|------|------|
| inspection_id | 예: INS-001 |
| vehicle | model, year, mileage_km |
| inspector, inspected_at | 검수자, 시각 |
| memo | 자유 형식 본문 |

### WorkCode (표준 작업 코드, 입력)
`data/work_codes.csv`의 한 줄(35개). 바꾸지 않는다.

| 필드 | 설명 |
|------|------|
| code | 예: BP-FR-PT |
| name, part | 이름, 부위 |
| hours, price | 공임 시간, 가격 |
| note | 비고(수량 단위 등). 예: `1짝 기준 공임 포함` |

### Sentence (메모 문장)
메모를 문장으로 나눈 것. 번호로 근거를 가리킨다.

| 필드 | 설명 |
|------|------|
| idx | 0부터 시작하는 번호 |
| text | 원문 |
| role | 반영, 제외, 애매, 연결없음 중 하나. 항목과의 연결에서 계산한다 |

### Item (작업 항목)
메모에서 읽어 낸 작업 하나.

| 필드 | 설명 |
|------|------|
| id | 초안 안에서 유일한 번호 |
| status | 제안, 확인필요, 코드없음 |
| code | 코드표의 코드. 코드없음이거나 해석 실패이면 null |
| qty | 수량. 모르면 null |
| evidence | 근거 문장 번호 목록. 비어 있으면 안 된다 |
| issue | 확인필요이면 쟁점 한 줄, 코드없음이면 이유 |
| recommended | 확인필요의 추천 `{code, qty}` 또는 null |
| alternatives | 대안 `{code, qty}` 목록 |
| downgraded_by | 프로그램 검사가 상태를 내렸다면 규칙 ID(V1 등). 아니면 null |

규칙: 상태가 제안이면 code와 qty가 있어야 하고, 코드는 코드표에 있어야 한다.

### Excluded (제외 항목)
하지 않기로 한 작업. `{evidence, reason}`. 제안 목록에 들어가지 않는다.

### Draft (오더 초안, 출력)
한 메모에서 나온 결과 전체.

| 필드 | 설명 |
|------|------|
| inspection_id, memo | 입력 |
| sentences | Sentence 목록 |
| overall | 정상, 작업없음, 판단불가 |
| items | Item 목록 |
| excluded | Excluded 목록 |
| warnings | 누락 경고 등 문자열 목록 |
| meta | model, knowledge(base 또는 extended), attempts(시도 횟수), failure(해석 실패 사유 또는 null), cost_usd(해석 비용, 참고용, 없을 수 있음) |

해석이 실패한 초안(FR-022): overall은 판단불가, items는 문장마다 하나씩 확인필요(code null), meta.failure에 사유를 넣는다.

### ConfirmedOrder (확정 오더)
관리자가 승인한 결과. `orders/<inspection_id>.json`에 저장한다.

| 필드 | 설명 |
|------|------|
| inspection_id, knowledge | 어떤 초안을 승인했는가 |
| lines | `{code, qty, source}` 목록. source는 제안승인, 직접선택 중 하나 |
| skipped | "이 작업은 하지 않음"을 고른 항목 id와 이유 |
| manual | 코드없음이라 확정 오더에 들어가지 않고 수동 처리가 필요한 항목 id 목록 |
| approved_at | 승인 시각 |

### AnswerKeyEntry (정답표, 평가용)
`data/answer_key.json`의 한 건.

| 필드 | 설명 |
|------|------|
| inspection_id | |
| overall | 기대하는 전체 판정 |
| suggest | `{code, qty}` 목록: 제안이어야 하는 것 |
| confirm | 코드 묶음 목록: 확인필요여야 하는 것(묶음 안의 코드 중 하나라도 있으면 충족) |
| no_code | 코드없음 개수 |
| forbidden | `{code, max_qty}` 목록: 나오면 안 되는 것 |

정답표는 우리가 만든 해석이다(spec Assumptions 3번).

### KnowledgeSet (지식 문서)
`knowledge/<name>/` 아래 JSON 세 개.

| 파일 | 내용 |
|------|------|
| glossary.json | 현장 약어와 부위 |
| rules.json | 수량과 부위 해석 규칙 |
| tone.json | 지시어, 약한말투, 교환_근거어 |

`base`는 문서에서 근거를 찾은 것만, `extended`는 가정을 더한 것이다.

## 상태 전이

- 항목: 제안 또는 확인필요 또는 코드없음으로 시작한다. 프로그램 검사에서 제안이 확인필요로 내려갈 수 있고, 반대로 올라가지는 않는다.
- 초안: 확인필요 항목이 하나라도 남아 있으면 승인할 수 없다. 모두 코드를 고르거나 "하지 않음"을 고르면 승인할 수 있다.
- 코드없음 항목은 승인을 막지 않고, 확정 오더에 들어가지 않으며 화면에 "수동 처리 필요"로 표시된다(코드가 없다).

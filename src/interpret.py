"""LLM이 메모를 읽고 항목 후보를 내도록 하는 프롬프트와 출력 형식. 해석만 맡기고 검사는 validator가 한다."""
from typing import Callable

from .catalog import load_catalog
from .knowledge import Knowledge
from .llm import complete_json

_CODE_QTY = {
    "type": ["object", "null"],
    "properties": {"code": {"type": "string"}, "qty": {"type": ["integer", "null"]}},
    "required": ["code", "qty"],
}

RAW_SCHEMA = {
    "type": "object",
    "properties": {
        "overall": {"enum": ["정상", "작업없음", "판단불가"]},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "status": {"enum": ["제안", "확인필요", "코드없음"]},
                    "code": {"type": ["string", "null"]},
                    "qty": {"type": ["integer", "null"]},
                    "evidence": {"type": "array", "items": {"type": "integer"}},
                    "issue": {"type": ["string", "null"]},
                    "recommended": _CODE_QTY,
                    "alternatives": {"type": "array", "items": _CODE_QTY},
                },
                "required": ["status", "code", "qty", "evidence", "issue", "recommended", "alternatives"],
            },
        },
        "excluded": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"evidence": {"type": "array", "items": {"type": "integer"}}, "reason": {"type": "string"}},
                "required": ["evidence", "reason"],
            },
        },
    },
    "required": ["overall", "items", "excluded"],
}

_INSTRUCTIONS = """당신은 중고차 정비소에서 검수자가 쓴 메모를 읽고, 관리자가 작업 오더를 만들 수 있도록 표준 작업 코드로 정리하는 도우미입니다.
오더가 틀리면 현장에서 그대로 작업이 진행되고 한 건에 수십만 원이 걸립니다. 그래서 확실하지 않으면 추측하지 말고 확인필요로 넘기세요.

## 출력
메모는 번호가 붙은 문장 목록으로 주어집니다(번호는 0부터). 각 항목의 evidence에는 근거가 된 문장 번호를 적습니다.

항목의 상태:
- 제안: 표준 코드표에서 정확히 하나의 코드와 수량을 확실하게 고를 수 있는 경우. code와 qty를 채웁니다.
- 확인필요: 하나로 고를 수 없는 경우(말투가 권장이나 추측이라 지시인지 모름, 위치나 수량이 빠짐, 후보가 여럿). code는 null로 두고 issue에 쟁점을 한 줄로 적고, recommended에 가장 그럴듯한 코드와 수량을, alternatives에 다른 후보를 적습니다.
- 코드없음: 메모가 작업을 말하지만 코드표에 맞는 코드가 없는 경우. code는 null, issue에 이유를 적습니다. 비슷한 다른 코드에 억지로 연결하지 마세요.

excluded: 메모가 '하지 않는다', '필요 없다', '이미 했다'고 적은 작업입니다. 이유를 적습니다. 제안에 넣지 마세요.

overall: 정상(처리할 항목이 있음), 작업없음(해야 할 작업이 하나도 없음), 판단불가(메모만으로 어떤 작업을 해야 하는지 고를 수 없음. 이때 어떤 코드도 제안하지 마세요).

## 지침
1. 메모에 적힌 작업만 다룹니다. 메모에 없는 작업을 덧붙이지 마세요.
2. 같은 부품을 두 번 적었으면 한 항목으로 합치고 evidence에 두 문장을 모두 적으세요.
3. 한 문장에 작업이 여럿이면 항목을 나누세요.
4. 문장 하나를 근거로 쓰고도 확신이 없으면 확인필요입니다. 애매하면 확인필요가 맞습니다.
5. 코드와 수량은 코드표의 이름과 비고를 따릅니다. 비고의 단위(1짝 기준, 전륜 또는 후륜 기준, 1매 기준)와 메모의 표현이 맞는지 모르면 확인필요입니다.
6. 코드는 반드시 코드표에 있는 코드만 쓰세요.
7. 점검, 확인, 진단처럼 코드표에 해당 작업이 없는 일은 비슷한 교환 코드에 연결하지 말고 코드없음으로 두세요. 교환 코드는 메모가 교환이나 교체를 말할 때만 추천합니다.
8. 판단불가는 어떤 부위를 어떻게 하라는 것인지 전혀 알 수 없을 때만 씁니다. 구체적인 부품이나 증상(예: 모터 소음)이 적혀 있는데 코드표에 해당 작업이 없으면 판단불가가 아니라 코드없음입니다."""


def build_system_prompt(knowledge: Knowledge, catalog: dict | None = None) -> str:
    catalog = catalog if catalog is not None else load_catalog()
    parts = [_INSTRUCTIONS]

    parts.append("## 규칙 (문서)")
    parts += [f"- [{r['id']}] {r['text']}" for r in knowledge.rules.get("rules", [])]

    parts.append("## 용어집 (문서)")
    parts += [f"- {t['term']}: {t['means']}" for t in knowledge.glossary.get("terms", [])]

    tone = knowledge.tone
    parts.append("## 말투 사전 (문서)")
    parts.append(f"- 지시로 보는 말: {', '.join(tone.get('지시어', []))}")
    parts.append(f"- 추천이나 추측이라 확인필요로 보는 말: {', '.join(tone.get('약한말투', []))}")
    parts.append(f"- 교환의 근거가 되는 말: {', '.join(tone.get('교환_근거어', []))}")
    parts.append(f"- 작업이 필요 없다는 뜻의 말: {', '.join(tone.get('제외_표현', []))}")

    parts.append("## 표준 작업 코드표 (코드 | 이름 | 부위 | 비고)")
    parts += [f"{c['code']} | {c['name']} | {c['part']} | {c['note'] or '-'}" for c in catalog.values()]
    return "\n".join(parts)


def build_user_prompt(sentences: list[str]) -> str:
    lines = "\n".join(f"{i}: {s}" for i, s in enumerate(sentences))
    return f"다음 검수 메모를 정리하세요.\n\n{lines}"


def interpret(sentences: list[str], knowledge: Knowledge, *, runner: Callable | None = None,
              catalog: dict | None = None) -> tuple[dict, int]:
    """(날것의 결과, 시도 횟수). 모두 실패하면 LLMFailure."""
    return complete_json(build_system_prompt(knowledge, catalog), build_user_prompt(sentences), RAW_SCHEMA, runner=runner)

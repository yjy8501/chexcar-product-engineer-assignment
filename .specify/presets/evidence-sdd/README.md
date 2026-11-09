# evidence-sdd

Spec Kit 기본 흐름(specify, plan, tasks, implement)에 **근거 규칙**을 덧붙이는 preset입니다.
AI가 추측을 사실처럼 쓰거나, 확인하지 않은 범위를 "없다"고 하거나, 검증 없이 "완료"라고 보고하는 것을 막는 것이 목적입니다.

REA(Reverse Engineer Anything)의 에이전트 운영 규칙(관찰 / 추론 / 미확인 구분, 범위 있는 부재 주장, 질문 체크리스트, 검증 기반 완료)을 Spec Kit 단계에 옮겼습니다.

## 규칙 4가지

| 규칙 | 한 줄 요약 | 적용 단계 |
|------|-----------|-----------|
| E1. 출처를 붙인다 | 요구사항마다 `명시` / `관찰` / `추정` / `미확인` 표시 | specify |
| E2. 범위 없이 "없다"고 하지 않는다 | 부재 주장에는 확인한 경로, 검색어를 함께 적음 | plan, converge |
| E3. 질문 목록으로 시작해서 끝낸다 | research.md를 질문 원장(답변됨 / 부분 답변 / 미해결)으로 작성 | plan |
| E4. 검증이 통과해야 완료다 | MUST 요구사항마다 검증 태스크 필수, 실행 결과로만 완료 처리 | tasks, implement |

`analyze`는 위 규칙 위반을 Findings로 보고합니다.

## 바뀌는 것

코어 파일을 통째로 바꾸지 않고 **뒤에 덧붙입니다**(`strategy: append`). Spec Kit을 업그레이드해도 코어 내용은 새 버전을 그대로 따라갑니다.

| 파일 | 덧붙는 내용 |
|------|-------------|
| constitution-template | 근거 원칙 E1 - E4 |
| spec-template | `요구사항 근거` 표 (ID / 출처 / 근거 / 검증 방법) |
| plan-template | `근거 점검` 체크리스트 |
| tasks-template | `요구사항-검증 추적표` (상태 / 실행 근거) |
| specify, plan, tasks, implement, analyze, converge 명령 | 단계별 근거 규칙 |

코어와 다르게 동작하는 부분:

- `tasks`: 코어는 테스트 태스크가 선택 사항이지만, 이 preset은 MUST 요구사항마다 검증 태스크를 만듭니다.
- `specify`: `[NEEDS CLARIFICATION]` 3개 제한은 그대로 두되, 기본값으로 채운 항목은 `추정`으로 남깁니다.
- `implement`: 태스크가 모두 `[X]`여도 추적표에 `미검증` / `실패`가 있으면 완료로 보고하지 않습니다.

## 설치

### 1. 준비: PyYAML이 있는 Python

템플릿을 덧붙이는(append) 기능은 Spec Kit 스크립트가 Python + PyYAML로 처리합니다. 없으면 새 기능을 만들 때 `Error: PyYAML is required to resolve preset template composition`으로 실패합니다.

```bash
uv venv ~/.local/share/speckit-py
uv pip install --python ~/.local/share/speckit-py/bin/python pyyaml
# 셸 시작 파일(~/.zshrc 또는 ~/.zprofile)에 추가
export SPECKIT_PYTHON_EXECUTABLE="$HOME/.local/share/speckit-py/bin/python"
```

### 2. 프로젝트에 적용

템플릿은 이 폴더에 두고, 쓰고 싶은 프로젝트에만 적용합니다. 대상은 `specify init`으로 초기화된 프로젝트(`.specify/`가 있는 폴더)여야 합니다.

```bash
~/IdeaProjects/speckit-evidence-preset/apply.sh ~/IdeaProjects/my-project            # 적용
~/IdeaProjects/speckit-evidence-preset/apply.sh --remove ~/IdeaProjects/my-project   # 제거
```

경로를 생략하면 현재 디렉토리에 적용합니다. 적용하거나 제거한 뒤에는 에이전트(Claude Code)를 재시작합니다.

스크립트는 `.specify/`가 없거나 PyYAML이 없으면 아무것도 바꾸지 않고 멈춥니다. `specify` 명령이 PATH에 없으면 `uvx`로 Spec Kit을 받아서 실행합니다.

### 3. 기존 constitution에 원칙 추가 (이미 constitution이 있는 프로젝트)

constitution-template 변경은 새로 만드는 constitution에만 반영됩니다. 기존 프로젝트는 다음처럼 요청합니다.

```text
/speckit-constitution evidence-sdd 프리셋의 근거 원칙 E1-E4를 추가해줘
```

## 확인

```bash
specify preset list                    # 설치 확인
specify preset resolve spec-template   # 코어 + evidence-sdd 합성 순서 확인
```

`specify` 명령이 PATH에 없으면 앞에 `uvx --from git+https://github.com/github/spec-kit.git`를 붙입니다.

제거 후 참고: 규칙은 모두 빠지고 skill 본문은 원래대로 돌아오지만, Spec Kit이 `.claude/skills/speckit-*/SKILL.md`를 다시 쓰면서 머리말 서식(따옴표, 제목 한 줄)이 바뀌고 빈 `.specify/presets/.registry` 파일이 남습니다. git diff에 이 변경이 보일 수 있습니다.

## 검증 기록

- 2026-10-14, Spec Kit main(1.2.0) CLI로 `payment-concurrency-lab` 복사본에 설치
  - 6개 skill 모두 코어 본문 유지 + 규칙 추가 확인
  - `create-new-feature.sh`, `setup-plan.sh` 실행 시 spec.md, plan.md 끝에 섹션 추가 확인
  - PyYAML 없는 Python으로는 `create-new-feature.sh` 실패 확인 (설치 1단계가 필요한 이유)
- 2026-10-14, `apply.sh` 테스트 (복사본 대상)
  - `.specify/` 없는 폴더, PyYAML 없는 Python: 변경 없이 중단 확인
  - 적용: 6개 skill에 규칙 추가 확인 / 제거: 규칙 잔여 없음, skill 본문 6개 원본과 동일 (머리말 서식만 다름)
- 확인하지 않은 것: 실제 `/speckit-*` 명령을 끝까지 실행했을 때 에이전트가 규칙을 지키는지

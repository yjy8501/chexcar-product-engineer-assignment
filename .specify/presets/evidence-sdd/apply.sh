#!/usr/bin/env bash
# evidence-sdd preset을 지정한 프로젝트에 적용하거나 제거한다.
#   apply.sh [프로젝트경로]           적용 (경로 생략 시 현재 디렉토리)
#   apply.sh --remove [프로젝트경로]  제거
set -euo pipefail

PRESET_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPECKIT_SOURCE="${SPECKIT_SOURCE:-git+https://github.com/github/spec-kit.git}"

action="add"
if [[ "${1:-}" == "--remove" ]]; then
    action="remove"
    shift
fi
target="$(cd "${1:-.}" && pwd)"

if [[ ! -d "$target/.specify" ]]; then
    echo "중단: $target 에 .specify/ 가 없습니다. 먼저 specify init 으로 초기화하세요." >&2
    exit 1
fi

run_specify() {
    if command -v specify >/dev/null 2>&1; then
        command specify "$@"
    else
        uvx --from "$SPECKIT_SOURCE" specify "$@"
    fi
}

cd "$target"

if [[ "$action" == "remove" ]]; then
    run_specify preset remove evidence-sdd
    echo "제거 완료: $target (에이전트를 재시작하세요)"
    exit 0
fi

py="${SPECKIT_PYTHON_EXECUTABLE:-python3}"
if ! "$py" -c 'import yaml' >/dev/null 2>&1; then
    echo "중단: $py 에 PyYAML이 없습니다. README의 '준비' 단계를 먼저 진행하세요." >&2
    exit 1
fi

run_specify preset add --dev "$PRESET_DIR"
echo "적용 완료: $target"
echo "- 에이전트(Claude Code)를 재시작하세요."
echo "- 기존 constitution이 있으면: /speckit-constitution evidence-sdd 프리셋의 근거 원칙 E1-E4를 추가해줘"

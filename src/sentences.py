"""메모를 문장으로 나눈다. 근거는 이 문장 번호(idx)로 가리킨다 (FR-004, FR-013)."""
import re

# 마침표, 물음표, 느낌표 뒤의 공백이나 줄바꿈에서 나눈다. 숫자의 소수점(2.5mm)은 나누지 않는다.
_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def split_sentences(memo: str) -> list[str]:
    return [s.strip() for s in _SPLIT.split(memo or "") if s and s.strip()]

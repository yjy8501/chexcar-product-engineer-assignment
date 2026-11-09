"""T005: 메모를 문장으로 나누기 (FR-004, FR-013)."""
from src.sentences import split_sentences


def test_splits_on_period_and_keeps_numbers():
    memo = "프싸 우측 스크래치 15cm, 도색 필요. 본넷 단차 약간 있음 탈부착 요망."
    assert split_sentences(memo) == [
        "프싸 우측 스크래치 15cm, 도색 필요.",
        "본넷 단차 약간 있음 탈부착 요망.",
    ]


def test_three_sentences():
    memo = "앞범퍼 도색. 프론트범퍼 좌측에도 스크래치 있어 같이 진행. 브레이크 패드 잔량 3mm 교체 권장."
    assert len(split_sentences(memo)) == 3


def test_decimal_numbers_do_not_split():
    assert split_sentences("트레드 2.5mm 남음.") == ["트레드 2.5mm 남음."]


def test_newlines_split_and_empty_dropped():
    assert split_sentences("도색 필요\n\n탈부착 요망") == ["도색 필요", "탈부착 요망"]


def test_empty_memo():
    assert split_sentences("") == []

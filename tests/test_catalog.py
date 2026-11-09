"""T004: 표준 작업 코드표 읽기 (FR-003)."""
from src.catalog import has_code, load_catalog


def test_catalog_has_35_codes():
    assert len(load_catalog()) == 35


def test_known_code_is_accepted():
    assert has_code("BP-FR-PT")
    assert has_code("TY-00-EX")


def test_unknown_code_is_rejected():
    assert not has_code("XX-00-ZZ")
    assert not has_code("")
    assert not has_code(None)


def test_catalog_rows_keep_note():
    cat = load_catalog()
    assert cat["TY-00-EX"]["note"] == "1짝 기준 공임 포함"
    assert cat["BR-00-EX"]["note"] == "전륜 또는 후륜 기준"
    assert cat["BP-FR-PT"]["name"] == "프론트범퍼 도색"

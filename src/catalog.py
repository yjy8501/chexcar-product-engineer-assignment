"""표준 작업 코드표 읽기. 결과에 나오는 모든 코드는 여기에 있어야 한다 (FR-003)."""
import csv
from functools import lru_cache
from pathlib import Path

from .config import WORK_CODES


@lru_cache(maxsize=None)
def _load(path: str) -> dict:
    with open(path, encoding="utf-8", newline="") as f:
        return {row["code"]: row for row in csv.DictReader(f)}


def load_catalog(path: Path | str = WORK_CODES) -> dict:
    return _load(str(path))


def has_code(code, catalog: dict | None = None) -> bool:
    if not code:
        return False
    return code in (catalog if catalog is not None else load_catalog())

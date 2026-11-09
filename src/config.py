"""경로와 모델 이름. 환경변수 MAPPER_MODEL 로 모델을 바꿀 수 있다."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
KNOWLEDGE = ROOT / "knowledge"
RESULTS = ROOT / "results"
ORDERS = ROOT / "orders"
WEB = ROOT / "web"

INSPECTIONS = DATA / "inspections.json"
WORK_CODES = DATA / "work_codes.csv"
ANSWER_KEY = DATA / "answer_key.json"

MODEL = os.environ.get("MAPPER_MODEL", "claude-sonnet-5-5")
MAX_ATTEMPTS = 2  # 첫 시도 + 재시도 1회 (FR-022)
LLM_TIMEOUT_SEC = 240

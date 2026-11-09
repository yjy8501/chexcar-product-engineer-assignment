"""결과 데이터 구조 (data-model.md, contracts/draft.schema.json)."""
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .catalog import has_code

Status = Literal["제안", "확인필요", "코드없음"]
Overall = Literal["정상", "작업없음", "판단불가"]
Role = Literal["반영", "제외", "애매", "연결없음"]


class Sentence(BaseModel):
    idx: int = Field(ge=0)
    text: str
    role: Role


class CodeQty(BaseModel):
    code: str
    qty: int | None = None


class Item(BaseModel):
    id: int
    status: Status
    code: str | None
    qty: int | None = Field(default=None, ge=1)
    evidence: list[int] = Field(min_length=1)  # 근거 문장 번호는 비어 있으면 안 된다
    issue: str | None = None
    recommended: CodeQty | None = None
    alternatives: list[CodeQty] = Field(default_factory=list)
    downgraded_by: str | None = None

    @model_validator(mode="after")
    def suggestion_needs_valid_code_and_qty(self):
        # 상태가 제안이면 code와 qty가 있어야 하고, 코드는 코드표에 있어야 한다
        if self.status == "제안":
            if self.code is None or self.qty is None:
                raise ValueError("제안에는 code와 qty가 필요하다")
            if not has_code(self.code):
                raise ValueError(f"코드표에 없는 코드: {self.code}")
        return self


class Excluded(BaseModel):
    evidence: list[int]
    reason: str


class Meta(BaseModel):
    model: str
    knowledge: str
    attempts: int = Field(ge=1)
    failure: str | None = None
    cost_usd: float | None = None  # 이 메모를 해석하는 데 든 비용(참고용)


class Draft(BaseModel):
    inspection_id: str
    memo: str
    sentences: list[Sentence]
    overall: Overall
    items: list[Item]
    excluded: list[Excluded]
    warnings: list[str]
    meta: Meta

    @model_validator(mode="after")
    def unfit_overall_has_no_suggestion(self):
        # 판단불가 결과에는 제안이 없어야 한다 (FR-008)
        if self.overall == "판단불가" and any(i.status == "제안" for i in self.items):
            raise ValueError("판단불가 결과에는 제안이 있을 수 없다")
        return self


class OrderLine(BaseModel):
    code: str
    qty: int = Field(ge=1)
    source: Literal["제안승인", "직접선택"]


class Skipped(BaseModel):
    item_id: int
    reason: str = "하지 않음"


class ConfirmedOrder(BaseModel):
    inspection_id: str
    knowledge: str
    lines: list[OrderLine]
    skipped: list[Skipped]
    manual: list[int] = Field(default_factory=list)  # 코드없음이라 수동 처리가 필요한 항목 id
    approved_at: str

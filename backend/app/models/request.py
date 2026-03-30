from pydantic import BaseModel, Field, field_validator
from typing import Optional


class FindInvestorsRequest(BaseModel):
    company_url: Optional[str] = None
    industries: list[str] = Field(default_factory=list)
    icp_segments: list[str] = Field(default_factory=list)
    arr: Optional[float] = None
    arr_growth: Optional[float] = None
    raise_amount: Optional[float] = None   # desired raise in $M, e.g. 10.0 = $10M
    keywords: list[str] = Field(default_factory=list)
    round_stage: Optional[str] = None
    further_context: Optional[str] = None
    competitors: list[str] = Field(default_factory=list)

    @field_validator("arr", "arr_growth", "raise_amount", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v

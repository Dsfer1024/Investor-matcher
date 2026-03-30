from pydantic import BaseModel, Field, field_validator
from typing import Optional


class FindInvestorsRequest(BaseModel):
    company_url: Optional[str] = None
    broad_industry: Optional[str] = None
    target_customer: Optional[str] = None
    arr: Optional[float] = None
    arr_growth: Optional[float] = None
    business_types: list[str] = Field(default_factory=list)
    round_stage: Optional[str] = None
    further_context: Optional[str] = None
    competitors: list[str] = Field(default_factory=list)

    @field_validator("arr", "arr_growth", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v

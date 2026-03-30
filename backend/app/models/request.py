from pydantic import BaseModel, Field, field_validator
from typing import Optional


class FindInvestorsRequest(BaseModel):
    company_url: Optional[str] = None
    broad_industry: Optional[str] = None
    icp_segments: list[str] = Field(default_factory=list)   # SMB / Mid-market / Enterprise
    arr: Optional[float] = None
    arr_growth: Optional[float] = None
    keywords: list[str] = Field(default_factory=list)       # business type keywords
    round_stage: Optional[str] = None
    further_context: Optional[str] = None
    competitors: list[str] = Field(default_factory=list)    # competitor URLs

    @field_validator("arr", "arr_growth", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v

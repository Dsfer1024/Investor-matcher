from pydantic import BaseModel, Field
from typing import Optional


class FindInvestorsRequest(BaseModel):
    company_url: Optional[str] = None
    broad_industry: Optional[str] = None
    target_customer: Optional[str] = None
    arr: Optional[float] = None          # in $m
    arr_growth: Optional[float] = None   # percentage YoY
    business_types: list[str] = Field(default_factory=list)  # multi-select
    round_stage: Optional[str] = None
    further_context: Optional[str] = None
    competitors: list[str] = Field(default_factory=list)
    # File is handled as multipart in the router, parsed separately

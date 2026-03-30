from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class DataSource(str, Enum):
    openvc = "openvc"
    github = "github"
    user_upload = "user_upload"
    merged = "merged"
    claude = "claude"


class InvestorRecord(BaseModel):
    """Internal record — superset of all output columns + scoring fields."""
    id: str
    fund_name: str
    target_partner: Optional[str] = None
    partner_title: Optional[str] = None
    fund_size_raw: Optional[str] = None
    fund_size_usd: Optional[int] = None
    check_size_min_usd: Optional[int] = None
    check_size_max_usd: Optional[int] = None
    check_size_raw: Optional[str] = None
    lead_or_follow: Optional[str] = None
    areas_of_focus: list[str] = Field(default_factory=list)
    portfolio_companies: list[str] = Field(default_factory=list)
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    geography: Optional[str] = None
    stages_invested: list[str] = Field(default_factory=list)
    source: DataSource = DataSource.claude
    raw_data: dict = Field(default_factory=dict)

    # Scoring fields — populated by claude_service
    fit_score: Optional[int] = None
    prestige_score: Optional[int] = None
    tier: Optional[int] = None                  # 1, 2, or 3
    relevant_portfolio: list[str] = Field(default_factory=list)
    why_fit: list[str] = Field(default_factory=list)
    evidence_links: list[str] = Field(default_factory=list)
    has_competitor_conflict: bool = False
    conflicting_competitors: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    score_reasoning: Optional[str] = None

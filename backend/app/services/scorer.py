"""Orchestrates the full scoring pipeline: prefilter → Claude → sort."""
import logging
import re
from typing import Callable, Awaitable

from app.models.investor import InvestorRecord
from app.models.request import FindInvestorsRequest
from app.config import get_settings
from app.services import claude_service

logger = logging.getLogger(__name__)
settings = get_settings()

# Stage → check size range in USD for heuristic matching
STAGE_CHECK_RANGES: dict[str, tuple[int, int]] = {
    "pre-seed": (50_000, 500_000),
    "seed": (250_000, 3_000_000),
    "series a": (2_000_000, 15_000_000),
    "series b": (10_000_000, 50_000_000),
    "series c+": (25_000_000, 200_000_000),
}

BUSINESS_TYPE_KEYWORDS: dict[str, list[str]] = {
    "b2b saas": ["saas", "b2b", "enterprise", "software"],
    "vertical saas": ["vertical", "saas", "industry software"],
    "vertical ai": ["ai", "artificial intelligence", "vertical", "machine learning"],
    "vertical fintech": ["fintech", "financial", "vertical", "payments"],
    "fintech": ["fintech", "financial technology", "payments", "banking", "insurance"],
    "healthcare it": ["health", "healthcare", "medtech", "digital health", "health tech"],
}


def _heuristic_score(inv: InvestorRecord, request: FindInvestorsRequest) -> int:
    score = 0
    focus_text = " ".join(inv.areas_of_focus + inv.stages_invested).lower()
    stages_text = " ".join(inv.stages_invested).lower()

    # Stage match
    stage_key = (request.round_stage or "").lower()
    stage_range = STAGE_CHECK_RANGES.get(stage_key)
    if stage_range and inv.check_size_min_usd and inv.check_size_max_usd:
        # Check if ranges overlap
        if inv.check_size_min_usd <= stage_range[1] and inv.check_size_max_usd >= stage_range[0]:
            score += 30
    elif stage_key and any(stage_key.split()[0] in s for s in inv.stages_invested):
        score += 20

    # Business type match
    for btype in request.business_types:
        keywords = BUSINESS_TYPE_KEYWORDS.get(btype.lower(), [btype.lower()])
        if any(kw in focus_text for kw in keywords):
            score += 25
            break

    # Industry / tags overlap
    industry = (request.broad_industry or "").lower()
    if industry:
        industry_words = re.findall(r"\w+", industry)
        matches = sum(1 for w in industry_words if len(w) > 3 and w in focus_text)
        score += min(matches * 5, 20)

    # Target customer overlap
    customer = (request.target_customer or "").lower()
    if customer:
        customer_words = re.findall(r"\w+", customer)
        matches = sum(1 for w in customer_words if len(w) > 4 and w in focus_text)
        score += min(matches * 3, 15)

    return score


def heuristic_prefilter(
    investors: list[InvestorRecord],
    request: FindInvestorsRequest,
    top_n: int | None = None,
) -> list[InvestorRecord]:
    """Fast keyword-based filter — narrows candidates before Claude scoring."""
    top_n = top_n or settings.max_investors_to_score
    scored = [(inv, _heuristic_score(inv, request)) for inv in investors]
    scored.sort(key=lambda x: -x[1])
    return [inv for inv, _ in scored[:top_n]]


async def run_scoring_pipeline(
    investors: list[InvestorRecord],
    request: FindInvestorsRequest,
    progress_callback: Callable[[str], Awaitable[None]] | None = None,
) -> list[InvestorRecord]:
    """Full pipeline: prefilter → Claude batch scoring."""
    candidates = heuristic_prefilter(investors, request)
    logger.info(f"Scoring {len(candidates)} candidates with Claude")
    scored = await claude_service.score_all_investors(
        candidates, request, progress_callback
    )
    return scored

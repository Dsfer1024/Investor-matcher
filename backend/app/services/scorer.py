"""Single-call AI pipeline: one Claude call generates, scores, and tiers investors."""
import logging
from typing import Callable, Awaitable

from app.models.investor import InvestorRecord
from app.models.request import FindInvestorsRequest
from app.config import get_settings
from app.services import claude_service

logger = logging.getLogger(__name__)
settings = get_settings()


def sort_by_tier_and_score(investors: list[InvestorRecord]) -> list[InvestorRecord]:
    return sorted(
        investors,
        key=lambda x: (x.tier or 3, -(x.fit_score or 0), -(x.prestige_score or 0)),
    )


async def run_dynamic_pipeline(
    request: FindInvestorsRequest,
    progress_callback: Callable[[str], Awaitable[None]] | None = None,
) -> tuple[list[InvestorRecord], str]:
    """
    Single Claude call: generate + score + tier in one shot.
    Returns (investors, quick_thesis).
    """
    async def _progress(msg: str) -> None:
        if progress_callback:
            await progress_callback(msg)

    await _progress("generate")
    investors, quick_thesis = await claude_service.generate_full_investor_list(
        request, conflict_map={}, target=settings.longlist_target
    )
    logger.info(f"Pipeline returned {len(investors)} investors")

    return sort_by_tier_and_score(investors)[:100], quick_thesis

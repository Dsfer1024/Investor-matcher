"""Dynamic AI pipeline: conflict research → full research → gap fill → sort."""
import logging
from typing import Callable, Awaitable

from app.models.investor import InvestorRecord
from app.models.request import FindInvestorsRequest
from app.config import get_settings
from app.services import claude_service
from app.services.deduplicator import deduplicate
from app.cache.investor_cache import get_public_investors

logger = logging.getLogger(__name__)
settings = get_settings()


def sort_by_tier_and_score(investors: list[InvestorRecord]) -> list[InvestorRecord]:
    """Sort by tier ascending, then fit_score desc, then prestige_score desc."""
    return sorted(
        investors,
        key=lambda x: (x.tier or 3, -(x.fit_score or 0), -(x.prestige_score or 0)),
    )


async def run_dynamic_pipeline(
    request: FindInvestorsRequest,
    progress_callback: Callable[[str], Awaitable[None]] | None = None,
) -> list[InvestorRecord]:
    """Full dynamic pipeline: conflict research → comprehensive AI list → gap fill → sort."""

    async def _progress(msg: str) -> None:
        if progress_callback:
            await progress_callback(msg)

    # Phase 1: Competitor conflict research
    await _progress("conflicts")
    conflict_map = await claude_service.research_competitor_conflicts(request.competitors)
    logger.info(f"Conflict map built for {len(conflict_map)} competitors")

    # Phase 2: Single comprehensive research call
    await _progress("generate")
    investors = await claude_service.generate_full_investor_list(
        request, conflict_map, target=settings.longlist_target
    )
    logger.info(f"Full research returned {len(investors)} investors")

    # Merge Excel supplement (additive only)
    excel = get_public_investors()
    if excel:
        investors = deduplicate(investors + excel)
        logger.info(f"After Excel merge + dedup: {len(investors)} unique investors")

    # Phase 3: Gap fill if below minimum
    if len(investors) < settings.min_results_guarantee:
        await _progress("gap")
        gap = settings.min_results_guarantee - len(investors)
        exclude = {inv.fund_name.lower() for inv in investors}
        extra = await claude_service.generate_full_investor_list(
            request, conflict_map, target=gap + 20, exclude=exclude
        )
        logger.info(f"Gap fill: generated {len(extra)} additional investors")
        if extra:
            investors.extend(extra)
            logger.info(f"After gap fill: {len(investors)} total investors")

    # Phase 4: Sort and return top 100
    return sort_by_tier_and_score(investors)[:100]

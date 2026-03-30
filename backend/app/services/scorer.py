"""Dynamic AI pipeline: conflict research → full research → gap fill → sort."""
import logging
from typing import Callable, Awaitable

from app.models.investor import InvestorRecord
from app.models.request import FindInvestorsRequest
from app.config import get_settings
from app.services import claude_service
from app.services.deduplicator import deduplicate

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
) -> tuple[list[InvestorRecord], str]:
    """
    Full dynamic pipeline:
      1. Conflict research
      2. Comprehensive AI generation (40 investors per call, within token limits)
      3. Gap fill with additional calls until min_results_guarantee is met
      4. Sort and return top 100
    Returns (investors, quick_thesis).
    """

    async def _progress(msg: str) -> None:
        if progress_callback:
            await progress_callback(msg)

    # Phase 1: Competitor conflict research
    await _progress("conflicts")
    conflict_map = await claude_service.research_competitor_conflicts(request.competitors)
    logger.info(f"Conflict map built for {len(conflict_map)} competitors")

    # Phase 2: First comprehensive generation call
    await _progress("generate")
    investors, quick_thesis = await claude_service.generate_full_investor_list(
        request, conflict_map, target=settings.longlist_target
    )
    logger.info(f"First generation call returned {len(investors)} investors")

    # Phase 3: Gap fill with additional calls until we hit min_results_guarantee
    max_gap_rounds = 5  # prevent infinite loop
    round_num = 0
    while len(investors) < settings.min_results_guarantee and round_num < max_gap_rounds:
        await _progress("gap")
        round_num += 1
        gap = settings.min_results_guarantee - len(investors)
        call_target = min(gap + 10, settings.max_per_call)
        exclude = {inv.fund_name.lower() for inv in investors}
        logger.info(f"Gap fill round {round_num}: need {gap} more, requesting {call_target}")
        extra, _ = await claude_service.generate_full_investor_list(
            request, conflict_map, target=call_target, exclude=exclude
        )
        if not extra:
            logger.warning("Gap fill returned 0 investors, stopping")
            break
        investors = deduplicate(investors + extra)
        logger.info(f"After gap fill round {round_num}: {len(investors)} total investors")

    # Phase 4: Sort and return top 100
    return sort_by_tier_and_score(investors)[:100], quick_thesis

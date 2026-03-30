"""Dynamic AI pipeline: conflict research → longlist → enrich → gap fill → sort."""
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
    """Full dynamic pipeline delegating all research to Claude."""

    async def _progress(msg: str) -> None:
        if progress_callback:
            await progress_callback(msg)

    # Phase 1: Competitor conflict research
    await _progress("conflicts")
    conflict_map = await claude_service.research_competitor_conflicts(request.competitors)
    logger.info(f"Conflict map built for {len(conflict_map)} competitors")

    # Phase 2: Generate investor longlist
    await _progress("generate")
    longlist = await claude_service.generate_investor_longlist(
        request, conflict_map, target=settings.longlist_target
    )
    logger.info(f"Longlist contains {len(longlist)} investors from Claude")

    # Merge Excel supplement (additive only)
    excel = get_public_investors()
    if excel:
        longlist = deduplicate(longlist + excel)
        logger.info(f"After Excel merge + dedup: {len(longlist)} unique investors")

    # Phase 3: Enrich + score in concurrent batches
    await _progress("enrich")
    scored = await claude_service.enrich_and_score_all(
        longlist, request, conflict_map, progress_callback
    )
    logger.info(f"Enriched {len(scored)} investors")

    # Phase 4: Gap fill if below minimum
    if len(scored) < settings.min_results_guarantee:
        await _progress("gap")
        gap = settings.min_results_guarantee - len(scored)
        exclude = {inv.fund_name.lower() for inv in scored}
        extra = await claude_service.generate_investor_longlist(
            request, conflict_map, target=gap + 20, exclude=exclude
        )
        logger.info(f"Gap fill: generated {len(extra)} additional investors")
        if extra:
            extra_scored = await claude_service.enrich_and_score_all(
                extra, request, conflict_map
            )
            scored.extend(extra_scored)
            logger.info(f"After gap fill: {len(scored)} total investors")

    # Phase 5: Sort and return top 100
    return sort_by_tier_and_score(scored)[:100]

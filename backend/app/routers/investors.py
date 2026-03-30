"""POST /api/find-investors — SSE streaming endpoint."""
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Form
from fastapi.responses import StreamingResponse

from app.models.request import FindInvestorsRequest
from app.models.investor import InvestorRecord
from app.services import claude_service
from app.services.scorer import sort_by_tier_and_score
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _serialize(inv: InvestorRecord, rank: int) -> dict:
    return {
        "id": inv.id,
        "rank": rank,
        "tier": inv.tier or 3,
        "prestigeScore": inv.prestige_score or 0,
        "fitScore": inv.fit_score or 0,
        "fundName": inv.fund_name,
        "firmUrl": inv.website,
        "recommendedPartner": inv.target_partner,
        "partnerTitle": inv.partner_title,
        "partnerLinkedIn": inv.linkedin_url,
        "geoFocus": inv.geography,
        "typicalLeadCheckUsd": inv.check_size_raw,
        "leadsRoundFrequently": inv.leads_round_frequently,
        "whyFit": inv.why_fit,
        "relevantPastInvestments": inv.relevant_past_investments,
        "evidenceLinks": inv.evidence_links,
        "hasCompetitorConflict": inv.has_competitor_conflict,
        "conflictingCompetitors": inv.conflicting_competitors,
        "notes": inv.notes,
        "source": inv.source,
    }


@router.post("/find-investors")
async def find_investors(data: str = Form(...)):
    request = FindInvestorsRequest.model_validate_json(data)

    MIN_RESULTS = 40

    async def event_stream() -> AsyncGenerator[str, None]:
        yield _sse({"type": "progress", "step": {"id": "generate", "label": "Generating investor list with AI...", "status": "active"}})

        all_investors: list[InvestorRecord] = []
        quick_thesis = ""
        found_count = 0

        async def _run_stream(target: int, exclude: set[str] | None = None, is_gap: bool = False) -> None:
            nonlocal found_count, quick_thesis
            async for event_type, payload in claude_service.stream_investors(
                request, target=target, exclude=exclude
            ):
                if event_type == "thesis":
                    if not quick_thesis:
                        quick_thesis = payload
                elif event_type == "investor":
                    all_investors.append(payload)
                    found_count += 1
                    label = f"Found {found_count} investors..." if not is_gap else f"Gap fill — {found_count} investors found..."
                    yield _sse({"type": "progress", "step": {"id": "generate", "label": label, "status": "active"}})
                elif event_type == "error":
                    yield _sse({"type": "error", "message": payload})

        # Phase 1: first call
        async for sse in _run_stream(settings.longlist_target):
            yield sse

        # Phase 2: gap fill — up to 2 more rounds to reach MIN_RESULTS
        gap_rounds = 0
        while len(all_investors) < MIN_RESULTS and gap_rounds < 2:
            gap_rounds += 1
            needed = MIN_RESULTS - len(all_investors) + 5  # +5 buffer for dupes
            exclude_set = {inv.fund_name.lower() for inv in all_investors}
            logger.info(f"Gap fill round {gap_rounds}: have {len(all_investors)}, need {needed} more")
            async for sse in _run_stream(needed, exclude=exclude_set, is_gap=True):
                yield sse

        # Sort and emit final result
        yield _sse({"type": "progress", "step": {"id": "generate", "label": "Ranking results...", "status": "active"}})
        sorted_investors = sort_by_tier_and_score(all_investors)[:100]
        output = [_serialize(inv, rank + 1) for rank, inv in enumerate(sorted_investors)]
        yield _sse({"type": "progress", "step": {"id": "generate", "label": f"Done — {len(output)} investors ranked", "status": "complete"}})
        yield _sse({"type": "result", "investors": output, "total": len(output), "quickThesis": quick_thesis})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

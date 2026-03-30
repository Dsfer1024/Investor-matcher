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

    async def event_stream() -> AsyncGenerator[str, None]:
        # Signal start
        yield _sse({"type": "progress", "step": {"id": "generate", "label": "Generating investor list with AI...", "status": "active"}})

        all_investors: list[InvestorRecord] = []
        quick_thesis = ""
        found_count = 0

        async for event_type, payload in claude_service.stream_investors(
            request, target=settings.longlist_target
        ):
            if event_type == "thesis":
                quick_thesis = payload
                yield _sse({"type": "thesis", "thesis": payload})

            elif event_type == "investor":
                all_investors.append(payload)
                found_count += 1
                # Update loading label with live count
                yield _sse({
                    "type": "progress",
                    "step": {
                        "id": "generate",
                        "label": f"Found {found_count} investors so far...",
                        "status": "active",
                    },
                })

            elif event_type == "error":
                yield _sse({"type": "error", "message": payload})
                return

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

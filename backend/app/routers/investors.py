"""POST /api/find-investors — SSE streaming endpoint."""
import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Form
from fastapi.responses import StreamingResponse

from app.models.request import FindInvestorsRequest
from app.models.investor import InvestorRecord
from app.services import scorer

logger = logging.getLogger(__name__)
router = APIRouter()


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _progress(step_id: str, label: str, status: str) -> str:
    return _sse({"type": "progress", "step": {"id": step_id, "label": label, "status": status}})


STEP_LABELS: dict[str, str] = {
    "generate": "Generating & scoring investor list with AI...",
    "rank": "Ranking & tiering results...",
}


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
async def find_investors(
    data: str = Form(...),
):
    request = FindInvestorsRequest.model_validate_json(data)

    async def event_stream() -> AsyncGenerator[str, None]:
        for step_id, label in STEP_LABELS.items():
            yield _progress(step_id, label, "pending")

        progress_queue: asyncio.Queue[str] = asyncio.Queue()

        async def on_progress(msg: str) -> None:
            await progress_queue.put(msg)

        PHASE_STEP = {
            "generate": "generate",
            "rank": "rank",
        }

        yield _progress("generate", STEP_LABELS["generate"], "active")
        last_step = "generate"

        pipeline_task = asyncio.create_task(
            scorer.run_dynamic_pipeline(request, on_progress)
        )

        while not pipeline_task.done():
            try:
                msg = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                if msg in PHASE_STEP:
                    new_step = PHASE_STEP[msg]
                    if new_step != last_step:
                        yield _progress(last_step, STEP_LABELS[last_step], "complete")
                        yield _progress(new_step, STEP_LABELS[new_step], "active")
                        last_step = new_step
                else:
                    yield _sse({"type": "info", "message": msg})
            except asyncio.TimeoutError:
                continue

        while not progress_queue.empty():
            msg = progress_queue.get_nowait()
            if msg in PHASE_STEP:
                new_step = PHASE_STEP[msg]
                if new_step != last_step:
                    yield _progress(last_step, STEP_LABELS[last_step], "complete")
                    yield _progress(new_step, STEP_LABELS[new_step], "active")
                    last_step = new_step

        exc = pipeline_task.exception()
        if exc:
            logger.error(f"Pipeline failed: {exc}")
            yield _progress(last_step, STEP_LABELS[last_step], "error")
            yield _sse({"type": "error", "message": str(exc)})
            return

        result_investors, quick_thesis = pipeline_task.result()

        yield _progress(last_step, STEP_LABELS[last_step], "complete")
        yield _progress("rank", STEP_LABELS["rank"], "active")

        output = [_serialize(inv, rank + 1) for rank, inv in enumerate(result_investors)]

        yield _progress("rank", f"Found {len(output)} investors", "complete")
        yield _sse({"type": "result", "investors": output, "total": len(output), "quickThesis": quick_thesis})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

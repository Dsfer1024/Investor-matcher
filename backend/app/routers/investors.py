"""POST /api/find-investors — SSE streaming endpoint."""
import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.models.request import FindInvestorsRequest
from app.models.investor import InvestorRecord
from app.services import scorer, spreadsheet_parser

logger = logging.getLogger(__name__)
router = APIRouter()


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _progress(step_id: str, label: str, status: str) -> str:
    return _sse({"type": "progress", "step": {"id": step_id, "label": label, "status": status}})


STEP_LABELS: dict[str, str] = {
    "conflicts": "Researching competitor conflicts...",
    "generate": "Generating investor longlist with AI...",
    "enrich": "Enriching & scoring investor profiles...",
    "gap": "Checking for gaps (ensuring 80+ results)...",
    "rank": "Ranking & tiering results...",
}


def _serialize(inv: InvestorRecord, rank: int) -> dict:
    check_size = inv.check_size_raw
    if not check_size and inv.check_size_min_usd and inv.check_size_max_usd:
        def fmt(n: int) -> str:
            if n >= 1_000_000:
                return f"${n // 1_000_000}M"
            return f"${n // 1_000}K"
        check_size = f"{fmt(inv.check_size_min_usd)}–{fmt(inv.check_size_max_usd)}"

    fund_size = inv.fund_size_raw
    if not fund_size and inv.fund_size_usd:
        fund_size = f"${inv.fund_size_usd // 1_000_000}M"

    return {
        "id": inv.id,
        "rank": rank,
        "fitScore": inv.fit_score or 0,
        "prestigeScore": inv.prestige_score or 0,
        "tier": inv.tier or 3,
        "fundName": inv.fund_name,
        "targetPartner": inv.target_partner,
        "partnerTitle": inv.partner_title,
        "fundSize": fund_size,
        "checkSize": check_size,
        "leadOrFollow": inv.lead_or_follow,
        "areasOfFocus": inv.areas_of_focus,
        "relevantPortfolioCompanies": inv.relevant_portfolio,
        "whyFit": inv.why_fit,
        "evidenceLinks": inv.evidence_links,
        "hasCompetitorConflict": inv.has_competitor_conflict,
        "conflictingCompetitors": inv.conflicting_competitors,
        "website": inv.website,
        "linkedinUrl": inv.linkedin_url,
        "geography": inv.geography,
        "notes": inv.notes,
        "source": inv.source,
    }


@router.post("/find-investors")
async def find_investors(
    data: str = Form(...),
    file: UploadFile | None = File(None),
):
    request = FindInvestorsRequest.model_validate_json(data)

    # Parse uploaded spreadsheet before streaming (needs to be read before async gen)
    upload_investors: list[InvestorRecord] = []
    if file and file.filename:
        try:
            content = await file.read()
            upload_investors = spreadsheet_parser.parse_spreadsheet(content, file.filename)
            logger.info(f"Parsed {len(upload_investors)} investors from uploaded spreadsheet")
        except Exception as e:
            logger.error(f"Spreadsheet parse error: {e}")

    # Merge upload investors into request context via a side-channel
    # (scorer pipeline handles public Excel; upload_investors are injected separately)
    async def event_stream() -> AsyncGenerator[str, None]:
        # Emit all step IDs as pending initially
        for step_id, label in STEP_LABELS.items():
            yield _progress(step_id, label, "pending")

        # Queue for progress messages from the pipeline
        progress_queue: asyncio.Queue[str] = asyncio.Queue()
        current_step = {"id": "conflicts"}

        async def on_progress(msg: str) -> None:
            await progress_queue.put(msg)

        # Map phase keywords → step IDs
        PHASE_STEP = {
            "conflicts": "conflicts",
            "generate": "generate",
            "enrich": "enrich",
            "gap": "gap",
            "rank": "rank",
        }

        # Mark conflicts as active
        yield _progress("conflicts", STEP_LABELS["conflicts"], "active")
        current_step["id"] = "conflicts"

        # Run the pipeline as a background task so we can interleave SSE events
        pipeline_task = asyncio.create_task(
            scorer.run_dynamic_pipeline(request, on_progress)
        )

        last_step = "conflicts"
        result_investors: list[InvestorRecord] = []

        while not pipeline_task.done():
            try:
                msg = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                # msg is either a phase keyword or an enrichment progress string
                if msg in PHASE_STEP:
                    new_step = PHASE_STEP[msg]
                    if new_step != last_step:
                        yield _progress(last_step, STEP_LABELS[last_step], "complete")
                        yield _progress(new_step, STEP_LABELS[new_step], "active")
                        last_step = new_step
                else:
                    # Enrichment progress update — send as SSE info
                    yield _sse({"type": "info", "message": msg})
            except asyncio.TimeoutError:
                continue

        # Drain remaining queue items
        while not progress_queue.empty():
            msg = progress_queue.get_nowait()
            if msg in PHASE_STEP:
                new_step = PHASE_STEP[msg]
                if new_step != last_step:
                    yield _progress(last_step, STEP_LABELS[last_step], "complete")
                    yield _progress(new_step, STEP_LABELS[new_step], "active")
                    last_step = new_step

        # Handle pipeline result or exception
        exc = pipeline_task.exception()
        if exc:
            logger.error(f"Pipeline failed: {exc}")
            yield _progress(last_step, STEP_LABELS[last_step], "error")
            yield _sse({"type": "error", "message": str(exc)})
            return

        result_investors = pipeline_task.result()

        # If there were uploaded investors, merge + re-sort
        if upload_investors:
            from app.services.deduplicator import deduplicate as _dedup
            combined = _dedup(result_investors + upload_investors)
            # Re-apply tier sort (uploaded investors won't have scores, put at end)
            result_investors = scorer.sort_by_tier_and_score(combined)[:100]

        # Mark remaining steps complete
        yield _progress(last_step, STEP_LABELS[last_step], "complete")
        yield _progress("rank", STEP_LABELS["rank"], "active")

        output = [_serialize(inv, rank + 1) for rank, inv in enumerate(result_investors)]

        yield _progress("rank", f"Found {len(output)} investors", "complete")
        yield _sse({"type": "result", "investors": output, "total": len(output)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

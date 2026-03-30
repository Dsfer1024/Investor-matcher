"""POST /api/find-investors — SSE streaming endpoint."""
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.cache.investor_cache import get_public_investors
from app.models.request import FindInvestorsRequest
from app.models.investor import InvestorRecord
from app.services import deduplicator, scorer, spreadsheet_parser

logger = logging.getLogger(__name__)
router = APIRouter()


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _progress(step_id: str, label: str, status: str) -> str:
    return _sse({"type": "progress", "step": {"id": step_id, "label": label, "status": status}})


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
        "fundName": inv.fund_name,
        "targetPartner": inv.target_partner,
        "fundSize": fund_size,
        "checkSize": check_size,
        "leadOrFollow": inv.lead_or_follow,
        "areasOfFocus": inv.areas_of_focus,
        "relevantPortfolioCompanies": inv.relevant_portfolio,
        "hasCompetitorConflict": inv.has_competitor_conflict,
        "conflictingCompetitors": inv.conflicting_competitors,
        "website": inv.website,
        "linkedinUrl": inv.linkedin_url,
        "geography": inv.geography,
        "source": inv.source,
    }


@router.post("/find-investors")
async def find_investors(
    data: str = Form(...),
    file: UploadFile | None = File(None),
):
    request = FindInvestorsRequest.model_validate_json(data)

    async def event_stream() -> AsyncGenerator[str, None]:
        # Step 1: Load public investors
        yield _progress("load", "Loading investor database", "active")
        public_investors = get_public_investors()
        yield _progress("load", "Loading investor database", "complete")

        # Step 2: Parse uploaded spreadsheet
        upload_investors: list[InvestorRecord] = []
        if file and file.filename:
            yield _progress("upload", "Processing your spreadsheet", "active")
            try:
                content = await file.read()
                upload_investors = spreadsheet_parser.parse_spreadsheet(
                    content, file.filename
                )
            except Exception as e:
                logger.error(f"Spreadsheet parse error: {e}")
            yield _progress("upload", "Processing your spreadsheet", "complete")
        else:
            yield _progress("upload", "No spreadsheet provided — skipping", "complete")

        # Step 3: Merge + deduplicate
        yield _progress("merge", "Merging & deduplicating records", "active")
        all_investors = deduplicator.deduplicate(public_investors + upload_investors)
        logger.info(f"Total unique investors after dedup: {len(all_investors)}")
        yield _progress("merge", f"Merged {len(all_investors)} unique investors", "complete")

        # Step 4: Score with Claude
        yield _progress("score", "Scoring investors with AI (this takes ~30s)", "active")
        scored_investors: list[InvestorRecord] = []
        last_progress_msg = ""

        async def on_progress(msg: str) -> None:
            nonlocal last_progress_msg
            last_progress_msg = msg
            # We can't yield from a callback, so just log
            logger.info(f"Scoring progress: {msg}")

        try:
            scored_investors = await scorer.run_scoring_pipeline(
                all_investors, request, on_progress
            )
        except Exception as e:
            logger.error(f"Scoring pipeline failed: {e}")
            yield _sse({"type": "error", "message": f"Scoring failed: {str(e)}"})
            return

        yield _progress("score", "Scoring investors with AI", "complete")

        # Step 5: Rank and return
        yield _progress("rank", "Ranking results", "active")
        top_100 = sorted(scored_investors, key=lambda x: -(x.fit_score or 0))[:100]
        yield _progress("rank", f"Found {len(top_100)} investors", "complete")

        output = [_serialize(inv, rank + 1) for rank, inv in enumerate(top_100)]
        yield _sse({"type": "result", "investors": output, "total": len(output)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

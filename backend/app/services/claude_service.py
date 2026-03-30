"""Claude API scoring service — batch-scores investors against company profile."""
import asyncio
import json
import logging
import re
from typing import Callable, Awaitable

import anthropic

from app.config import get_settings
from app.models.investor import InvestorRecord
from app.models.request import FindInvestorsRequest
from app.utils import rate_limiter

logger = logging.getLogger(__name__)
settings = get_settings()

_semaphore = asyncio.Semaphore(settings.max_concurrent_batches)


def _get_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


def _build_company_profile(request: FindInvestorsRequest) -> str:
    lines = []
    if request.company_url:
        lines.append(f"Company URL: {request.company_url}")
    if request.broad_industry:
        lines.append(f"Industry: {request.broad_industry}")
    if request.target_customer:
        lines.append(f"Target Customer / ICP: {request.target_customer}")
    if request.arr is not None:
        lines.append(f"ARR: ${request.arr}M")
    if request.arr_growth is not None:
        lines.append(f"ARR Growth YoY: {request.arr_growth}%")
    if request.business_types:
        lines.append(f"Business Type(s): {', '.join(request.business_types)}")
    if request.round_stage:
        lines.append(f"Round Stage: {request.round_stage}")
    if request.competitors:
        lines.append(f"Competitors: {', '.join(request.competitors)}")
    if request.further_context:
        lines.append(f"Additional Context: {request.further_context}")
    return "\n".join(lines)


def _build_investor_list(investors: list[InvestorRecord]) -> str:
    items = []
    for inv in investors:
        focus = ", ".join(inv.areas_of_focus[:10]) if inv.areas_of_focus else "Unknown"
        stages = ", ".join(inv.stages_invested[:5]) if inv.stages_invested else "Unknown"
        portfolio = ", ".join(inv.portfolio_companies[:15]) if inv.portfolio_companies else "None listed"
        check = inv.check_size_raw or (
            f"${inv.check_size_min_usd // 1000}K–${inv.check_size_max_usd // 1000}K"
            if inv.check_size_min_usd and inv.check_size_max_usd
            else "Unknown"
        )
        fund_size = inv.fund_size_raw or (
            f"${inv.fund_size_usd // 1_000_000}M" if inv.fund_size_usd else "Unknown"
        )

        # Extra context from Excel fields
        rd = inv.raw_data or {}
        extra_lines = []
        if rd.get("best_fit_profile"):
            extra_lines.append(f"  Best-fit Founder: {rd['best_fit_profile']}")
        if rd.get("arr_entry_band"):
            extra_lines.append(f"  ARR Entry Band: {rd['arr_entry_band']}")
        if rd.get("followon_capacity"):
            extra_lines.append(f"  Follow-on Capacity: {rd['followon_capacity']}")
        if rd.get("category"):
            extra_lines.append(f"  Category: {rd['category']}")

        block = (
            f"ID: {inv.id}\n"
            f"  Fund: {inv.fund_name}\n"
            f"  Focus: {focus}\n"
            f"  Stages: {stages}\n"
            f"  Check Size: {check}\n"
            f"  Fund Size: {fund_size}\n"
            f"  Portfolio: {portfolio}"
        )
        if extra_lines:
            block += "\n" + "\n".join(extra_lines)
        items.append(block)
    return "\n\n".join(items)


def _extract_json(text: str) -> list[dict]:
    """Extract JSON array from Claude response, tolerating markdown fences."""
    text = text.strip()
    # Strip ```json ... ``` fences
    text = re.sub(r"^```(?:json)?", "", text, flags=re.MULTILINE)
    text = re.sub(r"```$", "", text, flags=re.MULTILINE)
    text = text.strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        # Try to find the first JSON array in the response
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return []


def _apply_scores(
    investors: list[InvestorRecord], score_data: list[dict]
) -> list[InvestorRecord]:
    score_map = {item["id"]: item for item in score_data if "id" in item}
    result = []
    for inv in investors:
        scored = inv.model_copy(deep=True)
        data = score_map.get(inv.id)
        if data:
            scored.fit_score = max(0, min(100, int(data.get("fit_score", 0))))
            scored.relevant_portfolio = data.get("relevant_portfolio", [])
            scored.has_competitor_conflict = bool(data.get("has_competitor_conflict", False))
            scored.conflicting_competitors = data.get("conflicting_competitors", [])
            scored.score_reasoning = data.get("score_reasoning", "")
        else:
            scored.fit_score = 0
        result.append(scored)
    return result


async def score_investor_batch(
    investors: list[InvestorRecord],
    request: FindInvestorsRequest,
) -> list[InvestorRecord]:
    """Score a batch of investors with a single Claude call."""
    async with _semaphore:
        await rate_limiter.acquire()
        client = _get_client()

        company_profile = _build_company_profile(request)
        investor_list = _build_investor_list(investors)
        competitor_list = ", ".join(request.competitors) if request.competitors else "None"

        prompt = f"""You are an expert startup fundraising advisor. Score each investor below for fit with this company.

## Company Profile
{company_profile}

## Competitors to Flag
{competitor_list}

## Investors to Score
{investor_list}

## Scoring Weights
- Business model fit (50 pts): Does the investor back this type of company (B2B SaaS, Vertical AI, Fintech, etc.)? Do their thesis and sector focus align with the business type, industry, and target customer?
- Stage fit (30 pts): Does their check size and stage focus match the round being raised?
- Growth metrics fit (20 pts): Do the ARR and growth numbers suggest this is an attractive company for their portfolio?

## Instructions
Return ONLY a valid JSON array (no markdown, no explanation). For each investor return:
{{
  "id": "<exact id string>",
  "fit_score": <integer 0-100>,
  "relevant_portfolio": ["<company>", ...],
  "has_competitor_conflict": <true|false>,
  "conflicting_competitors": ["<competitor>", ...],
  "score_reasoning": "<1-2 sentence explanation>"
}}

Relevant portfolio: list companies from the investor's portfolio that are relevant to this startup's space.
Competitor conflict: set true if the investor has invested in ANY of the listed competitors.
Return exactly {len(investors)} objects in the array, one per investor.
"""

        try:
            message = await client.messages.create(
                model=settings.claude_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text
            score_data = _extract_json(raw)
            return _apply_scores(investors, score_data)
        except Exception as e:
            logger.error(f"Claude batch scoring failed: {e}")
            # Return investors with score=0 so pipeline doesn't fail
            for inv in investors:
                inv.fit_score = 0
            return investors


async def score_all_investors(
    investors: list[InvestorRecord],
    request: FindInvestorsRequest,
    progress_callback: Callable[[str], Awaitable[None]] | None = None,
) -> list[InvestorRecord]:
    """Score all investors in concurrent batches."""
    batch_size = settings.scoring_batch_size
    batches = [
        investors[i: i + batch_size]
        for i in range(0, len(investors), batch_size)
    ]
    total = len(batches)
    scored: list[InvestorRecord] = []

    async def score_one(batch: list[InvestorRecord], index: int) -> list[InvestorRecord]:
        result = await score_investor_batch(batch, request)
        if progress_callback:
            await progress_callback(f"Scored {min((index + 1) * batch_size, len(investors))}/{len(investors)} investors")
        return result

    tasks = [score_one(batch, i) for i, batch in enumerate(batches)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, Exception):
            logger.error(f"Batch failed: {r}")
            continue
        scored.extend(r)

    return scored

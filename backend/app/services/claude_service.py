"""Dynamic Claude-powered investor research pipeline."""
import asyncio
import json
import logging
import re
from typing import Callable, Awaitable

import anthropic

from app.config import get_settings
from app.models.investor import DataSource, InvestorRecord
from app.models.request import FindInvestorsRequest
from app.utils import rate_limiter

logger = logging.getLogger(__name__)
settings = get_settings()

_semaphore = asyncio.Semaphore(settings.max_concurrent_batches)


def _get_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _extract_json(text: str) -> list[dict]:
    """Extract JSON array from Claude response, tolerating markdown fences."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text, flags=re.MULTILINE)
    text = re.sub(r"```$", "", text, flags=re.MULTILINE)
    text = text.strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return []


def _build_company_profile(request: FindInvestorsRequest) -> str:
    """Build a dynamic company profile string from request inputs."""
    lines = []
    if request.company_url:
        lines.append(f"Company URL: {request.company_url}")
    if request.industries:
        lines.append(f"Industry / Category: {', '.join(request.industries)}")
    if request.keywords:
        lines.append(f"Business Type(s) / Keywords: {', '.join(request.keywords)}")
    if request.icp_segments:
        lines.append(f"ICP / Target Segments: {', '.join(request.icp_segments)}")
    if request.arr is not None:
        lines.append(f"ARR: ${request.arr}M")
    if request.arr_growth is not None:
        lines.append(f"ARR Growth YoY: {request.arr_growth}%")
    if request.round_stage:
        lines.append(f"Round Stage: {request.round_stage}")
    if request.competitors:
        lines.append(f"Competitor URLs: {', '.join(request.competitors)}")
    if request.further_context:
        lines.append(f"Additional Context: {request.further_context}")
    return "\n".join(lines)


# ─── Phase 1: Competitor Conflict Research ──────────────────────────────────

async def research_competitor_conflicts(
    competitors: list[str],
) -> dict[str, list[str]]:
    """Ask Claude which VC/PE firms have invested in each competitor."""
    if not competitors:
        return {}

    async with _semaphore:
        await rate_limiter.acquire()
        client = _get_client()

        competitor_list = ", ".join(competitors)
        prompt = f"""I need to identify which VC/PE firms have invested in these companies: {competitor_list}

For each company, list the known investors (fund/firm names only, not individual names).
Use your training knowledge. Only include firms you are reasonably confident about.
Mark "Unknown" in known_investors if you have no reliable information.

Return ONLY a valid JSON array, no markdown:
[{{"competitor": "CompanyName", "known_investors": ["Fund A", "Fund B"]}}]

One object per company listed above."""

        try:
            message = await client.messages.create(
                model=settings.claude_model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text
            data = _extract_json(raw)
            result: dict[str, list[str]] = {}
            for item in data:
                if isinstance(item, dict):
                    comp = item.get("competitor", "")
                    investors = [
                        i for i in (item.get("known_investors") or [])
                        if isinstance(i, str) and i.lower() != "unknown"
                    ]
                    if comp:
                        result[comp] = investors
            logger.info(f"Conflict research: found investors for {len(result)} competitors")
            return result
        except Exception as e:
            logger.error(f"Competitor conflict research failed: {e}")
            return {}


# ─── Phase 2: Full Investor Research (single comprehensive call) ─────────────

async def generate_full_investor_list(
    request: FindInvestorsRequest,
    conflict_map: dict[str, list[str]],
    target: int = 100,
    exclude: set[str] | None = None,
) -> list[InvestorRecord]:
    """
    Single comprehensive Claude call that generates, validates, scores, and tiers
    the full investor list using the structured research prompt.
    """
    async with _semaphore:
        await rate_limiter.acquire()
        client = _get_client()

        company_profile = _build_company_profile(request)

        # Build conflict section
        conflict_firms: list[str] = []
        for investors in conflict_map.values():
            conflict_firms.extend(investors)
        conflict_note = ""
        if conflict_firms:
            conflict_note = (
                f"Funds with known investments in competitors "
                f"(flag, do NOT exclude): {', '.join(set(conflict_firms)[:30])}"
            )

        competitors_str = (
            ", ".join(request.competitors) if request.competitors
            else "None provided"
        )
        round_stage = request.round_stage or "Seed / Pre-Series A"
        keywords_str = (
            ", ".join(request.keywords) if request.keywords
            else "Vertical SaaS / AI"
        )
        icp_str = (
            ", ".join(request.icp_segments) if request.icp_segments
            else "Not specified"
        )

        exclude_note = ""
        if exclude:
            sample = list(exclude)[:25]
            exclude_note = f"\n\nDo NOT repeat these firms (already in list): {', '.join(sample)}"

        prompt = f"""You are a meticulous venture research analyst. Your task is to create an ACCURATE, citation-backed list of {target} potential investor VC firms for the company described below.

Identify the best partner at each firm, explain why they're a fit, and include relevant past investments. Output must be clean, deduped, and ready for CSV.

---

ABOUT THE COMPANY
{company_profile}
• Geo preference: North America (prioritize USA)
• Conflicts to avoid (flag, do not exclude): Funds with active board seats or publicly-disclosed investments in: {competitors_str}

TARGET INVESTOR PROFILE
• Stage: {round_stage}
• Keywords / Themes: {keywords_str}
• ICP / Buyer: {icp_str} customer segments
• Geography: Prioritize North America
• Conflict Flags: Flag firms with active board seats in direct competitors — highlight but include

HOW TO FIND CANDIDATES
1) Backtrace from the competitor URLs listed; identify who led or followed into similar rounds
2) Use primary sources (firm sites, press, partner bios) and your training data
3) Confirm LEAD vs participant; capture board seats
4) Use last 5–7 years to evidence lead behavior{conflict_note}

DATA QUALITY (no hallucinations)
• Each row: 2–3 evidence links from credible sources. If not verifiable, use "https://needs-verification.com" as placeholder
• Confirm lead behavior from training data before marking "Yes" on LeadsRoundFrequently

SCORING & TIERS
PrestigeScore (0–100): Outcomes/Brand (30pts) + Lead Velocity (25pts) + Platform Strength (15pts) + Cross-Cycle Conviction (15pts) + Peer Signaling (15pts)
FitScore (0–100): Sector Relevance (35pts) + Thesis Fit (35pts) + Geo/Stage Match (15pts) + Conflict Risk (15pts — penalize active competitor boards)
• Tier 1 = PrestigeScore 80–100 | Tier 2 = 60–79 | Tier 3 = 40–59

ORDERING
Group by Tier (1→2→3). Within Tier, sort by FitScore desc, then PrestigeScore desc.{exclude_note}

REQUIRED OUTPUT
Return ONLY a valid JSON array of exactly {target} objects, no markdown fences:
[{{
  "tier": 1,
  "prestige_score": 85,
  "fit_score": 90,
  "firm": "Exact Fund Name",
  "recommended_partner": "Best Partner Name",
  "partner_title": "General Partner",
  "firm_url": "https://...",
  "partner_linkedin": "https://linkedin.com/in/...",
  "geo_focus": "USA / North America",
  "typical_lead_check_usd": "$2M–$5M",
  "leads_round_frequently": "Yes",
  "why_fit": ["Specific reason 1", "Specific reason 2", "Specific reason 3"],
  "relevant_past_investments": ["Company Name (Series A, 2022)", "Company2 (Seed, 2021)"],
  "evidence_links": ["https://...", "https://..."],
  "has_competitor_conflict": false,
  "conflicting_competitors": [],
  "notes": "One sentence additional context or flag"
}}]

Deliver the single JSON array now. Minimum {target} rows."""

        try:
            message = await client.messages.create(
                model=settings.claude_model,
                max_tokens=16000,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text
            logger.info(
                f"generate_full_investor_list: {len(raw)} chars, "
                f"stop_reason={message.stop_reason}, target={target}"
            )
            if message.stop_reason == "max_tokens":
                logger.error(
                    f"STILL TRUNCATED at max_tokens=16000! "
                    f"First 500 chars: {raw[:500]!r}"
                )
            data = _extract_json(raw)
            if not data:
                logger.error(
                    f"JSON extraction returned empty list. "
                    f"First 500 chars of response: {raw[:500]!r}"
                )

            records: list[InvestorRecord] = []
            seen_ids: set[str] = set()

            for item in data:
                if not isinstance(item, dict):
                    continue
                firm = str(item.get("firm") or "").strip()
                if not firm:
                    continue
                if exclude and firm.lower() in exclude:
                    continue

                record_id = _slugify(firm)
                if record_id in seen_ids:
                    record_id = f"{record_id}_{len(seen_ids)}"
                seen_ids.add(record_id)

                raw_tier = item.get("tier")
                tier = raw_tier if raw_tier in (1, 2, 3) else 3

                records.append(InvestorRecord(
                    id=record_id,
                    fund_name=firm,
                    target_partner=item.get("recommended_partner"),
                    partner_title=item.get("partner_title"),
                    website=item.get("firm_url"),
                    linkedin_url=item.get("partner_linkedin"),
                    geography=item.get("geo_focus"),
                    check_size_raw=item.get("typical_lead_check_usd"),
                    lead_or_follow="Lead" if item.get("leads_round_frequently") == "Yes" else None,
                    leads_round_frequently=item.get("leads_round_frequently"),
                    prestige_score=max(0, min(100, int(item.get("prestige_score") or 0))),
                    fit_score=max(0, min(100, int(item.get("fit_score") or 0))),
                    tier=tier,
                    why_fit=item.get("why_fit") or [],
                    relevant_past_investments=item.get("relevant_past_investments") or [],
                    evidence_links=item.get("evidence_links") or [],
                    has_competitor_conflict=bool(item.get("has_competitor_conflict", False)),
                    conflicting_competitors=item.get("conflicting_competitors") or [],
                    notes=item.get("notes"),
                    source=DataSource.claude,
                ))

            logger.info(f"Full investor research returned {len(records)} records")
            return records

        except Exception as e:
            logger.error(f"Full investor list generation failed: {e}")
            return []


# ─── Progress-wrapped alias for use in pipeline ──────────────────────────────

async def generate_investors_with_progress(
    request: FindInvestorsRequest,
    conflict_map: dict[str, list[str]],
    target: int = 100,
    exclude: set[str] | None = None,
    progress_callback: Callable[[str], Awaitable[None]] | None = None,
) -> list[InvestorRecord]:
    if progress_callback:
        await progress_callback("generate")
    result = await generate_full_investor_list(request, conflict_map, target, exclude)
    if progress_callback:
        await progress_callback(f"Generated {len(result)} investors")
    return result

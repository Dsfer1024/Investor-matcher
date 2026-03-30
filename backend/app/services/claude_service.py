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


# ─── Phase 2: Investor Longlist Generation ──────────────────────────────────

async def generate_investor_longlist(
    request: FindInvestorsRequest,
    conflict_map: dict[str, list[str]],
    target: int = 120,
    exclude: set[str] | None = None,
) -> list[InvestorRecord]:
    """Ask Claude to generate a longlist of investors for this company profile."""
    async with _semaphore:
        await rate_limiter.acquire()
        client = _get_client()

        company_profile = _build_company_profile(request)
        exclude_note = ""
        if exclude:
            sample = list(exclude)[:20]
            exclude_note = f"\n\nDo NOT include these funds (already found): {', '.join(sample)}"

        conflict_funds = set()
        for investors in conflict_map.values():
            conflict_funds.update(i.lower() for i in investors)
        conflict_note = ""
        if conflict_funds:
            conflict_note = f"\n\nEXCLUDE these funds (invested in competitors): {', '.join(list(conflict_funds)[:20])}"

        prompt = f"""You are a meticulous venture research analyst. Generate a longlist of exactly {target} VC and PE firms that would be ideal investors for this company.

## Company Profile
{company_profile}

## Requirements
- Match the round stage: include funds that actively invest at this stage with appropriate check sizes
- Prioritize North America geography
- Include a mix of: top-tier brand-name VCs, specialist vertical/sector funds, and emerging managers with relevant thesis
- Exclude: angels, family offices, pure CVCs (unless proven stage leaders), growth-only funds investing too late
- Include both lead investors and strong follow-on investors
- Aim for diversity: different fund sizes, geographies within NA, investment styles{exclude_note}{conflict_note}

Return ONLY a valid JSON array of exactly {target} objects, no markdown:
[{{
  "id": "slugified_fund_name",
  "fund_name": "Exact Fund Name",
  "target_partner": "Best Partner Name",
  "check_size_raw": "$Xm-$Ym",
  "fund_size_raw": "$XM",
  "areas_of_focus": ["tag1", "tag2"],
  "stages_invested": ["Stage A", "Stage B"],
  "portfolio_companies": ["Co1", "Co2", "Co3"],
  "website": "https://...",
  "geography": "USA / North America",
  "lead_or_follow": "Lead"
}}]"""

        try:
            message = await client.messages.create(
                model=settings.claude_model,
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text
            data = _extract_json(raw)
            records: list[InvestorRecord] = []
            seen_ids: set[str] = set()
            for item in data:
                if not isinstance(item, dict):
                    continue
                fund_name = str(item.get("fund_name") or "").strip()
                if not fund_name:
                    continue
                # Skip excluded funds
                if exclude and fund_name.lower() in exclude:
                    continue
                record_id = item.get("id") or _slugify(fund_name)
                if record_id in seen_ids:
                    record_id = f"{record_id}_{len(seen_ids)}"
                seen_ids.add(record_id)

                records.append(InvestorRecord(
                    id=record_id,
                    fund_name=fund_name,
                    target_partner=item.get("target_partner"),
                    check_size_raw=item.get("check_size_raw"),
                    fund_size_raw=item.get("fund_size_raw"),
                    areas_of_focus=item.get("areas_of_focus") or [],
                    stages_invested=item.get("stages_invested") or [],
                    portfolio_companies=item.get("portfolio_companies") or [],
                    website=item.get("website"),
                    geography=item.get("geography"),
                    lead_or_follow=item.get("lead_or_follow"),
                    source=DataSource.claude,
                ))
            logger.info(f"Generated longlist of {len(records)} investors")
            return records
        except Exception as e:
            logger.error(f"Longlist generation failed: {e}")
            return []


# ─── Phase 3: Enrich + Score ─────────────────────────────────────────────────

def _build_investor_block(investors: list[InvestorRecord]) -> str:
    items = []
    for inv in investors:
        focus = ", ".join(inv.areas_of_focus[:8]) or "Unknown"
        stages = ", ".join(inv.stages_invested[:4]) or "Unknown"
        portfolio = ", ".join(inv.portfolio_companies[:10]) or "None listed"
        check = inv.check_size_raw or "Unknown"
        fund_size = inv.fund_size_raw or "Unknown"
        items.append(
            f'ID: {inv.id}\n'
            f'  Fund: {inv.fund_name}\n'
            f'  Partner: {inv.target_partner or "Unknown"}\n'
            f'  Focus: {focus}\n'
            f'  Stages: {stages}\n'
            f'  Check Size: {check}\n'
            f'  Fund Size: {fund_size}\n'
            f'  Geography: {inv.geography or "Unknown"}\n'
            f'  Portfolio: {portfolio}'
        )
    return "\n\n".join(items)


async def enrich_and_score_batch(
    investors: list[InvestorRecord],
    request: FindInvestorsRequest,
    conflict_map: dict[str, list[str]],
) -> list[InvestorRecord]:
    """Enrich and score a batch of investors in a single Claude call."""
    async with _semaphore:
        await rate_limiter.acquire()
        client = _get_client()

        company_profile = _build_company_profile(request)
        investor_block = _build_investor_block(investors)
        conflict_json = json.dumps(conflict_map) if conflict_map else "{}"
        competitor_list = ", ".join(request.competitors) if request.competitors else "None"

        prompt = f"""You are a meticulous venture research analyst. Enrich and score each investor below for this company.

## Company Profile
{company_profile}

## Competitors to Flag as Conflicts
{competitor_list}

## Known Competitor Investors (conflict map)
{conflict_json}

## Investors to Score
{investor_block}

## Scoring Rubric
**PrestigeScore (0-100):**
- Outcomes/Brand (30pts): Track record of exits, unicorns, fund reputation
- Lead Velocity (25pts): How frequently they lead rounds at this stage
- Platform Strength (15pts): Value-add beyond capital (network, hiring, BD)
- Cross-Cycle Conviction (15pts): Invested through downturns, consistent follow-on
- Peer Signaling (15pts): Co-investor quality, LP base credibility

**FitScore (0-100):**
- Sector Relevance (35pts): Portfolio alignment with this company's sector and keywords
- Thesis Fit (35pts): Does their stated investment thesis match this business model and ICP?
- Geo/Stage Match (15pts): Geography and check size alignment with this round
- Conflict Risk (15pts): Penalize if they have active board seats in direct competitors

**Tier:**
- Tier 1: PrestigeScore 80-100
- Tier 2: PrestigeScore 60-79
- Tier 3: PrestigeScore 40-59

## Instructions
For EACH investor, return an enriched object. Use your training knowledge to fill in accurate details.
If you're unsure of a specific URL or detail, use your best knowledge or omit it.

Return ONLY a valid JSON array, no markdown:
[{{
  "id": "<exact id>",
  "partner_title": "General Partner",
  "linkedin_url": "https://linkedin.com/in/...",
  "prestige_score": 0-100,
  "fit_score": 0-100,
  "tier": 1 or 2 or 3,
  "why_fit": ["Bullet 1 explaining fit", "Bullet 2", "Bullet 3"],
  "relevant_portfolio": ["Company (Stage, Year)", ...],
  "evidence_links": ["https://...", "https://..."],
  "has_competitor_conflict": true or false,
  "conflicting_competitors": ["CompetitorName if applicable"],
  "notes": "One sentence additional note"
}}]

Return exactly {len(investors)} objects."""

        try:
            message = await client.messages.create(
                model=settings.claude_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text
            score_data = _extract_json(raw)
            score_map = {item["id"]: item for item in score_data if "id" in item}

            result = []
            for inv in investors:
                enriched = inv.model_copy(deep=True)
                data = score_map.get(inv.id, {})
                if data:
                    enriched.partner_title = data.get("partner_title") or inv.partner_title
                    enriched.linkedin_url = data.get("linkedin_url") or inv.linkedin_url
                    enriched.prestige_score = max(0, min(100, int(data.get("prestige_score") or 0)))
                    enriched.fit_score = max(0, min(100, int(data.get("fit_score") or 0)))
                    raw_tier = data.get("tier")
                    enriched.tier = raw_tier if raw_tier in (1, 2, 3) else 3
                    enriched.why_fit = data.get("why_fit") or []
                    enriched.relevant_portfolio = data.get("relevant_portfolio") or []
                    enriched.evidence_links = data.get("evidence_links") or []
                    enriched.has_competitor_conflict = bool(data.get("has_competitor_conflict", False))
                    enriched.conflicting_competitors = data.get("conflicting_competitors") or []
                    enriched.notes = data.get("notes")
                else:
                    enriched.prestige_score = 0
                    enriched.fit_score = 0
                    enriched.tier = 3
                result.append(enriched)
            return result
        except Exception as e:
            logger.error(f"Enrichment batch failed: {e}")
            for inv in investors:
                inv.prestige_score = 0
                inv.fit_score = 0
                inv.tier = 3
            return investors


async def enrich_and_score_all(
    investors: list[InvestorRecord],
    request: FindInvestorsRequest,
    conflict_map: dict[str, list[str]],
    progress_callback: Callable[[str], Awaitable[None]] | None = None,
) -> list[InvestorRecord]:
    """Enrich and score all investors in concurrent batches."""
    batch_size = settings.scoring_batch_size
    batches = [
        investors[i: i + batch_size]
        for i in range(0, len(investors), batch_size)
    ]
    total_investors = len(investors)
    scored: list[InvestorRecord] = []
    completed = 0

    async def score_one(batch: list[InvestorRecord]) -> list[InvestorRecord]:
        nonlocal completed
        result = await enrich_and_score_batch(batch, request, conflict_map)
        completed += len(batch)
        if progress_callback:
            await progress_callback(
                f"Enriched {min(completed, total_investors)}/{total_investors} investors"
            )
        return result

    tasks = [score_one(batch) for batch in batches]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, Exception):
            logger.error(f"Enrichment batch exception: {r}")
            continue
        scored.extend(r)

    return scored

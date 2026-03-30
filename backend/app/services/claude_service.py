"""Claude-powered investor research — streaming pipeline."""
import json
import logging
import re
from typing import AsyncGenerator, Any

import anthropic

from app.config import get_settings
from app.models.investor import DataSource, InvestorRecord
from app.models.request import FindInvestorsRequest

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _build_company_profile(request: FindInvestorsRequest) -> str:
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
    if request.raise_amount is not None:
        min_check = round(request.raise_amount * 0.30, 2)
        lines.append(f"Desired Raise: ${request.raise_amount}M")
        lines.append(f"Minimum Investor Check Size: ${min_check}M (30% of raise)")
    if request.competitors:
        lines.append(f"Competitor URLs: {', '.join(request.competitors)}")
    if request.further_context:
        lines.append(f"Additional Context: {request.further_context}")
    return "\n".join(lines)


def _parse_record(item: dict, seen_ids: set[str]) -> InvestorRecord | None:
    """Parse a raw JSON dict into an InvestorRecord. Returns None if invalid."""
    firm = str(item.get("firm") or "").strip()
    if not firm:
        return None
    record_id = _slugify(firm)
    if record_id in seen_ids:
        record_id = f"{record_id}_{len(seen_ids)}"
    seen_ids.add(record_id)

    raw_tier = item.get("tier")
    tier = raw_tier if raw_tier in (1, 2, 3) else 3

    return InvestorRecord(
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
    )


def _build_prompt(profile: str, target: int) -> str:
    competitors_str = next(
        (line.split(": ", 1)[1] for line in profile.splitlines() if line.startswith("Competitor URLs:")),
        "None provided",
    )
    round_stage = next(
        (line.split(": ", 1)[1] for line in profile.splitlines() if line.startswith("Round Stage:")),
        "Seed / Series A",
    )
    keywords_str = next(
        (line.split(": ", 1)[1] for line in profile.splitlines() if line.startswith("Business Type")),
        "Vertical SaaS / AI",
    )
    icp_str = next(
        (line.split(": ", 1)[1] for line in profile.splitlines() if line.startswith("ICP")),
        "Not specified",
    )

    # Build check-size filter line if raise_amount was provided
    min_check = None
    for line in profile.splitlines():
        if line.startswith("Minimum Investor Check Size:"):
            try:
                min_check = float(line.split("$")[1].split("M")[0])
            except Exception:
                pass
    check_size_rule = (
        f"• Minimum check size: ${min_check}M — only include investors whose typical lead check "
        f"starts at ${min_check}M or above (30% of the desired raise)"
        if min_check is not None
        else ""
    )

    return f"""You are a meticulous venture research analyst. Create an ACCURATE, citation-backed list of {target} investor VC firms for the company below.

ABOUT THE COMPANY
{profile}
• Geo preference: North America (prioritize USA)
• Conflicts: Flag firms with active board seats in: {competitors_str} — include but flag

TARGET INVESTOR PROFILE
• Stage: {round_stage}
• Keywords / Themes: {keywords_str}
• ICP / Buyer: {icp_str} customer segments
• Geography: Prioritize North America
{check_size_rule}

SCORING & TIERS
PrestigeScore (0–100): Outcomes/Brand (30pts) + Lead Velocity (25pts) + Platform Strength (15pts) + Cross-Cycle Conviction (15pts) + Peer Signaling (15pts)
FitScore (0–100): Sector Relevance (35pts) + Thesis Fit (35pts) + Geo/Stage Match (15pts) + Conflict Risk (15pts — penalize active competitor boards)
Tier 1 = PrestigeScore 80–100 | Tier 2 = 60–79 | Tier 3 = 40–59

OUTPUT FORMAT
First write one paragraph labeled "QUICK THESIS:" summarizing the company, ideal investor profile, and what makes a perfect lead. 3–4 sentences.

Then output a valid JSON array of exactly {target} objects (no markdown fences):
[{{
  "tier": 1,
  "prestige_score": 85,
  "fit_score": 90,
  "firm": "Exact Fund Name",
  "recommended_partner": "Partner Name",
  "partner_title": "General Partner",
  "firm_url": "https://...",
  "partner_linkedin": "https://linkedin.com/in/...",
  "geo_focus": "USA / North America",
  "typical_lead_check_usd": "$2M–$5M",
  "leads_round_frequently": "Yes",
  "why_fit": ["Specific reason 1", "Specific reason 2"],
  "relevant_past_investments": ["Company A (Series A, 2022)", "Company B (Seed, 2021)"],
  "evidence_links": ["https://...", "https://..."],
  "has_competitor_conflict": false,
  "conflicting_competitors": [],
  "notes": "One sentence of context"
}}]"""


async def stream_investors(
    request: FindInvestorsRequest,
    target: int = 25,
) -> AsyncGenerator[tuple[str, Any], None]:
    """
    Async generator that streams investor data from Claude token-by-token.
    Yields:
      ("thesis", str)           — quick thesis paragraph, emitted as soon as Claude writes it
      ("investor", InvestorRecord) — each investor the moment its JSON object closes
      ("error", str)            — if something goes wrong
    """
    client = _get_client()
    profile = _build_company_profile(request)
    prompt = _build_prompt(profile, target)

    # JSON streaming state machine
    buffer = ""
    in_string = False
    escape_next = False
    array_started = False
    depth = 0
    obj_start = 0
    thesis_sent = False
    seen_ids: set[str] = set()

    try:
        async with client.messages.stream(
            model=settings.claude_model,
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text_chunk in stream.text_stream:
                for char in text_chunk:
                    buffer += char

                    # ── String-escape tracking ──────────────────────
                    if escape_next:
                        escape_next = False
                        continue
                    if char == "\\" and in_string:
                        escape_next = True
                        continue
                    if char == '"':
                        in_string = not in_string
                        continue
                    if in_string:
                        continue

                    # ── Before the JSON array: extract thesis ────────
                    if not array_started:
                        if char == "[":
                            array_started = True
                            if not thesis_sent:
                                bracket_pos = len(buffer) - 1
                                raw = buffer[:bracket_pos].strip()
                                raw = re.sub(
                                    r"^QUICK THESIS[:\s*\n]*", "", raw, flags=re.IGNORECASE
                                ).strip()
                                thesis = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", raw)
                                yield ("thesis", thesis)
                                thesis_sent = True
                        continue

                    # ── Inside the JSON array: track object depth ────
                    if char == "{":
                        if depth == 0:
                            obj_start = len(buffer) - 1
                        depth += 1
                    elif char == "}":
                        depth -= 1
                        if depth == 0 and obj_start is not None:
                            obj_json = buffer[obj_start : len(buffer)]
                            try:
                                data = json.loads(obj_json)
                                record = _parse_record(data, seen_ids)
                                if record:
                                    yield ("investor", record)
                            except json.JSONDecodeError:
                                pass

    except anthropic.APIStatusError as e:
        logger.error(f"Anthropic API error: {e.status_code} {e.message}")
        yield ("error", f"AI API error ({e.status_code}). Please try again.")
    except Exception as e:
        logger.error(f"stream_investors failed: {e}")
        yield ("error", str(e))

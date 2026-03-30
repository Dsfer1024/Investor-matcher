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
        # Expand bridge stages into investor targeting instructions
        bridge_map = {
            "Bridge (Seed-A)": "Bridge round between Seed and Series A — target investors who lead Seed, larger Seed, or small Series A rounds ($500K–$4M checks)",
            "Bridge (A-B)": "Bridge round between Series A and B — target investors who lead large Seeds, Series As, or small Series Bs ($3M–$15M checks)",
            "Bridge (B and Beyond)": "Bridge round B-stage and beyond — target investors who lead Series Bs, Cs, or Ds ($10M–$75M checks)",
            "Majority Buyout": "Majority buyout — target ONLY PE funds, growth equity firms, or VCs that explicitly do majority ownership deals. Do NOT include minority-only VC funds.",
        }
        if request.round_stage in bridge_map:
            lines.append(f"Stage Detail: {bridge_map[request.round_stage]}")
    if request.investor_types:
        lines.append(f"Investor Types Requested: {', '.join(request.investor_types)}")
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

    # Build investor type weighting rule
    investor_types_str = next(
        (line.split(": ", 1)[1] for line in profile.splitlines() if line.startswith("Investor Types Requested:")),
        "",
    )
    types = [t.strip() for t in investor_types_str.split(",") if t.strip()]
    has_vc = "VC" in types
    has_ge = "Growth Equity" in types
    has_pe = "Private Equity" in types

    if has_vc and not has_ge and not has_pe:
        investor_type_rule = "• Investor mix: 100% VC / venture capital firms ONLY. Do not include PE or growth equity funds."
    elif has_vc and (has_ge or has_pe):
        investor_type_rule = "• Investor mix: at least 80% must be VC / venture capital firms. Remainder can be minority growth equity if highly relevant. No majority-only PE unless stage is Majority Buyout."
    elif not has_vc and (has_ge or has_pe):
        parts = []
        if has_ge:
            parts.append("growth equity")
        if has_pe:
            parts.append("private equity")
        investor_type_rule = f"• Investor mix: focus on {' and '.join(parts)} funds. No VC-only early-stage funds."
    else:
        investor_type_rule = ""

    return f"""You are a venture research analyst. Return a JSON list of {target} investors for the company below. Be concise — short field values only.

COMPANY
{profile}
Geo: North America (USA priority)
Conflicts: Flag board seats in {competitors_str} — include but mark has_competitor_conflict=true
{check_size_rule}
{investor_type_rule}

INVESTOR CRITERIA
Stage: {round_stage} | Keywords: {keywords_str} | ICP: {icp_str}

SCORING
PrestigeScore (0-100): Brand/Outcomes 30 + Lead Velocity 25 + Platform 15 + Cross-Cycle 15 + Peer Signal 15
FitScore (0-100): Sector Fit 35 + Thesis 35 + Geo/Stage 15 + Conflict Risk 15
Tier 1=80-100 Tier 2=60-79 Tier 3=40-59

OUTPUT: First write "QUICK THESIS:" paragraph (3 sentences max). Then a JSON array of exactly {target} objects. Keep every string value SHORT (firm names exact, why_fit max 2 bullets of ≤12 words each, notes ≤8 words, max 2 past investments, max 2 evidence links). No markdown fences.

[{{"tier":1,"prestige_score":85,"fit_score":90,"firm":"Fund Name","recommended_partner":"Name","partner_title":"GP","firm_url":"https://...","partner_linkedin":"https://linkedin.com/in/...","geo_focus":"USA","typical_lead_check_usd":"$3M-$8M","leads_round_frequently":"Yes","why_fit":["Reason 1","Reason 2"],"relevant_past_investments":["Co A (2022)","Co B (2021)"],"evidence_links":["https://..."],"has_competitor_conflict":false,"conflicting_competitors":[],"notes":"Brief note"}}]

Output all {target} objects now."""


async def stream_investors(
    request: FindInvestorsRequest,
    target: int = 25,
    exclude: set[str] | None = None,
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
            max_tokens=16000,
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
                                    if exclude and record.fund_name.lower() in exclude:
                                        continue
                                    yield ("investor", record)
                            except json.JSONDecodeError:
                                pass

    except anthropic.APIStatusError as e:
        logger.error(f"Anthropic API error: {e.status_code} {e.message}")
        yield ("error", f"AI API error ({e.status_code}). Please try again.")
    except Exception as e:
        logger.error(f"stream_investors failed: {e}")
        yield ("error", str(e))

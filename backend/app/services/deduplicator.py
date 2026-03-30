"""Merge and deduplicate investor records from multiple sources."""
import re

from app.models.investor import DataSource, InvestorRecord

# Suffixes to strip when normalizing fund names for deduplication
_STRIP_WORDS = {
    "ventures", "venture", "capital", "fund", "partners", "management",
    "investments", "group", "holdings", "llc", "lp", "inc", "co",
}

SOURCE_PRIORITY: dict[str, int] = {
    "user_upload": 0,
    "claude": 1,
    "openvc": 2,
    "github": 3,
    "merged": 4,
}


def _normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9 ]+", " ", name)
    words = [w for w in name.split() if w not in _STRIP_WORDS]
    return " ".join(words).strip()


def _merge(a: InvestorRecord, b: InvestorRecord) -> InvestorRecord:
    """Merge two records; higher-priority source wins on field conflicts."""
    a_pri = SOURCE_PRIORITY.get(a.source, 99)
    b_pri = SOURCE_PRIORITY.get(b.source, 99)
    primary, secondary = (a, b) if a_pri <= b_pri else (b, a)

    merged = primary.model_copy(deep=True)

    # Fill None scalar fields from secondary
    scalar_fields = [
        "target_partner", "fund_size_raw", "fund_size_usd",
        "check_size_min_usd", "check_size_max_usd", "check_size_raw",
        "lead_or_follow", "website", "linkedin_url", "geography",
    ]
    for field in scalar_fields:
        if getattr(merged, field) is None and getattr(secondary, field) is not None:
            setattr(merged, field, getattr(secondary, field))

    # Union list fields
    merged.areas_of_focus = list(
        dict.fromkeys(primary.areas_of_focus + secondary.areas_of_focus)
    )
    merged.portfolio_companies = list(
        dict.fromkeys(primary.portfolio_companies + secondary.portfolio_companies)
    )
    merged.stages_invested = list(
        dict.fromkeys(primary.stages_invested + secondary.stages_invested)
    )
    merged.source = DataSource.merged
    return merged


def deduplicate(records: list[InvestorRecord]) -> list[InvestorRecord]:
    seen: dict[str, InvestorRecord] = {}
    for record in records:
        key = _normalize_name(record.fund_name)
        if not key:
            continue
        if key in seen:
            seen[key] = _merge(seen[key], record)
        else:
            seen[key] = record
    return list(seen.values())

"""Parse user-uploaded CSV or Excel investor spreadsheets."""
import re
import logging
from io import BytesIO

import pandas as pd

from app.models.investor import DataSource, InvestorRecord

logger = logging.getLogger(__name__)

# Maps canonical field names → accepted column header variations
COLUMN_ALIASES: dict[str, list[str]] = {
    "fund_name": ["fund name", "firm", "firm name", "vc name", "investor", "fund"],
    "target_partner": ["partner", "contact", "partner name", "gp name", "managing partner", "target partner"],
    "check_size_min": ["check size min", "min check", "minimum check", "min investment", "check min (usd)", "check size min (usd)"],
    "check_size_max": ["check size max", "max check", "maximum check", "max investment", "check max (usd)", "check size max (usd)"],
    "check_size_raw": ["check size", "investment size", "ticket size", "typical check"],
    "areas_of_focus": ["focus", "focus areas", "sectors", "thesis", "industries", "areas", "areas of focus"],
    "portfolio_companies": ["portfolio", "investments", "companies invested", "portfolio companies"],
    "stages_invested": ["stage", "stages", "investment stage", "stages invested"],
    "website": ["website", "url", "web", "link", "fund url"],
    "linkedin_url": ["linkedin", "linkedin url", "linkedin profile"],
    "geography": ["geo", "location", "region", "geography"],
    "lead_or_follow": ["lead or follow", "lead", "follow", "lead/follow", "investing type"],
    "fund_size_raw": ["fund size", "aum", "fund size ($)", "fund size (usd)"],
    "notes": ["notes", "comments", "description", "additional info"],
}


def _normalize_col(col: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", col.lower()).strip()


def _build_column_map(columns: list[str]) -> dict[str, str]:
    """Map canonical field names to actual dataframe column names."""
    normalized = {_normalize_col(c): c for c in columns}
    result = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                result[canonical] = normalized[alias]
                break
    return result


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _parse_comma_list(value) -> list[str]:
    if not value or (isinstance(value, float)):
        return []
    return [v.strip() for v in str(value).split(",") if v.strip()]


def _parse_usd(value) -> int | None:
    if not value or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().upper().replace(",", "").replace("$", "")
    multipliers = {"B": 1_000_000_000, "M": 1_000_000, "K": 1_000}
    for suffix, mult in multipliers.items():
        if text.endswith(suffix):
            try:
                return int(float(text[:-1]) * mult)
            except ValueError:
                return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _get(row, col_map: dict, key: str, default=None):
    col = col_map.get(key)
    if col is None:
        return default
    val = row.get(col)
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return val


def parse_spreadsheet(file_bytes: bytes, filename: str) -> list[InvestorRecord]:
    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(BytesIO(file_bytes))
        else:
            df = pd.read_excel(BytesIO(file_bytes))
    except Exception as e:
        logger.error(f"Failed to parse spreadsheet: {e}")
        return []

    col_map = _build_column_map(list(df.columns))
    records = []

    for _, row in df.iterrows():
        fund_name = str(_get(row, col_map, "fund_name", "")).strip()
        if not fund_name or fund_name.lower() in ("nan", "none", ""):
            continue

        check_min = _parse_usd(_get(row, col_map, "check_size_min"))
        check_max = _parse_usd(_get(row, col_map, "check_size_max"))
        check_raw = str(_get(row, col_map, "check_size_raw") or "").strip() or None
        fund_size_raw = str(_get(row, col_map, "fund_size_raw") or "").strip() or None

        records.append(
            InvestorRecord(
                id=f"upload_{_slugify(fund_name)}",
                fund_name=fund_name,
                target_partner=_get(row, col_map, "target_partner"),
                check_size_min_usd=check_min,
                check_size_max_usd=check_max,
                check_size_raw=check_raw,
                fund_size_raw=fund_size_raw,
                fund_size_usd=_parse_usd(fund_size_raw),
                lead_or_follow=_get(row, col_map, "lead_or_follow"),
                areas_of_focus=_parse_comma_list(_get(row, col_map, "areas_of_focus")),
                portfolio_companies=_parse_comma_list(_get(row, col_map, "portfolio_companies")),
                stages_invested=_parse_comma_list(_get(row, col_map, "stages_invested")),
                website=_get(row, col_map, "website"),
                linkedin_url=_get(row, col_map, "linkedin_url"),
                geography=_get(row, col_map, "geography"),
                source=DataSource.user_upload,
                raw_data=row.to_dict(),
            )
        )

    logger.info(f"Parsed {len(records)} investors from uploaded spreadsheet")
    return records

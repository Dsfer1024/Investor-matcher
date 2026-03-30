"""Load investor data from the bundled Excel database."""
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from app.config import get_settings
from app.models.investor import DataSource, InvestorRecord

logger = logging.getLogger(__name__)
settings = get_settings()

EXCEL_PATH = Path(__file__).parent.parent / "data" / "investor_list.xlsx"

# Sheets to load and their primary stage label
SHEET_STAGES = {
    "Pre-seed": "Pre-Seed",
    "Seed": "Seed",
    "Series A": "Series A",
    "Series B": "Series B",
    "Growth Equity": "Growth Equity",
    "Private Equity": "Private Equity",
}

# Adjacent stages added when Multi-stage == Y
ADJACENT_STAGES = {
    "Pre-Seed": ["Pre-Seed", "Seed"],
    "Seed": ["Pre-Seed", "Seed", "Series A"],
    "Series A": ["Seed", "Series A", "Series B"],
    "Series B": ["Series A", "Series B", "Series C"],
    "Growth Equity": ["Series B", "Series C", "Growth Equity"],
    "Private Equity": ["Growth Equity", "Private Equity"],
}


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


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


def _parse_check_size(raw: str) -> tuple[int | None, int | None]:
    """Parse '$500k–$2M' into (500000, 2000000)."""
    if not raw:
        return None, None
    raw = str(raw)
    # Split on em dash, en dash, or hyphen
    parts = re.split(r"[–—\-]", raw)
    if len(parts) == 2:
        return _parse_usd(parts[0].strip()), _parse_usd(parts[1].strip())
    single = _parse_usd(raw)
    return single, single


def _parse_list(value, sep=r"[;,]") -> list[str]:
    if not value or (isinstance(value, float) and pd.isna(value)):
        return []
    return [v.strip() for v in re.split(sep, str(value)) if v.strip()]


def _extract_url(value) -> str | None:
    if not value or (isinstance(value, float) and pd.isna(value)):
        return None
    urls = re.findall(r"https?://[^\s,;]+", str(value))
    return urls[0] if urls else None


def _str_or_none(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    return s if s else None


def _load_from_excel() -> list[InvestorRecord]:
    if not EXCEL_PATH.exists():
        logger.error(f"Investor Excel file not found at {EXCEL_PATH}")
        return []

    records: list[InvestorRecord] = []
    seen_ids: set[str] = set()

    for sheet_name, primary_stage in SHEET_STAGES.items():
        try:
            df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name)
        except Exception as e:
            logger.warning(f"Could not read sheet '{sheet_name}': {e}")
            continue

        # Normalize column names
        df.columns = [str(c).strip() for c in df.columns]

        # Find the actual column names (they may vary slightly)
        col = {}
        for c in df.columns:
            cl = c.lower()
            if "investor" in cl or "firm" in cl:
                col["name"] = c
            elif "category" in cl:
                col["category"] = c
            elif "multi" in cl and "stage" in cl:
                col["multi_stage"] = c
            elif "lead" in cl:
                col["lead"] = c
            elif "first check" in cl or ("check" in cl and "follow" not in cl):
                col["check_size"] = c
            elif "follow" in cl and "capacity" in cl:
                col["followon"] = c
            elif "thesis" in cl or "core" in cl:
                col["thesis"] = c
            elif "us invest" in cl or "investing focus" in cl:
                col["geography"] = c
            elif "recent" in cl or "deals" in cl:
                col["portfolio"] = c
            elif "founder profile" in cl or "best" in cl:
                col["profile"] = c
            elif "proof" in cl or "link" in cl:
                col["links"] = c
            elif "arr entry" in cl:
                col["arr_entry"] = c
            elif "growth equity band" in cl:
                col["ge_band"] = c
            elif "replaces" in cl:
                col["replaces"] = c
            elif "liquidity" in cl:
                col["liquidity"] = c

        for _, row in df.iterrows():
            fund_name = _str_or_none(row.get(col.get("name", ""), None))
            if not fund_name or fund_name.lower() in ("nan", "none", "investor / firm"):
                continue

            record_id = f"xl_{_slugify(fund_name)}_{_slugify(primary_stage)}"
            # Skip exact duplicates within the same sheet
            if record_id in seen_ids:
                continue
            seen_ids.add(record_id)

            # Stages
            multi = _str_or_none(row.get(col.get("multi_stage", ""), None))
            if multi and multi.upper() == "Y":
                stages = ADJACENT_STAGES.get(primary_stage, [primary_stage])
            else:
                stages = [primary_stage]

            # Check size
            check_raw = _str_or_none(row.get(col.get("check_size", ""), None))
            check_min, check_max = _parse_check_size(check_raw or "")

            # Thesis → areas_of_focus
            thesis_raw = _str_or_none(row.get(col.get("thesis", ""), None))
            areas = _parse_list(thesis_raw)

            # Portfolio companies
            portfolio_raw = _str_or_none(row.get(col.get("portfolio", ""), None))
            portfolio = _parse_list(portfolio_raw)

            # Website from proof links
            links_raw = _str_or_none(row.get(col.get("links", ""), None))
            website = _extract_url(links_raw)

            # Lead/follow
            lead_raw = _str_or_none(row.get(col.get("lead", ""), None))

            # Geography
            geo_raw = _str_or_none(row.get(col.get("geography", ""), None))

            # Extra context fields for Claude
            raw_data = {
                "category": _str_or_none(row.get(col.get("category", ""), None)),
                "best_fit_profile": _str_or_none(row.get(col.get("profile", ""), None)),
                "followon_capacity": _str_or_none(row.get(col.get("followon", ""), None)),
                "arr_entry_band": _str_or_none(row.get(col.get("arr_entry", ""), None)),
                "growth_equity_band": _str_or_none(row.get(col.get("ge_band", ""), None)),
                "replaces_series": _str_or_none(row.get(col.get("replaces", ""), None)),
                "founder_liquidity": _str_or_none(row.get(col.get("liquidity", ""), None)),
                "primary_stage": primary_stage,
            }

            records.append(
                InvestorRecord(
                    id=record_id,
                    fund_name=fund_name,
                    check_size_raw=check_raw,
                    check_size_min_usd=check_min,
                    check_size_max_usd=check_max,
                    lead_or_follow=lead_raw,
                    areas_of_focus=areas,
                    stages_invested=stages,
                    portfolio_companies=portfolio,
                    website=website,
                    geography=geo_raw,
                    source=DataSource.user_upload,
                    raw_data=raw_data,
                )
            )

    logger.info(f"Loaded {len(records)} investors from Excel database")
    return records


# ─── Cache layer ────────────────────────────────────────────────────────────

def _cache_path() -> Path:
    return Path(settings.data_cache_dir) / "public_investors_cache.json"


def _cache_meta_path() -> Path:
    return Path(settings.data_cache_dir) / "cache_meta.json"


def _load_from_cache() -> list[InvestorRecord] | None:
    meta_path = _cache_meta_path()
    cache_path = _cache_path()
    if not meta_path.exists() or not cache_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text())
        saved_at = datetime.fromisoformat(meta["saved_at"])
        if datetime.utcnow() - saved_at > timedelta(hours=settings.cache_ttl_hours):
            return None
        raw = json.loads(cache_path.read_text())
        return [InvestorRecord.model_validate(r) for r in raw]
    except Exception as e:
        logger.warning(f"Cache read failed: {e}")
        return None


def _save_to_cache(records: list[InvestorRecord]) -> None:
    Path(settings.data_cache_dir).mkdir(parents=True, exist_ok=True)
    try:
        _cache_path().write_text(
            json.dumps([r.model_dump() for r in records], default=str)
        )
        _cache_meta_path().write_text(
            json.dumps({"saved_at": datetime.utcnow().isoformat()})
        )
    except Exception as e:
        logger.warning(f"Cache write failed: {e}")


async def load_public_investors() -> list[InvestorRecord]:
    """Returns investor list from Excel, using disk cache if fresh."""
    cached = _load_from_cache()
    if cached:
        logger.info(f"Loaded {len(cached)} investors from cache")
        return cached

    records = _load_from_excel()
    _save_to_cache(records)
    return records

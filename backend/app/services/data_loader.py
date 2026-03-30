"""Fetch and cache public investor data from OpenVC and GitHub VC lists."""
import csv
import io
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from app.config import get_settings
from app.models.investor import DataSource, InvestorRecord

logger = logging.getLogger(__name__)
settings = get_settings()


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _parse_comma_list(value: str) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _parse_usd(value: str) -> int | None:
    """Parse strings like '$200M', '200000000', '200m' into int USD."""
    if not value:
        return None
    value = value.strip().upper().replace(",", "").replace("$", "")
    multipliers = {"B": 1_000_000_000, "M": 1_000_000, "K": 1_000}
    for suffix, mult in multipliers.items():
        if value.endswith(suffix):
            try:
                return int(float(value[:-1]) * mult)
            except ValueError:
                return None
    try:
        return int(float(value))
    except ValueError:
        return None


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


async def _fetch_openvc() -> list[InvestorRecord]:
    records = []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(settings.openvc_csv_url)
            resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        for row in reader:
            fund_name = (row.get("Fund Name") or row.get("fund_name") or "").strip()
            if not fund_name:
                continue
            records.append(
                InvestorRecord(
                    id=f"openvc_{_slugify(fund_name)}",
                    fund_name=fund_name,
                    target_partner=row.get("Partner Name") or row.get("partner_name"),
                    website=row.get("Website") or row.get("website"),
                    areas_of_focus=_parse_comma_list(
                        row.get("Focus Areas") or row.get("focus_areas") or ""
                    ),
                    stages_invested=_parse_comma_list(
                        row.get("Stages") or row.get("stages") or ""
                    ),
                    check_size_raw=row.get("Check Size") or row.get("check_size"),
                    fund_size_raw=row.get("Fund Size") or row.get("fund_size"),
                    fund_size_usd=_parse_usd(
                        row.get("Fund Size") or row.get("fund_size") or ""
                    ),
                    geography=row.get("Geography") or row.get("geography"),
                    portfolio_companies=_parse_comma_list(
                        row.get("Portfolio") or row.get("portfolio_companies") or ""
                    ),
                    lead_or_follow=row.get("Lead or Follow") or row.get("lead_or_follow"),
                    source=DataSource.openvc,
                    raw_data=dict(row),
                )
            )
    except Exception as e:
        logger.warning(f"OpenVC fetch failed: {e}")
    logger.info(f"Loaded {len(records)} records from OpenVC")
    return records


async def _fetch_github_lists() -> list[InvestorRecord]:
    records = []
    async with httpx.AsyncClient(timeout=30) as client:
        for url in settings.github_vc_list_urls:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                # Handle both list-of-dicts and dict-with-list shapes
                items = data if isinstance(data, list) else data.get("vcs", data.get("investors", []))
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    fund_name = (
                        item.get("name") or item.get("fund_name") or item.get("firm") or ""
                    ).strip()
                    if not fund_name:
                        continue
                    records.append(
                        InvestorRecord(
                            id=f"gh_{_slugify(fund_name)}",
                            fund_name=fund_name,
                            target_partner=item.get("partner") or item.get("partner_name"),
                            website=item.get("website") or item.get("url"),
                            areas_of_focus=_parse_comma_list(
                                item.get("focus") or item.get("sectors") or ""
                            )
                            if isinstance(item.get("focus") or item.get("sectors"), str)
                            else (item.get("focus") or item.get("sectors") or []),
                            stages_invested=_parse_comma_list(
                                item.get("stages") or ""
                            )
                            if isinstance(item.get("stages"), str)
                            else (item.get("stages") or []),
                            geography=item.get("geography") or item.get("location"),
                            fund_size_raw=str(item.get("fund_size") or ""),
                            fund_size_usd=_parse_usd(str(item.get("fund_size") or "")),
                            check_size_raw=item.get("check_size"),
                            source=DataSource.github,
                            raw_data=item,
                        )
                    )
            except Exception as e:
                logger.warning(f"GitHub VC list fetch failed ({url}): {e}")
    logger.info(f"Loaded {len(records)} records from GitHub lists")
    return records


async def load_public_investors() -> list[InvestorRecord]:
    """Returns merged public investor list, using disk cache if fresh."""
    cached = _load_from_cache()
    if cached:
        logger.info(f"Loaded {len(cached)} investors from cache")
        return cached

    openvc = await _fetch_openvc()
    github = await _fetch_github_lists()
    all_records = openvc + github
    _save_to_cache(all_records)
    logger.info(f"Fetched {len(all_records)} total public investors")
    return all_records

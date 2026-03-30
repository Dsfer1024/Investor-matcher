"""In-memory cache for public investor data, populated at startup."""
from app.models.investor import InvestorRecord

_public_investors: list[InvestorRecord] = []


def set_public_investors(records: list[InvestorRecord]) -> None:
    global _public_investors
    _public_investors = records


def get_public_investors() -> list[InvestorRecord]:
    return _public_investors

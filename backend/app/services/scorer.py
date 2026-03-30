"""Thin wrapper — sorting logic only. Generation is done via streaming in the router."""
from app.models.investor import InvestorRecord


def sort_by_tier_and_score(investors: list[InvestorRecord]) -> list[InvestorRecord]:
    return sorted(
        investors,
        key=lambda x: (x.tier or 3, -(x.fit_score or 0), -(x.prestige_score or 0)),
    )

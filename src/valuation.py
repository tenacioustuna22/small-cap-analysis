"""Market value, enterprise value and multiples today. Pure functions.

Scenarios (what the business could be worth in a few years) live in scenarios.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from src.estimates import ForwardEstimate
from src.metrics import Fact


@dataclass
class Valuation:
    price: float | None = None
    price_day: date | None = None
    shares: Fact | None = None
    shares_basis: str = ""
    potential_shares: float | None = None
    liquidity: float | None = None  # cash and short-term investments
    debt: float | None = None  # None when no debt is tagged; treated as zero with a note
    revenue_ttm: float | None = None
    gross_profit_ttm: float | None = None
    equity: Fact | None = None
    notes: list[str] = field(default_factory=list)
    forward: ForwardEstimate | None = None  # next year's analyst revenue consensus

    @property
    def ev_forward_sales(self) -> float | None:
        return _ratio(self.enterprise_value, self.forward.average if self.forward else None)

    @property
    def market_cap(self) -> float | None:
        if self.price is None or self.shares is None:
            return None
        return self.price * self.shares.val

    @property
    def diluted_market_cap(self) -> float | None:
        if self.market_cap is None or self.potential_shares is None:
            return None
        return self.price * (self.shares.val + self.potential_shares)

    @property
    def enterprise_value(self) -> float | None:
        if self.market_cap is None or self.liquidity is None:
            return None
        return self.market_cap + (self.debt or 0.0) - self.liquidity

    @property
    def ev_sales(self) -> float | None:
        return _ratio(self.enterprise_value, self.revenue_ttm)

    @property
    def ev_gross_profit(self) -> float | None:
        return _ratio(self.enterprise_value, self.gross_profit_ttm)

    @property
    def price_book(self) -> float | None:
        return _ratio(self.market_cap, self.equity.val if self.equity else None)


def _ratio(top: float | None, bottom: float | None) -> float | None:
    if top is None or bottom is None or bottom <= 0:
        return None
    return top / bottom


def compute_valuation(
    price: float | None,
    price_day: date | None,
    shares: Fact | None,
    shares_basis: str,
    potential_shares: float | None,
    liquidity: float | None,
    debt: float | None,
    revenue_ttm: float | None,
    gross_profit_ttm: float | None,
    equity: Fact | None,
    forward: ForwardEstimate | None = None,
) -> Valuation:
    v = Valuation(price, price_day, shares, shares_basis, potential_shares, liquidity, debt,
                  revenue_ttm, gross_profit_ttm, equity, forward=forward)
    if forward is not None:
        v.notes.extend(forward.notes)
    if price is None:
        v.notes.append("no price, so no market value")
    if shares is not None and shares_basis != "cover page":
        v.notes.append(
            f"market value uses the {shares_basis} share count ({shares.end}), not a current figure; "
            "shares issued since then are missing"
        )
    if debt is None:
        v.notes.append("no debt is tagged, so enterprise value assumes none")
    if potential_shares:
        v.notes.append("fully diluted value counts every option and warrant, including ones far out of the money")
    if v.enterprise_value is not None and v.enterprise_value < 0:
        v.notes.append("enterprise value is negative: the market values the business below its net cash")
    return v

"""Bear, base and bull scenarios at several horizons, by revenue stream. Pure functions.

Assumptions live in assumptions.toml, one table per ticker (see the example there). A
ticker without an entry gets mechanical placeholders that the report labels as such.

Each case gives every stream a revenue path, either a starting point and growth rates or
an explicit yearly path (for lumpy contract revenue), and an exit EV/sales multiple. A
multiple of 0 means the stream is worth only the cash it brings in along the way. Cash
burn falls in a straight line to zero by the breakeven year; cash needed beyond today's
balance is raised by selling shares at a discount to today's price. Nothing is discounted
back to today: the annualized return is the way to compare horizons.
"""
from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from src.valuation import Valuation

ROOT = Path(__file__).resolve().parents[1]
ASSUMPTIONS_PATH = ROOT / "assumptions.toml"
CASES = ("bear", "base", "bull")
START_KINDS = ("ttm", "ytd_annualized", "run_rate")
START_LABELS = {"ttm": "last four quarters", "ytd_annualized": "year to date, annualized",
                "run_rate": "latest quarter × 4", "given": "set in assumptions.toml"}
EARLY_YEARS = 3  # growth_pct applies to years 1-3, late_growth_pct after
DEFAULT_HORIZONS = (3, 5)
WHOLE = "Total"  # stream name when a ticker is modelled as one business
GROWTH_CAP = 50.0  # placeholder growth never exceeds this, whatever the trailing rate

TICKER_KEYS = {"horizons", "split", "caveats"}
CASE_KEYS = {"breakeven_years", "annual_burn", "raise_discount_pct", "note", "sources", "streams"}
STREAM_KEYS = {"start", "growth_pct", "late_growth_pct", "revenue_by_year", "ev_sales", "note"}


class AssumptionError(ValueError):
    pass


@dataclass(frozen=True)
class StreamAssumption:
    name: str
    ev_sales: float
    start: tuple[str | float, ...] = ()  # start kinds to try in order, or a number in $M
    growth_pct: float | None = None
    late_growth_pct: float | None = None
    revenue_by_year: tuple[float, ...] = ()  # dollars, year 1 first
    note: str = ""

    def revenue_in(self, year: int, start_value: float | None) -> float:
        if self.revenue_by_year:
            return self.revenue_by_year[year - 1]
        early, late = self.growth_pct or 0.0, self.late_growth_pct if self.late_growth_pct is not None else self.growth_pct or 0.0
        return start_value * (1 + early / 100) ** min(year, EARLY_YEARS) * (1 + late / 100) ** max(0, year - EARLY_YEARS)


@dataclass(frozen=True)
class CaseAssumption:
    case: str
    breakeven_years: float  # inf = burn never stops
    streams: tuple[StreamAssumption, ...]
    raise_discount_pct: float = 0.0
    note: str = ""
    sources: tuple[str, ...] = ()
    placeholder: bool = False
    annual_burn: float | None = None  # dollars a year at the start; None = the four-quarter average


@dataclass(frozen=True)
class TickerAssumptions:
    ticker: str
    cases: tuple[CaseAssumption, ...]
    horizons: tuple[int, ...] = DEFAULT_HORIZONS
    split: str = ""  # title of the revenue split the streams come from; "" = whole company
    caveats: tuple[str, ...] = ()  # model limits that change how to read the figures, shown above them

    @property
    def placeholder(self) -> bool:
        return any(c.placeholder for c in self.cases)


# --- loading ------------------------------------------------------------------------

def _check_keys(table: dict, allowed: set[str], where: str) -> None:
    unknown = sorted(set(table) - allowed)
    if unknown:
        raise AssumptionError(f"{where}: unknown key{'s' if len(unknown) > 1 else ''} {', '.join(unknown)}; "
                              f"allowed: {', '.join(sorted(allowed))}")


def _number(value, where: str, key: str, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AssumptionError(f"{where}: {key} must be a number, got {value!r}")
    if minimum is not None and value < minimum:
        raise AssumptionError(f"{where}: {key} must be at least {minimum:g}, got {value!r}")
    return float(value)


def _stream(name: str, table: dict, where: str, longest: int) -> StreamAssumption:
    _check_keys(table, STREAM_KEYS, where)
    if "ev_sales" not in table:
        raise AssumptionError(f"{where}: ev_sales is required (0 means no exit value)")
    ev_sales = _number(table["ev_sales"], where, "ev_sales", minimum=0)
    note = str(table.get("note", ""))
    path = table.get("revenue_by_year")
    if path is not None:
        if {"start", "growth_pct", "late_growth_pct"} & set(table):
            raise AssumptionError(f"{where}: revenue_by_year replaces start and growth; give one or the other")
        if not isinstance(path, list) or not path:
            raise AssumptionError(f"{where}: revenue_by_year must be a non-empty list of $M per year")
        if len(path) < longest:
            raise AssumptionError(f"{where}: revenue_by_year has {len(path)} years but the longest horizon is {longest}")
        values = tuple(_number(v, where, "revenue_by_year", minimum=0) * 1e6 for v in path)
        return StreamAssumption(name, ev_sales, revenue_by_year=values, note=note)

    if "growth_pct" not in table:
        raise AssumptionError(f"{where}: give growth_pct (with start) or revenue_by_year")
    raw = table.get("start", ["ttm"])
    raw = raw if isinstance(raw, list) else [raw]
    start: list[str | float] = []
    for item in raw:
        if isinstance(item, str):
            if item not in START_KINDS:
                raise AssumptionError(f"{where}: start {item!r} is not one of {', '.join(START_KINDS)} or a number in $M")
            start.append(item)
        else:
            start.append(_number(item, where, "start", minimum=0) * 1e6)
    late = table.get("late_growth_pct")
    return StreamAssumption(
        name, ev_sales, tuple(start),
        growth_pct=_number(table["growth_pct"], where, "growth_pct", minimum=-100),
        late_growth_pct=_number(late, where, "late_growth_pct", minimum=-100) if late is not None else None,
        note=note,
    )


def _case(ticker: str, case: str, table: dict, split: str, longest: int) -> CaseAssumption:
    where = f"[{ticker}.{case}]"
    if split:
        _check_keys(table, CASE_KEYS, where)
        streams_table = table.get("streams")
        if not isinstance(streams_table, dict) or not streams_table:
            raise AssumptionError(f"{where}: split is {split!r}, so give one [{ticker}.{case}.streams.<name>] table per stream")
        streams = tuple(_stream(name, body, f"[{ticker}.{case}.streams.{name}]", longest)
                        for name, body in streams_table.items())
    else:
        _check_keys(table, (CASE_KEYS - {"streams"}) | STREAM_KEYS, where)
        whole = {k: v for k, v in table.items() if k in STREAM_KEYS and k != "note"}
        streams = (_stream(WHOLE, whole, where, longest),)
    breakeven = table.get("breakeven_years", "never")
    if isinstance(breakeven, str):
        if breakeven.lower() != "never":
            raise AssumptionError(f"{where}: breakeven_years must be a number of years or \"never\"")
        breakeven_years = math.inf
    else:
        breakeven_years = _number(breakeven, where, "breakeven_years", minimum=0)
    discount = _number(table.get("raise_discount_pct", 0), where, "raise_discount_pct", minimum=0)
    if discount >= 100:
        raise AssumptionError(f"{where}: raise_discount_pct must be below 100")
    sources = table.get("sources", [])
    if not isinstance(sources, list) or not all(isinstance(s, str) for s in sources):
        raise AssumptionError(f"{where}: sources must be a list of links")
    burn = table.get("annual_burn")
    annual_burn = _number(burn, where, "annual_burn", minimum=0) * 1e6 if burn is not None else None
    return CaseAssumption(case, breakeven_years, streams, discount, str(table.get("note", "")), tuple(sources),
                          annual_burn=annual_burn)


def parse_assumptions(ticker: str, data: dict) -> TickerAssumptions | None:
    """One ticker's entry from parsed TOML, validated. None when the ticker has no entry."""
    entry = next((v for k, v in data.items() if k.upper() == ticker.upper()), None)
    if entry is None:
        return None
    where = f"[{ticker}]"
    cases = {k: v for k, v in entry.items() if isinstance(v, dict)}
    _check_keys({k: v for k, v in entry.items() if k not in cases}, TICKER_KEYS, where)
    unknown = sorted(set(cases) - set(CASES))
    if unknown:
        raise AssumptionError(f"{where}: unknown case {', '.join(unknown)}; use {', '.join(CASES)}")
    missing = [c for c in CASES if c not in cases]
    if missing:
        raise AssumptionError(f"{where}: missing case {', '.join(missing)}")
    horizons = entry.get("horizons", list(DEFAULT_HORIZONS))
    if not isinstance(horizons, list) or not horizons or not all(isinstance(h, int) and h > 0 for h in horizons):
        raise AssumptionError(f"{where}: horizons must be a list of whole years, such as [3, 5]")
    split = str(entry.get("split", ""))
    caveats = entry.get("caveats", [])
    if not isinstance(caveats, list) or not all(isinstance(c, str) and c.strip() for c in caveats):
        raise AssumptionError(f"{where}: caveats must be a list of sentences")
    parsed = tuple(_case(ticker, c, cases[c], split, max(horizons)) for c in CASES)
    names = [tuple(s.name for s in c.streams) for c in parsed]
    if len(set(names)) > 1:
        raise AssumptionError(f"{where}: every case must name the same streams; got {names}")
    return TickerAssumptions(ticker.upper(), parsed, tuple(sorted(horizons)), split,
                             tuple(c.strip() for c in caveats))


def check_streams(a: TickerAssumptions, available: list[str]) -> None:
    """Every stream of the split needs assumptions, and every assumed stream must exist."""
    named = {s.name for s in a.cases[0].streams}
    missing, extra = sorted(set(available) - named), sorted(named - set(available))
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"no assumptions for {', '.join(missing)}")
        if extra:
            parts.append(f"{', '.join(extra)} is not a stream of {a.split!r}")
        raise AssumptionError(f"[{a.ticker}]: " + "; ".join(parts) + f" (streams: {', '.join(available)})")


def load_assumptions(ticker: str, path: Path = ASSUMPTIONS_PATH) -> TickerAssumptions | None:
    if not path.exists():
        return None
    with path.open("rb") as handle:
        try:
            data = tomllib.load(handle)
        except tomllib.TOMLDecodeError as error:
            raise AssumptionError(f"{path.name}: {error}") from error
    return parse_assumptions(ticker, data)


def placeholder_assumptions(v: Valuation, growth_ttm: float | None) -> TickerAssumptions | None:
    """Mechanical bear/base/bull cases from trailing figures, until real ones are written."""
    if v.ev_sales is None or growth_ttm is None:
        return None
    base = max(-20.0, min(GROWTH_CAP, growth_ttm))
    start = ("ttm",)
    return TickerAssumptions("", (
        CaseAssumption("bear", math.inf, (StreamAssumption(WHOLE, v.ev_sales * 0.5, start, base / 2),),
                       note="half the growth, half the multiple, burn never stops", placeholder=True),
        CaseAssumption("base", EARLY_YEARS, (StreamAssumption(WHOLE, v.ev_sales, start, base),),
                       note="trailing growth (capped), today's multiple, breakeven in year 3", placeholder=True),
        CaseAssumption("bull", EARLY_YEARS / 2,
                       (StreamAssumption(WHOLE, v.ev_sales, start, min(GROWTH_CAP * 1.5, base * 1.5)),),
                       note="1.5x growth at today's multiple, breakeven halfway to year 3", placeholder=True),
    ))


# --- running ------------------------------------------------------------------------

@dataclass(frozen=True)
class StreamResult:
    name: str
    start_label: str  # which starting point was used
    start_value: float | None  # None for an explicit yearly path
    revenue: float  # in the horizon year
    ev_sales: float
    enterprise_value: float


@dataclass(frozen=True)
class Scenario:
    case: CaseAssumption
    years: int
    streams: tuple[StreamResult, ...]
    cash_burned: float
    raised: float  # equity sold to cover burn beyond today's cash
    raise_price: float
    new_shares: float
    net_cash: float  # cash minus debt at the end
    per_share: float  # never below zero: shareholders cannot lose more than everything
    change_pct: float  # against today's price, not discounted
    annual_return_pct: float
    annual_burn: float = 0.0  # burn a year at the start, as used

    @property
    def revenue(self) -> float:
        return sum(s.revenue for s in self.streams)

    @property
    def enterprise_value(self) -> float:
        return sum(s.enterprise_value for s in self.streams)

    @property
    def implied_ev_sales(self) -> float | None:
        return self.enterprise_value / self.revenue if self.revenue else None


def cumulative_burn(annual_burn: float, years: float, breakeven_years: float) -> float:
    """Cash burned over `years` when burn falls in a straight line to zero at `breakeven_years`."""
    if annual_burn <= 0:
        return 0.0
    if math.isinf(breakeven_years):
        return annual_burn * years
    if breakeven_years <= years:
        return annual_burn * breakeven_years / 2
    return annual_burn * (years - years**2 / (2 * breakeven_years))


def resolve_start(s: StreamAssumption, available: dict[str, float]) -> tuple[str, float]:
    """The first starting point in the stream's list that the data can supply."""
    for option in s.start:
        if isinstance(option, float):
            return "given", option
        if option in available:
            return option, available[option]
    wanted = ", ".join(str(o) for o in s.start)
    have = ", ".join(sorted(available)) or "none"
    raise AssumptionError(f"stream {s.name!r}: no starting revenue for {wanted} (available: {have})")


def run_case(case: CaseAssumption, years: int, v: Valuation, annual_burn: float,
             starts: dict[str, dict[str, float]]) -> Scenario | None:
    """`starts` maps each stream name to its available starting points (see metrics.start_values).
    `annual_burn` is the default; a case's own `annual_burn` replaces it."""
    if v.price is None or v.shares is None or v.liquidity is None:
        return None
    if case.annual_burn is not None:
        annual_burn = case.annual_burn
    results = []
    for s in case.streams:
        if s.revenue_by_year:
            label, start = "yearly path", None
        else:
            label, start = resolve_start(s, starts.get(s.name, {}))
        revenue = s.revenue_in(years, start)
        results.append(StreamResult(s.name, START_LABELS.get(label, label), start, revenue, s.ev_sales, revenue * s.ev_sales))
    burned = cumulative_burn(annual_burn, years, case.breakeven_years)
    raised = max(0.0, burned - v.liquidity)
    raise_price = v.price * (1 - case.raise_discount_pct / 100)
    new_shares = raised / raise_price if raise_price > 0 else 0.0
    net_cash = v.liquidity + raised - burned - (v.debt or 0.0)
    ev = sum(r.enterprise_value for r in results)
    per_share = max(0.0, (ev + net_cash) / (v.shares.val + new_shares))
    ratio = per_share / v.price
    annual = (ratio ** (1 / years) - 1) * 100 if ratio > 0 else -100.0
    return Scenario(case, years, tuple(results), burned, raised, raise_price, new_shares, net_cash,
                    per_share, (ratio - 1) * 100, annual, annual_burn)


def run_all(a: TickerAssumptions, v: Valuation, annual_burn: float,
            starts: dict[str, dict[str, float]]) -> list[Scenario]:
    """Every case at every horizon, bear to bull, shortest horizon first within a case."""
    return [s for case in a.cases for years in a.horizons
            if (s := run_case(case, years, v, annual_burn, starts)) is not None]

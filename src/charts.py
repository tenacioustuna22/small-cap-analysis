"""Charts as responsive HTML and CSS, with a small SVG for lines. Pure functions.

Styling lives in src/assets/report.css. Every value shown on hover is also available
in a label or a table next to the chart.
"""
from __future__ import annotations

import calendar
import math
from dataclasses import dataclass
from datetime import date, timedelta
from html import escape

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def add_months(start: date, months: float) -> date:
    """Calendar months for the whole part, average-length days for the fraction."""
    whole = math.floor(months)
    index = start.year * 12 + (start.month - 1) + whole
    year, month = divmod(index, 12)
    month += 1
    last_day = calendar.monthrange(year, month)[1]
    moved = date(year, month, min(start.day, last_day))
    return moved + timedelta(days=round((months - whole) * 30.44))


def month_year(day: date) -> str:
    return f"{MONTHS[day.month - 1]} {day.year}"


def nice_ticks(low: float, high: float, target: int = 4) -> list[float]:
    """Round axis values that cover low..high in roughly `target` steps."""
    if high <= low:
        high = low + 1
    raw = (high - low) / target
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw - 1e-12)
    first = math.floor(low / step + 1e-9)
    last = math.ceil(high / step - 1e-9)
    return [round(i * step, 10) for i in range(first, last + 1)]


def _tick_label(value: float, prefix: str, suffix: str) -> str:
    return f"{'-' if value < 0 else ''}{prefix}{abs(value):g}{suffix}"


def _tip(head: str, value: str, detail: str) -> str:
    return f'tabindex="0" data-tip="{escape(head)}|{escape(value)}|{escape(detail)}"'


def _caption(title: str, subtitle: str) -> str:
    sub = f"<span>{escape(subtitle)}</span>" if subtitle else ""
    return f"<figcaption><strong>{escape(title)}</strong>{sub}</figcaption>"


def _y_axis(ticks: list[float], position, prefix: str, suffix: str) -> tuple[str, str]:
    labels = "".join(
        f'<span style="top:{position(t):.2f}%">{_tick_label(t, prefix, suffix)}</span>' for t in ticks
    )
    lines = "".join(
        f'<i class="gridline{" zero" if t == 0 else ""}" style="top:{position(t):.2f}%"></i>'
        for t in ticks
    )
    return f'<div class="yaxis">{labels}</div>', lines


# --- runway strip -------------------------------------------------------------------

@dataclass(frozen=True)
class StripRow:
    name: str  # row label, "" for a single unlabeled row
    href: str  # optional link for the name
    start: date  # balance sheet date the cash was counted on
    low: float | None  # months of cash at the faster burn; inf = not burning; None = unknown
    high: float | None  # months of cash at the slower burn
    text: str  # sentence shown above the bar, "" for none


def fit_horizon(rows: list[StripRow], minimum: int = 36, maximum: int = 180) -> int:
    """Whole years of timeline that show every finite runway in full, within limits."""
    longest = max(
        (row.high for row in rows if row.high is not None and not math.isinf(row.high)), default=0
    )
    return max(minimum, min(maximum, math.ceil(longest / 12 + 0.25) * 12))


def runway_strip(rows: list[StripRow], today: date, horizon_months: int = 36) -> str:
    """A calendar timeline per row: how far the cash reaches at two burn rates."""
    if not rows:
        return ""
    origin = min(row.start for row in rows)
    end = add_months(origin, horizon_months)
    span = (end - origin).days

    def pct(day: date) -> float:
        return max(0.0, min(100.0, (day - origin).days / span * 100))

    def reach(row: StripRow, months: float) -> float:
        return 100.0 if math.isinf(months) else pct(add_months(row.start, months))

    years = [date(y, 1, 1) for y in range(origin.year + 1, end.year + 1) if date(y, 1, 1) <= end]
    label_every = 1 if len(years) <= 8 else 2
    grid = "".join(f'<i style="left:{pct(y):.2f}%"></i>' for y in years)
    if origin <= today <= end:
        grid += f'<i class="today" style="left:{pct(today):.2f}%"><span>today</span></i>'
    axis = "".join(
        f'<span style="left:{pct(y):.2f}%">{y.year}</span>'
        for i, y in enumerate(years)
        if (len(years) - 1 - i) % label_every == 0
    )

    body = []
    any_solid = any_pale = clipped = False
    for row in rows:
        fills = ""
        if row.low is not None and row.high is not None:
            x0, x_low, x_high = pct(row.start), reach(row, row.low), reach(row, row.high)
            has_pale = x_high - x_low > 0.3
            any_solid = True
            any_pale = any_pale or has_pale
            clipped = clipped or x_high >= 100
            runs_out = "does not run out" if math.isinf(row.low) else month_year(add_months(row.start, row.low))
            solid_end = " end" if not has_pale and x_low < 100 else ""
            fills += (
                f'<span class="fill solid{solid_end}" style="left:{x0:.2f}%;width:{x_low - x0:.2f}%" '
                f'{_tip("Cash lasts at both burn rates", f"to {runs_out}", row.name)}></span>'
            )
            if has_pale:
                later = "beyond the chart" if math.isinf(row.high) else month_year(add_months(row.start, row.high))
                pale_end = " end" if x_high < 100 else ""
                fills += (
                    f'<span class="fill pale{pale_end}" '
                    f'style="left:calc({x_low:.2f}% + 2px);width:calc({x_high - x_low:.2f}% - 2px)" '
                    f'{_tip("Only at the lower burn rate", f"to {later}", row.name)}></span>'
                )
        name = escape(row.name)
        if row.href:
            name = f'<a href="{escape(row.href)}">{name}</a>'
        text = f'<p class="strip-text"><span>{escape(row.text)}</span></p>' if row.text else ""
        body.append(
            f'<div class="strip-row"><div class="strip-name">{name}</div>'
            f'<div class="strip-main">{text}<div class="track">{fills}</div></div></div>'
        )

    named = " named" if any(row.name for row in rows) else ""
    legend = ""
    if any_solid:
        legend += '<span><i class="sw solid"></i>Cash lasts at both recent burn rates</span>'
    if any_pale:
        legend += '<span><i class="sw pale"></i>Only at the lower burn rate</span>'
    foot = f"Timeline starts at the balance sheet date, {origin}, and shows {horizon_months // 12} years."
    if clipped:
        foot += " A bar that reaches the right edge continues past it."
    return (
        '<figure class="chart strip">'
        f'<div class="legend">{legend}</div>'
        f'<div class="strip-body{named}"><div class="strip-grid">{grid}</div>'
        f'{"".join(body)}<div class="strip-axis">{axis}</div></div>'
        f'<p class="chart-foot">{foot}</p>'
        "</figure>"
    )


# --- column chart -------------------------------------------------------------------

@dataclass(frozen=True)
class Column:
    top: str  # x-axis label, first line
    bottom: str  # x-axis label, second line
    value: float  # in display units
    tip_head: str
    tip_value: str
    tip_detail: str
    label: str = ""  # value printed at the bar end; leave empty on most bars


def column_chart(title: str, subtitle: str, columns: list[Column], prefix: str = "$", suffix: str = "M") -> str:
    """Columns from a zero baseline; negative values hang below it."""
    if not columns:
        return ""
    values = [c.value for c in columns]
    ticks = nice_ticks(min(0.0, min(values)) * 1.18, max(0.0, max(values)) * 1.18)
    low, high = ticks[0], ticks[-1]

    def y(value: float) -> float:
        return (high - value) / (high - low) * 100

    y_axis, gridlines = _y_axis(ticks, y, prefix, suffix)
    zero = y(0)
    cols, labels = [], []
    for column in columns:
        end = y(column.value)
        bar = value_label = ""
        if column.value < 0:
            bar = f'<b class="bar neg" style="top:{zero:.2f}%;height:{end - zero:.2f}%"></b>'
            place = f"top:calc({end:.2f}% + 4px)"
        elif column.value > 0:
            bar = f'<b class="bar pos" style="top:{end:.2f}%;height:{zero - end:.2f}%"></b>'
            place = f"bottom:calc({100 - end:.2f}% + 4px)"
        else:
            place = f"bottom:calc({100 - zero:.2f}% + 4px)"
        if column.label:
            value_label = f'<span class="val" style="{place}">{escape(column.label)}</span>'
        cols.append(
            f'<div class="col" {_tip(column.tip_head, column.tip_value, column.tip_detail)}>'
            f"{bar}{value_label}</div>"
        )
        labels.append(f"<span>{escape(column.top)}<br>{escape(column.bottom)}</span>")

    return (
        f'<figure class="chart">{_caption(title, subtitle)}'
        f'<div class="plot">{y_axis}<div class="area">{gridlines}'
        f'<div class="cols">{"".join(cols)}</div></div></div>'
        f'<div class="xaxis">{"".join(labels)}</div></figure>'
    )


@dataclass(frozen=True)
class Stack:
    top: str  # x-axis label, first line
    bottom: str  # x-axis label, second line
    parts: list[float]  # one non-negative value per series, in display units, bottom first
    tip_head: str
    tip_value: str
    tip_detail: str
    label: str = ""  # total printed above the stack; leave empty on most


STACK_COLOURS = 3  # categorical slots defined in report.css (.c1 to .c3)


def stacked_column_chart(
    title: str, subtitle: str, series: list[str], stacks: list[Stack], prefix: str = "$", suffix: str = "M"
) -> str:
    """Columns split into up to three series, the first at the baseline. The legend keeps
    the stacking order (bottom series first) and colours follow the series, never the rank."""
    if len(series) > STACK_COLOURS:
        raise ValueError(f"at most {STACK_COLOURS} series can be stacked")
    if not stacks or not series:
        return ""
    if any(len(s.parts) != len(series) or min(s.parts) < 0 for s in stacks):
        raise ValueError("every stack needs one non-negative value per series")
    ticks = nice_ticks(0.0, max(sum(s.parts) for s in stacks) * 1.18)
    high = ticks[-1]

    def y(value: float) -> float:
        return (high - value) / high * 100

    y_axis, gridlines = _y_axis(ticks, y, prefix, suffix)
    cols, labels = [], []
    for stack in stacks:
        segments, base = [], 0.0
        drawn = [i for i, v in enumerate(stack.parts) if v > 0]
        for i, value in enumerate(stack.parts):
            if value <= 0:
                continue
            classes = f"bar seg c{i + 1}" + (" topmost" if i == drawn[-1] else "") + (" lowest" if i == drawn[0] else "")
            segments.append(
                f'<b class="{classes}" style="top:{y(base + value):.2f}%;height:{y(base) - y(base + value):.2f}%"></b>'
            )
            base += value
        segments.reverse()  # the top segment first: the readout anchors on the first bar
        label = ""
        if stack.label:
            label = f'<span class="val" style="bottom:calc({100 - y(base):.2f}% + 4px)">{escape(stack.label)}</span>'
        cols.append(
            f'<div class="col" {_tip(stack.tip_head, stack.tip_value, stack.tip_detail)}>{"".join(segments)}{label}</div>'
        )
        labels.append(f"<span>{escape(stack.top)}<br>{escape(stack.bottom)}</span>")
    key = "".join(f'<span><i class="sw c{i + 1}"></i>{escape(name)}</span>' for i, name in enumerate(series))
    return (
        f'<figure class="chart">{_caption(title, subtitle)}<div class="legend">{key}</div>'
        f'<div class="plot">{y_axis}<div class="area">{gridlines}'
        f'<div class="cols">{"".join(cols)}</div></div></div>'
        f'<div class="xaxis">{"".join(labels)}</div></figure>'
    )


# --- value range --------------------------------------------------------------------

@dataclass(frozen=True)
class RangeMark:
    value: float  # in display units
    marker: int  # index into the chart's marker legend (0 = hollow, 1 = filled)
    tip_head: str
    tip_value: str
    tip_detail: str


MARKERS = ("ring", "disc")


def range_chart(
    title: str,
    subtitle: str,
    rows: list[tuple[str, list[RangeMark]]],
    marker_labels: list[str],
    reference: tuple[str, float],
    prefix: str = "$",
    suffix: str = "",
) -> str:
    """One labelled track per row with its marks on a shared horizontal axis, and a dashed
    reference line (today's price, say). Marker shape, not colour, tells the marks apart."""
    if not rows or not marker_labels:
        return ""
    if len(marker_labels) > len(MARKERS):
        raise ValueError(f"at most {len(MARKERS)} marker kinds")
    values = [m.value for _, marks in rows for m in marks] + [reference[1]]
    ticks = nice_ticks(0.0, max(values) * 1.1)
    high = ticks[-1] or 1.0

    def x(value: float) -> float:
        return max(0.0, min(100.0, value / high * 100))

    axis = "".join(f'<span style="left:{x(t):.2f}%">{_tick_label(t, prefix, suffix)}</span>' for t in ticks)
    grid = "".join(f'<i class="vgrid" style="left:{x(t):.2f}%"></i>' for t in ticks)
    ref = (f'<i class="range-ref" style="left:{x(reference[1]):.2f}%"></i>')
    tracks = []
    for label, marks in rows:
        dots = "".join(
            f'<span class="mark {MARKERS[m.marker]}" style="left:{x(m.value):.2f}%" '
            f"{_tip(m.tip_head, m.tip_value, m.tip_detail)}></span>"
            for m in marks
        )
        tracks.append(f'<div class="track"><span class="track-label">{escape(label)}</span>'
                      f'<div class="track-line">{grid}{ref}{dots}</div></div>')
    key = "".join(f'<span><i class="sw mark-key {MARKERS[i]}"></i>{escape(name)}</span>'
                  for i, name in enumerate(marker_labels))
    key += f'<span><i class="sw ref dashed"></i>{escape(reference[0])}</span>'
    return (
        f'<figure class="chart range">{_caption(title, subtitle)}<div class="legend">{key}</div>'
        f'{"".join(tracks)}<div class="range-axis">{axis}</div></figure>'
    )


# --- line chart ---------------------------------------------------------------------

@dataclass(frozen=True)
class Point:
    when: date
    value: float  # in display units
    tip_head: str
    tip_value: str
    tip_detail: str


@dataclass(frozen=True)
class Reference:
    """A neutral line on a line chart's axis, such as a moving average."""
    label: str
    points: list[tuple[date, float]]
    style: str = "dashed"  # "dashed" or "solid" (lighter grey); two lines need different styles


REFERENCE_STYLES = ("dashed", "solid")
DENSE_POINTS = 60  # above this, hover works on vertical slices instead of dots


def _date_axis(first_day: date, last_day: date, x) -> str:
    """Year labels for long spans; quarter-start month labels for spans under 20 months."""
    if (last_day - first_day).days >= 600:
        marks = [(date(yr, 1, 1), str(yr)) for yr in range(first_day.year + 1, last_day.year + 1)]
    else:
        marks = []
        for index in range(first_day.year * 12 + first_day.month, last_day.year * 12 + last_day.month):
            year, month = divmod(index, 12)
            if month % 3 == 0:  # Jan, Apr, Jul, Oct
                label = f"{MONTHS[month]} {year}" if month == 0 else MONTHS[month]
                marks.append((date(year, month + 1, 1), label))
    return "".join(f'<span style="left:{x(d):.2f}%">{text}</span>' for d, text in marks)


def line_chart(
    title: str,
    subtitle: str,
    points: list[Point],
    prefix: str = "",
    suffix: str = "M",
    *,
    references: list[Reference] | None = None,
    series_label: str = "",
    zero_based: bool = True,
) -> str:
    """One series over time with the first and last values labelled.

    `references` adds neutral lines (moving averages, say) on the same axis, drawn only
    within the main series' dates. With references, a legend names the series as
    `series_label` and each reference by its label. `zero_based=False` fits the axis to
    the data, for prices.
    """
    if not points:
        return ""
    points = sorted(points, key=lambda p: p.when)
    first_day, last_day = points[0].when, points[-1].when
    lines = []
    for ref in references or []:
        if ref.style not in REFERENCE_STYLES:
            raise ValueError(f"unknown reference style {ref.style!r}")
        kept = sorted((d, v) for d, v in ref.points if first_day <= d <= last_day)
        if kept:
            lines.append((ref, kept))
    values = [p.value for p in points] + [v for _, kept in lines for _, v in kept]
    if zero_based:
        ticks = nice_ticks(min(0.0, min(values) * 1.2), max(0.0, max(values)) * 1.2)
    else:
        lo, hi = min(values), max(values)
        pad = (hi - lo) * 0.08 or abs(hi) * 0.1 or 1
        ticks = nice_ticks(lo - pad, hi + pad)
    low, high = ticks[0], ticks[-1]
    span = (last_day - first_day).days

    def x(day: date) -> float:
        return 50.0 if span == 0 else (day - first_day).days / span * 100

    def y(value: float) -> float:
        return (high - value) / (high - low) * 100

    y_axis, gridlines = _y_axis(ticks, y, prefix, suffix)
    coords = [(x(p.when), y(p.value)) for p in points]
    path = " ".join(f"{px:.2f},{py:.2f}" for px, py in coords)
    svg = ""
    if low == 0:
        svg += f'<polygon class="line-wash" points="{path} {coords[-1][0]:.2f},100 {coords[0][0]:.2f},100"/>'
    for ref, kept in lines:
        ref_path = " ".join(f"{x(d):.2f},{y(v):.2f}" for d, v in kept)
        svg += f'<polyline class="line-ref {ref.style}" points="{ref_path}"/>'
    svg += f'<polyline class="line-path" points="{path}"/>'

    if len(points) <= DENSE_POINTS:
        marks = "".join(
            f'<span class="dot" style="left:{px:.2f}%;top:{py:.2f}%" '
            f"{_tip(p.tip_head, p.tip_value, p.tip_detail)}></span>"
            for p, (px, py) in zip(points, coords)
        )
    else:
        # Each point owns the strip of plot between the midpoints to its neighbours.
        edges = [0.0] + [(a[0] + b[0]) / 2 for a, b in zip(coords, coords[1:])] + [100.0]
        marks = "".join(
            f'<span class="slice" style="left:{edges[i]:.3f}%;width:{edges[i + 1] - edges[i]:.3f}%" '
            f'data-tip="{escape(p.tip_head)}|{escape(p.tip_value)}|{escape(p.tip_detail)}">'
            f'<i style="left:{(px - edges[i]) / max(edges[i + 1] - edges[i], 1e-9) * 100:.1f}%;top:{py:.2f}%"></i></span>'
            for i, (p, (px, py)) in enumerate(zip(points, coords))
        )
    labels = f'<span class="pt-label last" style="top:calc({coords[-1][1]:.2f}% - 10px)">{escape(points[-1].tip_value)}</span>'
    if len(points) > 1:
        labels += f'<span class="pt-label first" style="top:calc({coords[0][1]:.2f}% - 10px)">{escape(points[0].tip_value)}</span>'
    key = ""
    if lines:
        key = (
            f'<div class="legend"><span><i class="sw line"></i>{escape(series_label)}</span>'
            + "".join(f'<span><i class="sw ref {ref.style}"></i>{escape(ref.label)}</span>' for ref, _ in lines)
            + "</div>"
        )

    return (
        f'<figure class="chart">{_caption(title, subtitle)}{key}'
        f'<div class="plot">{y_axis}<div class="area line">{gridlines}'
        f'<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">{svg}</svg>'
        f"{marks}{labels}</div></div>"
        f'<div class="xaxis dated">{_date_axis(first_day, last_day, x)}</div></figure>'
    )

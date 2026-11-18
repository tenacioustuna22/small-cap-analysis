"""Formatting and HTML building blocks shared by every report section. No network access."""
from __future__ import annotations

import html
from datetime import date
from pathlib import Path

from src.metrics import Fact

ASSETS = Path(__file__).parent / "assets"
DISCLAIMER = "Analysis of public filings and market data, not financial advice."


# --- formatting -----------------------------------------------------------------

def e(text: object) -> str:
    return html.escape(str(text), quote=True)


def usd(value: float | None) -> str:
    """Millions: $64.5M. Values of $1B or more: $1.23B."""
    if value is None:
        return "n/a"
    sign = "-" if value < 0 else ""
    if abs(value) >= 1e9:
        return f"{sign}${abs(value) / 1e9:,.2f}B"
    return f"{sign}${abs(value) / 1e6:,.1f}M"


def dollars(value: float | None) -> str:
    """Whole dollars under $1M ($6,272), millions above it."""
    if value is None:
        return "n/a"
    if abs(value) >= 1e6:
        return usd(value)
    return f"{'-' if value < 0 else ''}${abs(value):,.0f}"


def shares_text(value: float | None) -> str:
    """Whole shares under a million (7,345), millions above it."""
    if value is None:
        return "n/a"
    return share_count(value) if abs(value) >= 1e6 else f"{value:,.0f}"


def money(value: float | None) -> str:
    """A per-share amount: $4.12, or $0.679 under a dollar."""
    if value is None:
        return "n/a"
    digits = 3 if abs(value) < 1 else 2
    return f"{'-' if value < 0 else ''}${abs(value):,.{digits}f}"


def share_count(value: float | None) -> str:
    return "n/a" if value is None else f"{value / 1e6:,.1f}M"


def percent(value: float | None, signed: bool = True, digits: int = 0) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.{digits}f}%" if signed else f"{value:.{digits}f}%"


def growth(value: float | None) -> str:
    """Percent change, shown as a multiple once it reaches +200% (11.1x reads better than +1008%)."""
    if value is None:
        return "n/a"
    return f"{1 + value / 100:.1f}x" if value >= 200 else f"{value:+.0f}%"


def multiple(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f}x"


def source(fact: Fact | None) -> str:
    if fact is None:
        return ""
    period = f"quarter ended {fact.end}" if fact.start else f"as of {fact.end}"
    return f"{fact.form}, {period}, filed {fact.filed}"


def filed_in(fact: Fact | None) -> str:
    return f"{fact.form} filed {fact.filed}" if fact else ""


def quarter_label(end: date) -> tuple[str, str]:
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return months[end.month - 1], str(end.year)


# --- building blocks ---------------------------------------------------------------

def page(title: str, body: str) -> str:
    css = (ASSETS / "report.css").read_text(encoding="utf-8")
    js = (ASSETS / "report.js").read_text(encoding="utf-8")
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{e(title)}</title>\n<style>\n{css}</style>\n</head>\n<body>\n<main>\n{body}\n</main>\n"
        f'<div id="tip" class="tip" role="status" hidden></div>\n<script>\n{js}</script>\n</body>\n</html>\n'
    )


def stat(label: str, value: str, detail: str = "") -> str:
    src = f'<span class="src">{e(detail)}</span>' if detail else ""
    return f'<div class="stat"><dt>{e(label)}</dt><dd><span class="value">{e(value)}</span>{src}</dd></div>'


def stats(*items: str) -> str:
    return '<dl class="stats">' + "".join(items) + "</dl>"


def table(headers: list[tuple[str, str]], rows: list[list[str]]) -> str:
    """`headers` are (text, css class); cells are HTML that is already escaped."""
    head = "".join(f'<th class="{cls}">{e(text)}</th>' for text, cls in headers)
    body = "".join(
        "<tr>" + "".join(f'<td class="{cls}">{cell}</td>' for cell, (_, cls) in zip(row, headers)) + "</tr>"
        for row in rows
    )
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def disclosure(summary: str, content: str) -> str:
    return f"<details><summary>{e(summary)}</summary>{content}</details>"


def table_view(headers: list[tuple[str, str]], rows: list[list[str]]) -> str:
    """The table behind a chart, folded away under the chart."""
    return disclosure("Show as a table, with the source of each figure", table(headers, rows))


def notes(items: list[str]) -> str:
    return "".join(f'<p class="note"><strong>Data note.</strong> {e(item)}</p>' for item in items)


def small(text_html: str) -> str:
    return f'<p class="small">{text_html}</p>'


def section(anchor: str, eyebrow: str, headline: str, *content: str) -> str:
    return (
        f'<section class="block" id="{e(anchor)}"><p class="eyebrow">{e(eyebrow)}</p>'
        f"<h2>{e(headline)}</h2>{''.join(content)}</section>"
    )


def link(url: str, text: str) -> str:
    return f'<a href="{e(url)}">{e(text)}</a>'

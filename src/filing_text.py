"""Pull readable sentences out of filing HTML. Pure functions, no network access."""
from __future__ import annotations

import html
import re

# Sentences longer than this are almost always flattened tables, not prose.
MAX_SENTENCE_CHARS = 600

_PUNCTUATION = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", " ": " ",
})


def to_text(document_html: str) -> str:
    """Strip tags and tidy the spacing that inline XBRL markup leaves around numbers."""
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", document_html)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text).translate(_PUNCTUATION)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\$ (?=\d)", "$", text)
    text = re.sub(r"\( (?=\S)", "(", text)
    text = re.sub(r" ([,.;)])", r"\1", text)
    return text.strip()


def sentences(text: str) -> list[str]:
    """Split prose into sentences. Initials such as 'B. Riley' do not end a sentence."""
    return re.split(r"(?<=[a-z0-9)\"]\.)\s+(?=[A-Z])", text)


def matching_sentences(document_html: str, pattern: re.Pattern[str]) -> list[str]:
    """Prose sentences that match `pattern` and state a dollar amount.

    Filings repeat the same disclosure in the notes and in the discussion section,
    so sentences that quote the same set of numbers are returned once.
    """
    found: list[str] = []
    seen: set[tuple[str, ...]] = set()
    for sentence in sentences(to_text(document_html)):
        if len(sentence) > MAX_SENTENCE_CHARS or "$" not in sentence:
            continue
        if not pattern.search(sentence):
            continue
        numbers = tuple(sorted(re.findall(r"\d[\d,.]*\d|\d", sentence)))
        if numbers in seen:
            continue
        seen.add(numbers)
        found.append(sentence)
    return found

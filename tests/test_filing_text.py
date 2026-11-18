import re

from src.filing_text import matching_sentences, sentences, to_text

ATM = re.compile(r"at-the-market|sales agreement", re.IGNORECASE)


def test_to_text_strips_markup_and_tidies_numbers():
    html = (
        "<style>p{color:red}</style><p>We sold shares for <ix:nonFraction>$ </ix:nonFraction>"
        "<span>11,667</span> , net of costs&nbsp;( <b>292</b> ) under the &#8220;Sales Agreement&#8221; .</p>"
    )
    assert to_text(html) == 'We sold shares for $11,667, net of costs (292) under the "Sales Agreement".'


def test_initials_and_abbreviations_do_not_split_sentences():
    text = "We sell through B. Riley Securities under U.S. law. The program began in 2023."
    assert sentences(text) == [
        "We sell through B. Riley Securities under U.S. law.",
        "The program began in 2023.",
    ]


def test_matching_sentences_need_a_dollar_amount_and_drop_repeats():
    html = (
        "<p>The Company may sell up to $ 50.0 million under the Sales Agreement. "
        "The Sales Agreement has no fixed term. "
        "Revenue was $ 3.0 million.</p>"
        "<p>We may sell up to $50.0 million under our at-the-market program.</p>"
    )
    assert matching_sentences(html, ATM) == [
        "The Company may sell up to $50.0 million under the Sales Agreement."
    ]


def test_flattened_tables_are_skipped():
    table = "Sales agreement proceeds $ 1 " + "1,000 2,000 " * 100 + "end."
    assert matching_sentences(f"<p>{table}</p>", ATM) == []

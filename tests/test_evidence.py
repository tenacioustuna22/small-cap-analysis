import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from evidence import guidance_blocks, quotes, GUIDANCE  # noqa: E402
from src.edgar import EXHIBIT_99_1  # noqa: E402

RELEASE = """<html><body>
<p>Beats High End of Guidance • Delivered quarterly Revenue of $32.6 million</p>
<p>Guidance Raised revenue guidance for the Fiscal Year 2026: • Revenue of $123 million to $126 million
• Adjusted EBITDA loss of $12 million to $15 million</p>
<p>Reconciliation of GAAP to Adjusted figures follows.</p>
<p>These forward-looking statements include our outlook for revenue growth in 2027 and beyond.</p>
<p>The Company expects revenue growth to continue as Embedded partners launch products next year.</p>
</body></html>"""


def test_guidance_blocks_keep_ranges_and_stop_at_the_next_section():
    blocks = guidance_blocks(RELEASE)
    assert len(blocks) == 1
    assert blocks[0].startswith("Guidance Raised revenue guidance")
    assert "$12 million to $15 million" in blocks[0] and "Reconciliation" not in blocks[0]


def test_outlook_sentences_skip_safe_harbor_boilerplate():
    found = quotes(RELEASE, GUIDANCE)
    assert any(q.startswith("The Company expects revenue growth") for q in found)
    assert not any("forward-looking" in q for q in found)


def test_press_release_file_names():
    for name in ("bfly-20261029xexx991.htm", "hypr-ex99_1.htm", "d142207dex991.htm", "a-ex-99.1.htm"):
        assert EXHIBIT_99_1.search(name), name
    for name in ("d142207dex992.htm", "ex9910.htm", "bfly-20261029.htm"):
        assert not EXHIBIT_99_1.search(name), name

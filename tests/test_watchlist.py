import pytest

from src.watchlist import load_tickers, load_watchlist


def write(tmp_path, text):
    path = tmp_path / "watchlist.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_status_filters_tickers_and_defaults_to_active(tmp_path):
    path = write(
        tmp_path,
        "ticker,company,business,status\n"
        "aaa,A Co,x,active\nBBB,B Co,x,peer\nCCC,C Co,x,inactive\nDDD,D Co,x,\n",
    )
    assert load_tickers(path=path) == ["AAA", "DDD"]
    assert load_tickers(("active", "peer"), path=path) == ["AAA", "BBB", "DDD"]
    assert load_watchlist(path)["CCC"]["company"] == "C Co"


def test_file_without_status_column_is_all_active(tmp_path):
    path = write(tmp_path, "ticker,company,business\nAAA,A Co,x\n")
    assert load_tickers(path=path) == ["AAA"]


def test_unknown_status_is_an_error(tmp_path):
    path = write(tmp_path, "ticker,company,business,status\nAAA,A Co,x,maybe\n")
    with pytest.raises(ValueError, match="unknown status"):
        load_watchlist(path)

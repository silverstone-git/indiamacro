"""Unit tests that need no network."""

import pandas as pd
import pytest

from indiamacro import _http, countries, india, utils
from indiamacro.sources import mospi


# ---------------------------------------------------------------- dates

@pytest.mark.parametrize("label", ["2024-25", "2024-2025", " 2024 - 25 "])
def test_fy_start(label):
    assert utils.fy_start(label) == pd.Timestamp("2024-04-01")


@pytest.mark.parametrize("date,expected", [("2025-02-10", "2024-25"), ("2025-04-01", "2025-26"),
                                           ("2025-03-31", "2024-25")])
def test_fy_label(date, expected):
    assert utils.fy_label(date) == expected


@pytest.mark.parametrize("q,expected", [("Q1", "2024-04-01"), ("Q3", "2024-10-01"), (4, "2025-01-01")])
def test_fy_quarter_start(q, expected):
    assert utils.fy_quarter_start("2024-25", q) == pd.Timestamp(expected)


@pytest.mark.parametrize("label,expected", [
    ("2024", "2024-01-01"), ("2024-06", "2024-06-01"), ("2024-Q2", "2024-04-01"),
    ("2024Q4", "2024-10-01"), ("2024-S2", "2024-07-01"), ("2011-12", "2011-12-01"),
    ("2024-06-30", "2024-06-30"),
])
def test_parse_period(label, expected):
    assert utils.parse_period(label) == pd.Timestamp(expected)


def test_month_number():
    assert utils.month_number("September") == 9
    assert utils.month_number("sep") == 9
    assert utils.month_number(3) == 3


def test_to_number_cleans_government_formatting():
    s = pd.Series(["1,234.5", "-", "", "NA", "7", None])
    out = utils.to_number(s)
    assert out.iloc[0] == 1234.5 and out.iloc[4] == 7
    assert out.iloc[[1, 2, 3, 5]].isna().all()


# ---------------------------------------------------------------- transforms

def test_yoy_infers_monthly_and_quarterly():
    m = pd.Series(range(100, 124), index=pd.date_range("2020-01-01", periods=24, freq="MS"), dtype=float)
    assert utils.yoy(m).iloc[12] == pytest.approx(12.0)
    q = pd.Series([100, 101, 102, 103, 110.0], index=pd.date_range("2020-01-01", periods=5, freq="QS"))
    assert utils.yoy(q).iloc[4] == pytest.approx(10.0)


def test_yoy_rejects_daily():
    d = pd.Series(1.0, index=pd.date_range("2020-01-01", periods=400, freq="D"))
    with pytest.raises(ValueError):
        utils.yoy(d)


def test_rebase_and_cagr():
    s = pd.Series([50.0, 100.0, 200.0], index=pd.to_datetime(["2020-01-01", "2021-01-01", "2022-01-01"]))
    assert utils.rebase(s, 2021).tolist() == [50, 100, 200]
    assert utils.cagr(s) == pytest.approx(100, rel=0.01)


def test_wide_pivots_long_frames():
    long = pd.DataFrame({"date": pd.to_datetime(["2020-01-01"] * 2), "country": ["IND", "CHN"], "value": [1, 2]})
    assert utils.wide(long).loc["2020-01-01", "CHN"] == 2


# ---------------------------------------------------------------- countries

def test_lookup_accepts_names_and_codes():
    assert countries.iso3("India") == "IND"
    assert countries.iso3("IN") == "IND"
    assert countries.iso2("ind") == "IN"
    assert countries.iso3("uk") == "GBR"
    assert countries.iso3("Bharat") == "IND"


def test_expand_groups_puts_india_first():
    codes = countries.expand(["USA", "BRICS"])
    assert codes[0] == "IND"
    assert set(codes) == {"IND", "USA", "BRA", "RUS", "CHN", "ZAF"}
    assert len(codes) == len(set(codes))
    assert countries.expand(None) == ["IND"]
    assert countries.expand("south asia")[0] == "IND"


# ---------------------------------------------------------------- MoSPI parsing

@pytest.mark.parametrize("year,month,expected", [
    ("2025", "August", "2025-08-01"),
    ("2024-25", "May", "2024-05-01"),
    ("2024-25", "February", "2025-02-01"),   # Jan-Mar are in the second calendar year
    ("2024-25", None, "2024-04-01"),
    ("2019", None, "2019-01-01"),
])
def test_rbi_date(year, month, expected):
    assert mospi._rbi_date(year, month) == pd.Timestamp(expected)


def _fake_pages(pages):
    """Stand-in for _http.get_json that serves MoSPI-style paginated responses."""
    calls = []

    def get_json(url, params, **kw):
        calls.append(params)
        p = params["page"]
        return {"data": pages[p - 1], "meta_data": {"page": p, "totalPages": len(pages),
                                                     "totalRecords": sum(map(len, pages))}}
    return get_json, calls


def test_query_follows_pagination(monkeypatch):
    get_json, calls = _fake_pages([[{"a": 1}, {"a": 2}], [{"a": 3}]])
    monkeypatch.setattr(_http, "get_json", get_json)
    df = mospi.query("x/y", year=[2024, 2025])
    assert df["a"].tolist() == [1, 2, 3]
    assert calls[0]["year"] == "2024,2025" and calls[0]["limit"] == mospi.PAGE
    assert [c["page"] for c in calls] == [1, 2]


def test_query_refuses_huge_downloads(monkeypatch):
    get_json, _ = _fake_pages([[{"a": 1}]] * 5)
    monkeypatch.setattr(_http, "get_json", get_json)
    with pytest.raises(_http.SourceError, match="5 pages"):
        mospi.query("x/y", max_pages=3)


def test_query_treats_no_data_as_empty(monkeypatch):
    monkeypatch.setattr(_http, "get_json", lambda *a, **k: {"msg": "No Data Found", "statusCode": True})
    assert mospi.query("x/y").empty


def test_query_raises_api_errors(monkeypatch):
    monkeypatch.setattr(_http, "get_json", lambda *a, **k: {"success": False, "message": "Limit too big"})
    with pytest.raises(_http.SourceError, match="Limit too big"):
        mospi.query("x/y")


# ---------------------------------------------------------------- India helpers

def test_latest_revision_keeps_most_final_estimate():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2023-04-01"] * 3 + ["2024-04-01"]),
        "revision": ["First Advance Estimates", "Final Estimates", "Provisional Estimates",
                     "First Advance Estimates"],
        "value": [1, 3, 2, 9],
    })
    out = india._latest_revision(df)
    assert out.set_index("date")["value"].to_dict() == {pd.Timestamp("2023-04-01"): 3,
                                                        pd.Timestamp("2024-04-01"): 9}


# ---------------------------------------------------------------- cache

def test_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(_http, "CACHE_DIR", tmp_path)
    hits = []

    class Resp:
        status_code, content, text, url = 200, b"hello", "hello", "u"

    class Sess:
        def get(self, *a, **k):
            hits.append(1)
            return Resp()

    monkeypatch.setattr(_http, "session", lambda: Sess())
    assert _http.get("https://example.org/a", {"x": 1}) == b"hello"
    assert _http.get("https://example.org/a", {"x": 1}) == b"hello"
    assert len(hits) == 1

"""Offline tests for events, the event-study engine, the story framework and the web server helpers."""

import numpy as np
import pandas as pd
import pytest

from indiamacro.analysis import charts as C, events as E, framework
from indiamacro.web import server


def _jump_series(dates, jump=5.0):
    """Random-walk-free price series that jumps by ``jump``% on each event date."""
    idx = pd.bdate_range("2020-01-01", "2022-12-31")
    logp = np.zeros(len(idx))
    for d in dates:
        logp[idx.searchsorted(pd.Timestamp(d)):] += np.log1p(jump / 100)
    return pd.Series(100 * np.exp(logp), index=idx)


def test_event_study_recovers_a_known_jump():
    dates = ["2020-09-01", "2021-03-15", "2022-05-02"]   # each has 120 trading days of history
    ev = pd.DataFrame({"date": pd.to_datetime(dates), "label": ["a", "b", "c"], "category": "custom"})
    r = E.event_study(_jump_series(dates), ev, pre=5, post=10, log=True)
    assert r["n"] == 3
    assert r["mean"].loc[-1] == pytest.approx(0)
    assert r["mean"].loc[0] == pytest.approx(np.log1p(.05) * 100, rel=1e-6)
    assert r["mean"].loc[10] == pytest.approx(r["mean"].loc[0])     # no drift afterwards
    assert (r["summary"]["share_positive"] == 1).all()


def test_event_study_skips_events_without_enough_history():
    ev = pd.DataFrame({"date": pd.to_datetime(["2020-01-03"]), "label": ["too early"], "category": "custom"})
    assert E.event_study(_jump_series([]), ev)["n"] == 0


def test_event_study_level_changes_for_spreads():
    s = pd.Series(np.r_[np.zeros(200), np.full(100, 3.0)], index=pd.bdate_range("2021-01-01", periods=300))
    ev = pd.DataFrame({"date": [s.index[200]], "label": ["x"], "category": "custom"})
    r = E.event_study(s, ev, pre=3, post=5, log=False)
    assert r["mean"].loc[0] == pytest.approx(3.0)


def test_user_events_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(E, "USER_FILE", tmp_path / "events.json")
    n0 = len(E.load())
    ev = E.add("2025-08-14", "Strike on X refinery", "refinery_strike", "Russia")
    df = E.load()
    assert len(df) == n0 + 1 and not df.loc[df["id"] == ev["id"], "builtin"].iloc[0]
    assert ev["id"] in set(E.select("refinery_strike")["id"])
    assert E.remove(ev["id"]) and len(E.load()) == n0
    with pytest.raises(ValueError):
        E.add("2025-01-01", "x", "not-a-category")


def test_select_adds_custom_dates():
    df = E.select("opec", ["2025-01-02"])
    assert "custom" in set(df["category"]) and (df["category"].isin(["opec", "custom"])).all()


def test_story_isolates_failing_charts():
    @framework.story("_test_story", "Test", "Tools", "?", params=[framework.Param("n", "N", "number", 3)])
    def _(s):
        s.chart(lambda: C.line(pd.Series([1.0, 2.0], index=pd.to_datetime(["2020-01-01", "2020-02-01"]), name="ok"),
                               "fine"))
        s.chart(lambda: 1 / 0, title="broken")
        s.insight(f"n is {s.p['n']}")

    try:
        out = framework.run("_test_story", {"n": "7"})
        kinds = [b["kind"] for b in out["blocks"]]
        assert kinds == ["line", "error"]
        assert "ZeroDivisionError" in out["blocks"][1]["message"]
        assert out["insights"] == ["n is 7"] and out["values"] == {"n": 7}
    finally:
        framework.STORIES.pop("_test_story")


def test_chart_specs_have_no_nan():
    s = pd.Series([1.0, np.nan, 3.0], index=pd.date_range("2020-01-01", periods=3, freq="MS"), name="x")
    spec = C.line(s, "t")
    assert spec["traces"][0]["y"] == [1.0, 3.0]
    tile = C.kpi("x", s)
    assert tile["value"] == 3.0 and tile["date"] == "2020-03-01"


def test_server_json_clean():
    assert server._clean({"a": [1.0, float("nan"), float("inf")], "b": (2, "x")}) == {"a": [1.0, None, None],
                                                                                        "b": [2, "x"]}

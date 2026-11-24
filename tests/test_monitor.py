"""Offline tests for the terminal (monitor package): no network, simulated data only."""

import json
import threading
from http.server import ThreadingHTTPServer

import pandas as pd
import pytest

from indiamacro.monitor import assistant, env, fake_llm, feeds, query, sim


@pytest.fixture(autouse=True)
def demo_mode(monkeypatch):
    """Force every loader and feed onto simulated data and hide any real LLM config."""
    monkeypatch.setenv("INDIAMACRO_DEMO", "1")
    for k in ("LLM_ENDPOINT", "LLM_API_KEY", "LLM_MODEL", "OPENAI_BASE_URL", "OPENAI_API_KEY", "OPENAI_MODEL"):
        monkeypatch.delenv(k, raising=False)
    feeds.clear()
    yield
    feeds.clear()


def test_env_loader_parses_quotes_comments_and_keeps_existing(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text('# comment\nA_ONE="quoted value"\nexport A_TWO=plain # trailing\nA_THREE=keep\n')
    monkeypatch.setenv("A_THREE", "from-env")
    env.load(f)
    assert env.get("A_ONE") == "quoted value"
    assert env.get("A_TWO") == "plain"
    assert env.get("A_THREE") == "from-env"


def test_openai_variable_names_are_accepted(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    assert assistant.configured() and assistant._endpoint() == "https://api.openai.com/v1"
    monkeypatch.setenv("OPENAI_BASE_URL", "http://proxy.local/v1/")
    monkeypatch.setenv("OPENAI_MODEL", "m")
    assert assistant._url() == "http://proxy.local/v1/chat/completions" and assistant._model() == "m"
    monkeypatch.setenv("LLM_ENDPOINT", "http://other/v1/chat/completions")
    assert assistant._url() == "http://other/v1/chat/completions"     # LLM_* wins


@pytest.mark.parametrize("text, expected", [
    ("food inflation vs repo rate", ["india_food_cpi", "repo_rate"]),
    ("how does oil relate to the rupee", ["brent", "usdinr"]),
    ("did oil prices drive the rupee?", ["brent", "usdinr"]),
    ("boiling point", []),                                   # "oil" inside a word is not a match
])
def test_mentions(text, expected):
    assert query.mentions(text) == expected


@pytest.mark.parametrize("question, tool", [
    ("How does the oil price relate to the rupee?", "correlate"),
    ("show nifty and gold since 2020", "get_series"),
    ("compare inflation with BRICS since 2010", "compare_countries"),
    ("india gdp growth vs china and us", "compare_countries"),
    ("rupee around 2025-04-02", "window"),
    ("what is happening right now?", "live_snapshot"),
    ("what can I ask?", "list_series"),
])
def test_planner_picks_tool(question, tool):
    assert assistant.plan(question)[0][0] == tool


def test_transforms():
    s = pd.Series(range(1, 25), index=pd.date_range("2020-01-01", periods=24, freq="MS"), dtype=float)
    assert query.transform(s, "yoy").iloc[0] == pytest.approx((13 / 1 - 1) * 100)
    assert query.transform(s, "index100").iloc[0] == 100
    assert abs(query.transform(s, "zscore").mean()) < 1e-9
    with pytest.raises(ValueError):
        query.transform(s, "nonsense")


def test_correlate_finds_a_planted_lead(monkeypatch):
    idx = pd.date_range("2000-01-01", periods=240, freq="MS")
    x = pd.Series(sim.series("x", periods=240, mean_revert=0, vol=1).values, index=idx)
    y = x.shift(3)                      # b follows a by 3 months
    monkeypatch.setitem(query.SERIES, "ta", query.Spec("A", "%", "test", lambda: x))
    monkeypatch.setitem(query.SERIES, "tb", query.Spec("B", "%", "test", lambda: y))
    monkeypatch.delenv("INDIAMACRO_DEMO")
    r = query.correlate("ta", "tb", freq="M", transform_="level")
    assert r["stats"]["best_lag"] == 3 and r["stats"]["best_r"] > 0.99
    assert {c["type"] for c in r["charts"]} == {"line", "bar"}


def test_get_series_never_uses_two_axes():
    r = query.get_series(["brent", "usdinr"])
    assert r["sim"] and "SIMULATED" in r["text"]
    assert len(r["charts"]) == 2                  # different units -> small multiples
    assert all("y2axis" not in c for c in r["charts"])


def test_mock_answer_is_labelled_and_charted():
    r = assistant.ask("How does brent relate to the rupee?")
    assert r["mode"] == "mock" and "Mock analyst" in r["answer"]
    assert r["sim"] and r["charts"]
    json.dumps(r)                                    # must be JSON-serialisable for the server


def test_feeds_fall_back_to_labelled_simulation():
    for env_ in (feeds.quotes(), feeds.quakes(), feeds.weather(), feeds.satellites("military")):
        assert env_["status"] == "sim" and env_["data"]
        assert "SIMULATED" in env_["source"]


def test_parse_tle_and_constellations():
    txt = ("IRNSS-1B\n1 39635U 14017A   26328.5  .00000000  00000-0  00000-0 0  9990\n"
           "2 39635  29.0 100.0 0001 0.0 0.0  1.00270000    10\n"
           "GPS BIIR-2  (PRN 13)\n1 24876U 97035A   26328.5  .00000000  00000-0  00000-0 0  9990\n"
           "2 24876  55.0 100.0 0001 0.0 0.0  2.00560000    10\n")
    sats = feeds._parse_tle(txt, "")
    assert [s["tag"] for s in sats] == ["NavIC", "GPS"] and sats[0]["norad"] == 39635


def test_eonet_centroid():
    assert feeds._centroid({"type": "Point", "coordinates": [77.0, 28.0]}) == (28.0, 77.0)
    lat, lon = feeds._centroid({"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2]]]})
    assert (lat, lon) == (1.0, 1.0)


def test_llm_tool_loop_against_fake_server(monkeypatch):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), fake_llm.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        monkeypatch.setenv("LLM_ENDPOINT", f"http://127.0.0.1:{srv.server_port}/v1")
        monkeypatch.setenv("LLM_API_KEY", "test")
        r = assistant.ask("Is food inflation leading the repo rate?")
        assert r["mode"] == "llm" and [t["name"] for t in r["tools"]] == ["correlate"]
        assert "Fake LLM answer" in r["answer"] and r["charts"]
    finally:
        srv.shutdown()

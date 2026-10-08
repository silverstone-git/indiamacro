"""Live checks against the real sources. Run with: uv run pytest -m live"""

import pandas as pd
import pytest

import indiamacro as im
from indiamacro.ping import CHECKS

pytestmark = pytest.mark.live


@pytest.mark.parametrize("check", CHECKS, ids=[f"{c.source}: {c.what}" for c in CHECKS])
def test_source_returns_recent_data(check):
    df = check.run()
    assert not df.empty
    assert df["value"].notna().any()
    assert pd.api.types.is_datetime64_any_dtype(df["date"])


@pytest.mark.parametrize("name", ["gdp", "gdp_growth", "iip_growth", "cpi_inflation", "cpi_food_inflation",
                                  "wpi_inflation", "unemployment", "repo_rate", "usdinr", "reer",
                                  "forex_reserves"])
def test_india_headline_series(name):
    s = getattr(im.india, name)()
    assert isinstance(s.index, pd.DatetimeIndex) and s.index.is_monotonic_increasing
    assert s.notna().sum() > 3
    assert s.attrs["source"] and s.attrs["unit"]


def test_compare_india_first():
    t = im.compare("inflation", "G20", start=2020)
    assert t.columns[0] == "IND" and len(t.columns) > 10


def test_imf_projection_flag():
    df = im.imf.weo("NGDP_RPCH", "IND")
    assert df["projection"].eq(True).any() and df["projection"].eq(False).any()


@pytest.mark.parametrize("story_id", [s for s in __import__("indiamacro.analysis", fromlist=["STORIES"]).STORIES
                                      if not s.startswith("_")])
def test_every_page_renders_without_errors(story_id):
    from indiamacro.analysis import run
    page = run(story_id)
    errors = [b for b in page["blocks"] if b.get("kind") == "error"]
    assert not errors, errors

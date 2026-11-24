"""The terminal: live feeds, a queryable series registry and an LLM analyst.

    feeds      real-time feeds (quotes, quakes, natural events, aircraft, weather/air quality,
               satellite orbital elements, chokepoint transits, IMF map data), each with a
               clearly labelled simulated fallback
    query      tools that slice the data (get, correlate, compare, live snapshot)
    assistant  answers questions with those tools, through an OpenAI-compatible endpoint
               (LLM_ENDPOINT / LLM_API_KEY in .env) or a rule-based mock when none is set
"""

from __future__ import annotations

from . import env  # noqa: F401  (loads .env on import)

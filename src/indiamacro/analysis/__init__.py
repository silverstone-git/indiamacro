"""Analysis: dated events, event studies, and the pages ("stories") the web app shows.

    from indiamacro.analysis import run, catalog, events
    page = run("tpl_refinery", {"post": 10})
"""

from . import events
from . import stories_india, stories_energy, stories_templates, stories_tools  # noqa: F401 - registers stories
from .framework import STORIES, catalog, run

__all__ = ["events", "run", "catalog", "STORIES"]

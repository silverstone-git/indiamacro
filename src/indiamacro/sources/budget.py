"""Union Budget documents (Ministry of Finance, indiabudget.gov.in).

The Budget publishes Excel workbooks with the latest Budget Estimates (BE),
Revised Estimates (RE) and previous-year Actuals. These are formatted reports
rather than tidy tables, so they are returned raw (``header=None``): look at the
sheet, then slice the rows you need.

Only the current year's files are on the home page; older years are in the
archive at https://www.indiabudget.gov.in/budget_archive/ .
"""

from __future__ import annotations

import io

import pandas as pd

from .. import _http

SOURCE = "budget"
BASE = "https://www.indiabudget.gov.in"

FILES = {
    "budget_at_a_glance": "doc/Budget_at_Glance/budget_at_a_glance.xlsx",
    "annual_financial_statement": "doc/AFS/allafs.xlsx",
    "expenditure_summary": "doc/eb/sumsbe.xlsx",
    "expenditure_by_ministry": "doc/eb/allsbe.xlsx",
}


def workbook(name: str = "budget_at_a_glance") -> dict[str, pd.DataFrame]:
    """All sheets of a Budget workbook as raw DataFrames, keyed by sheet name.

    ``name`` is a key of :data:`FILES` or a path relative to indiabudget.gov.in.
    """
    path = FILES.get(name, name)
    body = _http.get(f"{BASE}/{path}", ttl=7 * _http.DAY, source=SOURCE)
    if not body.startswith(b"PK"):
        raise _http.SourceError(SOURCE, f"{path} is not an .xlsx file")
    return pd.read_excel(io.BytesIO(body), sheet_name=None, header=None)

# Research-outcome angle: is R&D and education money producing results?

Status: **plan, nothing implemented yet.** Written 2026-11-19. Details about external sources were written from
memory and are marked "verify" where the URL, file format or coverage must be checked before coding.

The question: public and private money goes into education and R&D. What reaches the intended place, and what
comes out the other end (learning, startups, useful patents)? The library currently has **no** R&D, education or
patent data, apart from what World Bank gives through `worldbank.get(...)`.

The chain we want to be able to show, India first, peers alongside:

```
money in (budget, GERD, by funder)  ->  capacity (researchers, institutions)  ->  outputs (papers, patents, startups)
                                    ->  outcomes (learning levels, patent quality, commercial use)
```

---

## A. Changes needed in the repo (free data)

### A1. No new code: use `worldbank.get` and `compare`

World Bank indicators that already work with `sources/worldbank.py` (codes to verify with `worldbank.search`):

| Code | Meaning |
|---|---|
| `GB.XPD.RSDV.GD.ZS` | R&D spending, % of GDP (confirmed working; India has no value after 2020) |
| `SP.POP.SCIE.RD.P6` | Researchers in R&D per million people (confirmed; India sparse) |
| `SP.POP.TECH.RD.P6` | Technicians in R&D per million |
| `IP.PAT.RESD` / `IP.PAT.NRES` | Patent applications, residents / non-residents |
| `IP.JRN.ARTC.SC` | Scientific and technical journal articles |
| `SE.XPD.TOTL.GD.ZS` | Government education spending, % of GDP |
| `HD.HCI.LAYS` / `HD.HCI.HLO` | Learning-adjusted years of schooling / harmonized learning outcomes |
| `SE.LPV.PRIM` | Learning poverty (verify availability) |

Work: add an `RD_INDICATORS` / `EDUCATION_INDICATORS` dict (like `compare.INDICATORS`), a `india.rd_snapshot()`
helper, and a dashboard page. `compare.py` runs on IMF WEO, so these need either a World Bank-based `compare` variant
or a new function; decide which before building.

### A2. New source: `sources/aser.py` (ASER, Pratham)

- What: rural household survey. Share of Std V children who can read a Std II text, and who can do division;
  by state and district, 2005 onward (biennial, with a gap in the pandemic years).
- Where: asercentre.org data and report tables (verify: tables are PDF/Excel, there may be no API).
- Output: long format `date, country, series, value` plus `state`, `std`, `skill`. Date is the survey year.
- Caveats to write into the docstring and LIMITATIONS.md: **rural only**, Std II-level text (not Std III),
  survey method changed in 2022 and 2024 (phone vs household), so do not splice across method changes the way
  we do not splice across base years. Say so in `attrs["note"]`.

### A3. New source: `sources/udise_nas.py` (official schooling data)

- NCERT NAS 2021 and PARAKH Rashtriya Sarvekshan 2024 (grade 3, 6, 9 scores by state), UDISE+ (enrolment,
  teachers, infrastructure by state), AISHE (higher education).
- Where: education.gov.in, udiseplus.gov.in, aishe.gov.in (verify: mostly PDFs and dashboards; may need a
  maintained snapshot rather than a live parser).
- If a source has no stable machine-readable endpoint, keep it as a **dated snapshot CSV under `data/`** with the
  original URL and access date in the file header. Do not scrape fragile dashboards.

### A4. New source: `sources/budget.py` additions: R&D and education lines

`budget.py` already downloads the Union Budget workbooks as raw frames. Needed:

- A function `rd_lines()` that slices expenditure rows for: DST, DBT, DSIR/CSIR, ICAR, ISRO/Dept of Space,
  DRDO, Dept of Atomic Energy, MeitY, ANRF, Ministry of Earth Sciences.
- A function `education_lines()` for Dept of School Education and Dept of Higher Education (Samagra Shiksha, PM
  POSHAN, UGC, IITs/IIMs/NITs).
- Each row to carry BE, RE and Actuals. **The gap between BE and Actuals is the "is it reaching the target"
  measure we can compute for free.** Build `utilisation = actuals / BE` per ministry and year.
- Row labels change between years; keep a mapping table and test it on canned workbooks (offline).
- Older years need the archive at indiabudget.gov.in/budget_archive (the module docstring already notes this).

### A5. New source: `sources/patents.py`

Free patent-quality ingredients:

| Source | Use | Notes (verify) |
|---|---|---|
| PatentsView (USPTO) API | citations, family, assignee country, for India-origin US patents | free, needs an API key now |
| WIPO IP Statistics Data Center | filings by office/origin | bulk download |
| OECD patent indicators / REGPAT | triadic families, quality indicators | via the existing `oecd.py`? check coverage |
| Indian Patent Office annual report + InPASS | filings, grants, examination backlog, applicant type (university vs firm) | PDFs; InPASS search is not an API |
| Google Patents public data (BigQuery) | citations and legal status at scale | needs a Google account, free tier |

Quality proxies to compute (document each as a proxy, not "usefulness"):
forward citations, renewal/lapse rate, grant rate, triadic family share, share by applicant type.
Write the method note carefully: **citations measure technical influence, not social benefit.**

### A6. New source: `sources/startups.py`

- DPIIT Startup India recognised-startup counts by state/sector (verify: dashboard, may need snapshot).
- NIRF innovation fields and ARIIA ranking tables for incubators per institution (annual, PDF/Excel).
- Output: counts only. State plainly that these are institution self-reported and say nothing about survival.

### A7. Research output: `sources/openalex.py`

- OpenAlex API (free, no key; polite pool if you add a contact email in the query string, **but keep the
  contact out of the repo and use a generic client name**).
- Papers and citations by country and by Indian institution, field-normalised citation impact.
- Fits the "output" and "quality" stages: share of top-10% cited papers vs peers.

### A8. Wiring (per CLAUDE.md "Adding or changing a source")

For each new module:
1. Docstring with URL, key needs, quirks; `SOURCE`, `BASE`; long-format output; go through `_http.get`.
2. Export in `src/indiamacro/__init__.py` and `__all__`. (Known issue: `sources.energy` is still not
   exported; fix that in the same change.)
3. Add a `Check` to `ping.CHECKS`.
4. Document in README source table, `docs/SOURCES.md`, and `LIMITATIONS.md`.
5. Offline tests in `tests/test_offline.py` using canned payloads.

### A9. Dashboard pages (new section or under "India")

Use the `@story` pattern in `analysis/stories_india.py` (or a new `stories_research.py`, imported in
`analysis/__init__.py`):

1. `rd_funding` - GERD % GDP vs peers; central vs state vs business share (needs A1 + manual data B2).
2. `rd_budget_flow` - BE vs Actuals by science ministry (A4).
3. `learning_levels` - ASER reading/arithmetic by state over time (A2); insight computed from data.
4. `patent_quality` - India-origin patents: citations, lapse, family size vs Korea/China (A5).
5. `pipeline` - one page lining up input, capacity, output, outcome for India and peers.

Each needs `method` and `caveats`, and insights computed from numbers, not hard-coded.

### A10. Things we deliberately will NOT claim

- That money was "pocketed" or spent on "vanity projects". Budget data shows allocation and utilisation, not
  intent. Findings of misuse come from audits (CAG reports, utilisation certificates); cite those, do not infer.
- Anything about election spending from budget data. Party and election funding is a different dataset
  (ADR/Election Commission filings); out of scope unless you want to add it as a separate module.
- A single "percentage of useful patents". Report the proxies and say what each measures.

---

## B. Data to buy or obtain manually (ask the professor)

These are valuable but are paid, login-gated or not published as data. CLAUDE.md puts paid and gated sources out
of scope for the *library*, so treat these as **local files you supply**. If you obtain them, we can add a
loader that reads a path you give it (never commit the files; check each licence first).

### B1. Corporate R&D (the biggest gap: business is where India is weakest)

| Data | Where | Why it matters |
|---|---|---|
| Firm-level R&D expenditure, profits, wages, employees, listed and unlisted | **CMIE Prowess** (paid; many universities subscribe) | Links "profits" to R&D at firm level, which free data cannot do |
| Same, alternative | Capitaline, Bloomberg, S&P Capital IQ, Refinitiv (paid) | Cross-check Prowess |
| MCA21 company filings | mca.gov.in (per-filing fee) | Audited R&D line items for unlisted firms |
| Industrial R&D survey microdata | DSIR (Dept of Scientific and Industrial Research) | Official business R&D, in-house R&D units |
| R&D Statistics and Indicators (national S&T survey) | DST NSTMIS, request tables or microdata | Funding by source and sector, latest years beyond World Bank |

### B2. Who funds and who performs R&D

- **R&D funding by source and performer (central, state, higher-ed, industry)**: DST's "Research and Development
  Statistics" tables. Public but often late; the latest edition may need to be requested.
- **RBI DBIE** (partly gated) for state-level spending breakdowns, when free views are not enough.

### B3. Utilisation and misuse evidence

- **CAG audit reports** (public, PDFs): Smart Cities Mission, Samagra Shiksha, research council audits. Useful
  and free, but needs reading, not an API.
- **Utilisation certificates, scheme-level releases**: Ministry or Parliament Q&A (Lok Sabha / Rajya Sabha
  answers, public, searchable at sansad.in) give scheme-wise releases vs spending. Slow but free.
- **Smart Cities Mission dashboard** (smartcities.gov.in): project-level cost and completion; snapshot it.

### B4. Patents and commercialisation (paid or heavy)

- **Derwent Innovation, PatSnap, Questel Orbit, LexisNexis PatentSight** (paid): cleaned patent value
  scores, legal status, litigation and licensing. PatentSight's "Patent Asset Index" is the standard commercial
  quality metric.
- **Indian Patent Office renewal and lapse status in bulk**: InPASS lists them one patent at a time; bulk data
  likely needs a request to the office or a paid vendor.
- **Technology transfer / licensing income by university**: not published consistently; ask each institution's
  IPR/tech-transfer office, or check annual reports and NIRF submissions.

### B5. Startups

- **Tracxn, Venture Intelligence, Crunchbase, PitchBook, Inc42 Datalabs** (paid): funding, founders' alma mater,
  survival. Founders' college is the missing link for "startups from leading colleges"; the free registry lacks it.
- **LinkedIn / Naukri data** for employment outcomes (terms of use restrict scraping; do not scrape).
- **Incubator-level outcomes** (survival, jobs, funds raised): ask the incubators directly or DST NSTEDB.

### B6. Education outcomes

- **ASER microdata / district tables**: free on request from Pratham for researchers; confirm the licence.
- **NAS 2021 and PARAKH 2024 state/district microdata**: ask NCERT / Ministry of Education; summary reports are
  public, microdata is usually not.
- **PISA / TIMSS microdata** (OECD / IEA, free but India has no national PISA sample; use state-level 2009
  PISA+ data only with the caveat that it is old).
- **PLFS and NSS education rounds** (MoSPI, free microdata after registration): link education to jobs and wages.
- **Graduate outcomes / placement data**: NIRF submissions (self-reported) and, for better quality, institution
  records via the professor.

### B7. Research output

- **Scopus / Web of Science (paid)**: better coverage than OpenAlex for some fields; check the university
  subscription. OpenAlex is free and usually enough for country-level work.
- **SciVal / InCites** (paid): ready-made field-normalised impact for Indian institutions.

---

## C. Suggested order

1. A1 (existing World Bank indicators), so a first R&D-vs-peers page appears with no new scraping.
2. A4 (BE vs Actuals for science and education ministries): free, and the best "does it reach the target" evidence.
3. A2 (ASER) and A7 (OpenAlex): outcomes and quality, both free.
4. A5 (patents), starting with PatentsView and the OECD indicators.
5. Ask the professor for B1 and B2 first: business R&D is the largest unknown, and it decides whether the
   story is "government underspends" or "firms underspend".
6. A3 and A6 last: official schooling and startup data are the least machine-readable.

## D. Open questions for you

- Do you want the library to read local files from paid sources (a loader that takes a path), or keep those in a
  separate analysis folder outside the package?
- Is the target country India only, or India vs peers throughout (affects whether we need OECD/WIPO coverage)?
- Audience: students citing numbers. For the misuse question, are CAG report findings acceptable as the
  evidence base, given that budget data alone cannot show intent?

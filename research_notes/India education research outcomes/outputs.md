# Outputs and quality in India's education and R&D chain: papers, patents, startups

All live facts below were accessed on **20 Nov 2026** (the research date). Where a source itself carries a
publication/data date, that date is given first. "Unverified" marks anything taken from a search snippet rather
than a primary page; none of those are used as headline claims. No figure below comes from memory.

---

## Key question 1: Scientific publications and citations — how much does India publish, and what do citation proxies say?

### Takeaway
India is now a very large and fast-growing publisher (roughly a quarter-million journal articles a year in
OpenAlex and 228,000 in the World Bank/UNESCO series for 2023), but field-normalised citation impact is
*below* the world average (OpenAlex FWCI>1 share 29.8% in 2023; Clarivate CNCI 0.89 in 2024) and well below
the US, UK, Germany, China and Korea. The volume story and the impact story are different and must be kept apart.

### Cited Findings

**A. OpenAlex live API — exact queries and results (accessed 20 Nov 2026)**

Method actually run: REST endpoint `https://api.openalex.org/works`, default **core corpus** (excludes expansion
works, non-traditional parts and pulled works), `type:article`, one country at a time via
`institutions.country_code:{ISO2}`, one publication year at a time. Counts are `meta.count` of works with **at
least one author affiliated to an institution in that country** (not fractionalised by author). The API returned
a notice that keyless requests share a free daily budget; no key was used and all calls succeeded (HTTP 200).

- Base query template (exact form used), e.g. India 2023:
  `https://api.openalex.org/works?filter=institutions.country_code:IN,publication_year:2023,type:article&select=id&per-page=1` — returned **255,226** articles. [OpenAlex API](https://api.openalex.org/works?filter=institutions.country_code:IN,publication_year:2023,type:article&select=id&per-page=1) (accessed 20 Nov 2026)
- Field-normalised impact proxy: same query plus `,fwci:>1` — India 2023 **76,059 articles (29.8%)**. [OpenAlex API](https://api.openalex.org/works?filter=institutions.country_code:IN,publication_year:2023,type:article,fwci:%3E1&select=id&per-page=1) (accessed 20 Nov 2026)
- OpenAlex defines FWCI as citations received in publication year + 3 following years divided by the average for
  works of the same year, type and subfield; 1.0 = world average. It follows the Snowball Metrics recipe; about
  68% of works carry an FWCI (mid-2026). [OpenAlex citations documentation](https://help.openalex.org/data/works/citations.md) (accessed 20 Nov 2026)
- OpenAlex corpus/counting rules: default view is the curated core (~295M works), pulled works and non-traditional
  parts excluded; entity-level `works_count` may include the expansion corpus, so live works queries are the
  correct basis for these numbers. [OpenAlex corpus documentation](https://help.openalex.org/data/works/corpus.md) and [counting documentation](https://help.openalex.org/how-to/counting.md) (accessed 20 Nov 2026)

Full live results (all from the same query template, `type:article`, values are count; share with FWCI>1):

| Country | 2015 articles | 2015 FWCI>1 | 2023 articles | 2023 FWCI>1 | 2024 articles | 2024 FWCI>1 |
|---|---:|---:|---:|---:|---:|---:|
| India | 120,164 | 39,119 (32.6%) | 255,226 | 76,059 (29.8%) | 300,217 | 86,356 (28.8%) |
| China | 429,279 | 157,263 (36.6%) | 785,561 | 387,265 (49.3%) | 932,285 | 452,339 (48.5%) |
| South Korea | 85,716 | 34,617 (40.4%) | 89,894 | 39,223 (43.6%) | 94,769 | 41,970 (44.3%) |
| United States | 556,777 | 305,883 (54.9%) | 593,058 | 268,407 (45.3%) | 613,945 | 273,134 (44.5%) |
| United Kingdom | 161,671 | 95,699 (59.2%) | 188,384 | 101,622 (53.9%) | 196,742 | 105,091 (53.4%) |
| Germany | 139,639 | 76,254 (54.6%) | 157,617 | 76,506 (48.5%) | 160,011 | 78,763 (49.2%) |
| Brazil | 129,037 | 41,669 (32.3%) | 190,411 | 43,334 (22.8%) | 209,024 | 43,548 (20.8%) |

Source for every cell: the OpenAlex API query template linked above with the relevant ISO2 code (`IN`, `CN`,
`KR`, `US`, `GB`, `DE`, `BR`) and year substituted, with and without `fwci:>1` (accessed 20 Nov 2026).
Example peer query: `https://api.openalex.org/works?filter=institutions.country_code:CN,publication_year:2023,type:article,fwci:%3E1&select=id&per-page=1` [OpenAlex API](https://api.openalex.org/works?filter=institutions.country_code:CN,publication_year:2023,type:article,fwci:%3E1&select=id&per-page=1) (accessed 20 Nov 2026).

- If `type:article` is dropped (all OpenAlex work types), 2023 counts are: India **388,686**, China **1,062,774**,
  Korea **117,995**, US **1,207,756**, UK **314,420**, Germany **277,480**, Brazil **253,873**. [OpenAlex API](https://api.openalex.org/works?filter=institutions.country_code:IN,publication_year:2023&select=id&per-page=1) (accessed 20 Nov 2026) — always state which universe was used.
- A `cited_by_percentile_year.min:>90` "top-10%" filter was also run, but it produced implausibly large 2023
  shares (India 30.4%, China 47.2%, US 34.7% of articles) versus near-10% for 2015. This is a tie/coarse-bin
  artefact in the year-percentile field for recent years; **do not use that number as a top-10% share**. FWCI>1 is
  the defensible field-normalised public proxy here. [OpenAlex API test query](https://api.openalex.org/works?filter=institutions.country_code:IN,publication_year:2023,type:article,cited_by_percentile_year.min:%3E90&select=id&per-page=1) (accessed 20 Nov 2026)

**B. World Bank / UNESCO indicator IP.JRN.ARTC.SC (accessed 20 Nov 2026)**

- Latest available year is **2023**; World Bank API metadata `lastupdated` = 11 Nov 2026; the series is
  "Scientific and technical journal articles" (counts, not per-capita in the API response). [World Bank API](https://api.worldbank.org/v2/country/IND;CHN;KOR;USA;GBR;DEU;BRA/indicator/IP.JRN.ARTC.SC?format=json&per_page=300&date=2010:2025) (accessed 20 Nov 2026)
- 2023 values: India **228,174.3**, China **932,711.9**, US **430,843.3**, Germany **108,782.3**, UK **97,536**,
  Korea **71,724.3**, Brazil **58,292.04**. India's 2018–2023 path: 123,052.7 → 128,579.5 → 145,711.1 →
  173,096.5 → 200,488.4 → 228,174.3. [World Bank API](https://api.worldbank.org/v2/country/IND;CHN;KOR;USA;GBR;DEU;BRA/indicator/IP.JRN.ARTC.SC?format=json&per_page=300&date=2010:2025) (accessed 20 Nov 2026)
- **Conflict to flag:** World Bank/UNESCO 228,174 (India, 2023) vs OpenAlex 255,226 `type:article` and 388,686
  all-works (India, 2023). These are different corpora and counting rules (UNESCO UIS journal-article series vs
  OpenAlex's broader index, fractional vs whole-count authorship). Do not present them as interchangeable; cite
  the series name every time. [World Bank API](https://api.worldbank.org/v2/country/IND/indicator/IP.JRN.ARTC.SC?format=json&date=2023:2023) and [OpenAlex API](https://api.openalex.org/works?filter=institutions.country_code:IN,publication_year:2023,type:article&select=id&per-page=1) (both accessed 20 Nov 2026)

**C. Credible public bibliometric report: Springer Nature, "Global Research Pulse: India" (accessed 20 Nov 2026)**

This is a publisher-produced report; its impact numbers come from paid Clarivate/Dimensions data but the report
itself is free. Use it as a secondary, clearly attributed summary, not as an independent audit. [Springer Nature report](https://stories.springernature.com/global-research-pulse-india/) (accessed 20 Nov 2026)

- India's output rose from **34,000 articles (2010) to 195,000 (2024)**, almost six-fold; 141,000 of the 2024
  articles were Web-of-Science-indexed (72%+), a 5% share of indexed research. Five-year CAGR 2019–24 for indexed
  articles: India **14%**, China 14%, Brazil 1%, US/UK/Germany 0% or negative. [Springer Nature report](https://stories.springernature.com/global-research-pulse-india/) (accessed 20 Nov 2026)
- Category Normalized Citation Impact (CNCI, >1 = above world average): India **0.73 (2015) → 0.89 (2024)**;
  G20 average **1.04 (2015) → 1.13 (2024)**. Internationally co-authored Indian papers reach **1.4x** world
  average (Clarivate G20 research and innovation scorecard 2025). [Springer Nature report](https://stories.springernature.com/global-research-pulse-india/) (accessed 20 Nov 2026)
- CNCI distribution for India, 2015–2024: **18.57% uncited**, 9.23% in (0, 0.125], 11.31% in (0.125, 0.25],
  17.23% in (0.25, 0.5], 19.65% in (0.5, 1], 14.59% in (1, 2], 6.77% in (2, 4], 2.04% in (4, 8], 0.62% >8;
  G20 average uncited share 15.83%. [Springer Nature report](https://stories.springernature.com/global-research-pulse-india/) (accessed 20 Nov 2026)
- Top-10% cited papers: India **19,000 articles, 11% of its publications, 3rd globally behind China and the US**
  (Dimensions, 2023 publications). Note this is a publisher summary of a paid index. [Springer Nature report](https://stories.springernature.com/global-research-pulse-india/) (accessed 20 Nov 2026)
- JCR quartiles 2024: India Q1 **30%**, Q2 **37%**, Q3 22%, Q4 11% (129K articles); 67% in top-half journals.
  China 62% Q1, US 51%, UK 53%, Germany 52%, Korea 55%, Brazil 34%. [Springer Nature report](https://stories.springernature.com/global-research-pulse-india/) (accessed 20 Nov 2026)
- Nature Index 2025 Research Leaders: India ranked **9th**, with share-of-coverage **1,506.638 (2022) →
  1,783.337 (2023)**; only **1,506** articles counted in 2024. Nature Index itself warns that its metrics alone
  should not be used to assess institutions or individuals. **Internal conflict to flag:** the same report's prose
  says "14.5% increase in adjusted share from 2022 to 2023" while its Table 4 column "Change in Adjusted Share
  2022–2023" shows **2%** for India. Do not quote either without the caveat. [Springer Nature report](https://stories.springernature.com/global-research-pulse-india/) (accessed 20 Nov 2026)

### Inferences
- India's publication volume is now comparable to the US in level and faster growing; its citation-normalised
  impact is below 1 and below every rich-country peer in the OpenAlex and Clarivate comparisons, while Brazil is
  lower still. This is a statement about *measured citation influence in indexed journals*, not about the social
  or economic value of the research.
- The 2015→2023/24 move is mixed: OpenAlex FWCI>1 share fell slightly for India (32.6%→29.8%), while the
  Clarivate CNCI rose (0.73→0.89). Different field normalisation, corpora and time windows — flag as a
  methodology-dependent disagreement, not a trend reversal.
- Nature Index (a selected set of ~top natural/health journals) and JCR quartile shares reward a different
  phenomenon (where papers are published) from FWCI/CNCI (how often they are cited). India's rank-9 Nature Index
  position is compatible with below-average CNCI.

### Gaps
- No free, reproducible field-normalised **top-10% cited share** was obtained: the OpenAlex year-percentile filter
  is not reliable for recent years, and the 19,000-article figure comes from paid Dimensions via a publisher
  report without a downloadable query.
- No OpenAlex data on **retractions**, **open-access share**, **funder attribution** or **industry collaboration**
  by India was collected here; all are available in principle from the same free API and would strengthen a
  "quality" discussion.
- No independent (non-publisher, non-paid-database) bibliometric audit of Indian research was found in this pass.

---

## Key question 2: Patents — India-origin filings and grants, peers, and what "patent quality" proxies are actually free

### Takeaway
India crossed **100,000 patent applications in a calendar year for the first time in 2025 (105,163, +37.5%)**, but
grants fell sharply that year (15,989 origin-grants, −41.2%) — a backlog/exam-capacity artefact that must not be
read as an invention collapse. Genuinely free quality-ish proxies are limited to grant share, patents in force,
applicant-type mixes and per-patent legal status; forward citations, family size and triadic families are not
available as free India-level aggregates from the sources checked.

### Cited Findings

**A. WIPO World Intellectual Property Indicators 2026 (data as of Sep 2026; report published 18 Nov 2026; accessed 20 Nov 2026)**

- 2025 patent applications **by origin** (resident + abroad, absolute counts): world 3,948,900; China 1,910,431;
  US 489,766; Japan 466,301; Republic of Korea 319,210; Germany 132,714; **India 105,163 (+37.5%)**; France
  52,146; UK 48,765; Italy 27,634; Brazil **9,145 (+14.3%)**. [WIPO WIPI 2026, table A4](https://www.wipo.int/edocs/pubdocs/en/wipo-pub-941-2026-en-world-intellectual-property-indicators-2026.pdf) (accessed 20 Nov 2026)
- India's 2025 milestone is described as the **seventh consecutive year of double-digit growth**, driven mainly
  by resident filings. Global applications grew 6.0% in 2025; India contributed +28,690 of the net increase. [WIPO WIPI 2026, pp. 8, 10](https://www.wipo.int/edocs/pubdocs/en/wipo-pub-941-2026-en-world-intellectual-property-indicators-2026.pdf) (accessed 20 Nov 2026)
- WIPO news release confirming the milestone: "Global Patent and Trademark Filings Hit Record High; India Crosses
  100,000 Annual Patent Application Mark", published **18 Nov 2026**. [WIPO news](https://www.wipo.int/en/web/ip-statistics/w/news/2026/wipo-world-intellectual-property-indicators-global-patent-and-trademark-filings-hit-record-high-india-crosses-100-000-annual-patent-application-mark) (accessed 20 Nov 2026) — note the article body is JS-loaded and could not be read; the title/date are verified, numbers above come from the PDF.
- Resident share of filings at the **Indian office** rose from **27.6% (2015) to 67.5% (2025)**; Indian office
  filings grew 27.8% in 2025, the ninth straight annual increase. [WIPO WIPI 2026, p. 14](https://www.wipo.int/edocs/pubdocs/en/wipo-pub-941-2026-en-world-intellectual-property-indicators-2026.pdf) (accessed 20 Nov 2026)
- Resident applications per USD 100bn GDP, 2025: Korea 7,271; China 5,034; Japan 4,828; Finland 1,608;
  Switzerland 1,450; Germany 1,275; US 1,025. **India 150 (2015) → 618 (2025)**, a more-than-quadrupling. India
  is *not* in the top 20 for resident applications per million population (Korea 4,050; Japan 2,331; China
  1,262). [WIPO WIPI 2026, pp. 12–13](https://www.wipo.int/edocs/pubdocs/en/wipo-pub-941-2026-en-world-intellectual-property-indicators-2026.pdf) (accessed 20 Nov 2026)
- 2025 patent grants **by origin**: China 986,423; US 263,338; Japan 237,780; Korea 174,197; Germany 66,885;
  France 20,702; UK 20,436; **India 15,989 (−41.2%)**; Brazil **2,916 (−8.3%)**. India's *resident* grants fell
  from 19,746 to 7,822. [WIPO WIPI 2026, table A36 and p. 19](https://www.wipo.int/edocs/pubdocs/en/wipo-pub-941-2026-en-world-intellectual-property-indicators-2026.pdf) (accessed 20 Nov 2026)
- **Grant share** (grants as share of applications processed in 2025, offices reporting outcomes): Vietnam 81.4%,
  **India 77.7%**, Japan 75.5%, Korea 73.5%; US 39.1%, China 36.2%; withdrawal/abandonment shares highest in
  Brazil (39.9%) and Mexico (34.6%). WIPO explicitly warns that examination processes differ and cross-country
  comparison is difficult. [WIPO WIPI 2026, p. 18](https://www.wipo.int/edocs/pubdocs/en/wipo-pub-941-2026-en-world-intellectual-property-indicators-2026.pdf) (accessed 20 Nov 2026)
- Patents **in force**: world 21.4m in 2025 (+6.5%); China 6.3m, US 3.6m, Japan 2.1m, Korea 1.4m; **India
  224,162, down 1.9% — its first decline since 2015** after six straight years of double-digit growth. [WIPO WIPI 2026, pp. 19–20](https://www.wipo.int/edocs/pubdocs/en/wipo-pub-941-2026-en-world-intellectual-property-indicators-2026.pdf) (accessed 20 Nov 2026)
- WIPO caution: "differences in the number of patents granted depend on factors such as examination capacity and
  procedural delays. For this reason, application data for a given year should not be compared with grant data for
  that same year." [WIPO WIPI 2026, p. 18](https://www.wipo.int/edocs/pubdocs/en/wipo-pub-941-2026-en-world-intellectual-property-indicators-2026.pdf) (accessed 20 Nov 2026)

**B. Indian Patent Office (IPO/CGPDTM) Annual Report 2024-25 (English PDF published 2 May 2026; accessed 20 Nov 2026)**

Primary source page: [IPO annual reports list](https://www.ipindia.gov.in/annual-report); PDF:
[IPO Annual Report 2024-25](https://www.ipindia.gov.in/storage/uploads/docs-operator/7a8f0ca4-5a8e-416e-b8d4-5647ec352bb9.pdf) (both accessed 20 Nov 2026).

- Applications filed (fiscal years 2020-21 → 2024-25): **58,503; 66,440; 82,811; 92,168; 110,375**. FY2024-25
  was +19.75% YoY. [IPO AR 2024-25, pp. 9, 20](https://www.ipindia.gov.in/storage/uploads/docs-operator/7a8f0ca4-5a8e-416e-b8d4-5647ec352bb9.pdf) (accessed 20 Nov 2026)
- FY2024-25: **68,201 domestic** filings (61.79% of total, up from 51,574 / 55.96% in FY2023-24) and **42,174
  foreign** filings (+3.89% from 40,594). [IPO AR 2024-25, p. 20](https://www.ipindia.gov.in/storage/uploads/docs-operator/7a8f0ca4-5a8e-416e-b8d4-5647ec352bb9.pdf) (accessed 20 Nov 2026)
- Grants (same five fiscal years): 28,385; 30,073; 34,134; **103,057**; **33,504**. FY2024-25 grants fell 67.49%
  YoY and **10,682 of 33,504 went to Indian applicants**. As at 1 Apr 2025, **230,480 patents in force, 50,848
  held by Indian patentees**. The 103,057 in FY2023-24 is an exceptional one-year spike; treat both the spike and
  the fall as examination/backlog events, not as signals of invention quality. [IPO AR 2024-25, pp. 9, 26](https://www.ipindia.gov.in/storage/uploads/docs-operator/7a8f0ca4-5a8e-416e-b8d4-5647ec352bb9.pdf) (accessed 20 Nov 2026)
- **Applicant-type breakdown of FY2024-25 filings** (Indian / foreign): Natural persons 17,170 / 1,159;
  **startups 2,680 / 24**; small entities 2,575 / 172; **educational institutions 37,681 / 213**; other than
  natural persons 8,095 / 40,606; total 68,201 / 42,174. Educational institutions alone are ~34% of all Indian
  filings. [IPO AR 2024-25, p. 21](https://www.ipindia.gov.in/storage/uploads/docs-operator/7a8f0ca4-5a8e-416e-b8d4-5647ec352bb9.pdf) (accessed 20 Nov 2026)
- State-wise Indian applicants, FY2024-25 (top ten): Tamil Nadu 15,440; Karnataka 8,371; Maharashtra 7,893;
  Uttar Pradesh 5,703; Punjab 4,461; Telangana 4,293; Andhra Pradesh 3,582; Gujarat 2,743; Delhi 2,520;
  Rajasthan 2,003. [IPO AR 2024-25, p. 20](https://www.ipindia.gov.in/storage/uploads/docs-operator/7a8f0ca4-5a8e-416e-b8d4-5647ec352bb9.pdf) (accessed 20 Nov 2026)
- Top academic/university applicants by FY2024-25 applications filed: Lovely Professional University 2,241;
  Saveetha Institute of Medical and Technical Sciences 2,038; IITs collectively 1,740; Jain (deemed university)
  1,504; Siksha 'O' Anusandhan 995; Sanskriti University 703; Sathyabama 645; VIT 629; Presidency University
  Bangalore 625; Graphic Era 592. [IPO AR 2024-25, p. 23](https://www.ipindia.gov.in/storage/uploads/docs-operator/7a8f0ca4-5a8e-416e-b8d4-5647ec352bb9.pdf) (accessed 20 Nov 2026)
- Expedited examination (a procedural fast-track, not a patent-quality measure): 1,026 startup requests in
  FY2024-25, 546 granted; all categories 7,154 requests, 3,349 granted. [IPO AR 2024-25, p. 26](https://www.ipindia.gov.in/storage/uploads/docs-operator/7a8f0ca4-5a8e-416e-b8d4-5647ec352bb9.pdf) (accessed 20 Nov 2026)

**C. Which "quality" proxies are genuinely free (accessed 20 Nov 2026)**

- **Grant share / grant rate:** free and published by WIPO at office level for 2025 (India 77.7%); usable only as
  an examination-outcome statistic, not as a technology-quality score. [WIPO WIPI 2026, p. 18](https://www.wipo.int/edocs/pubdocs/en/wipo-pub-941-2026-en-world-intellectual-property-indicators-2026.pdf) (accessed 20 Nov 2026)
- **Patents in force (renewal proxy):** free stocks by office from WIPO (India 224,162 in 2025) and by Indian
  patentees from IPO (50,848 as at 1 Apr 2025). Neither gives a cohort **lapse/renewal rate**; that would require
  per-patent legal-status histories. [WIPO WIPI 2026, pp. 19–20](https://www.wipo.int/edocs/pubdocs/en/wipo-pub-941-2026-en-world-intellectual-property-indicators-2026.pdf) and [IPO AR 2024-25, p. 26](https://www.ipindia.gov.in/storage/uploads/docs-operator/7a8f0ca4-5a8e-416e-b8d4-5647ec352bb9.pdf) (both accessed 20 Nov 2026)
- **Applicant type (university vs firm vs startup):** free in the IPO annual report category table and top-applicant
  tables; no peer-comparable free series of this kind was found. [IPO AR 2024-25, pp. 21–23](https://www.ipindia.gov.in/storage/uploads/docs-operator/7a8f0ca4-5a8e-416e-b8d4-5647ec352bb9.pdf) (accessed 20 Nov 2026)
- **Per-patent legal status and full text:** free via the Indian Patent Office's InPASS public search
  (`https://iprsearch.ipindia.gov.in/PublicSearch/`), which supports bibliographic/full-text/legal-status search
  with CAPTCHA but is not a bulk-downloadable aggregate statistics API. [USPTO patent-office links](https://www.uspto.gov/patents/search) and [InPASS description](https://library.shu.edu/c.php?g=718339&p=5125321) (both accessed 20 Nov 2026)
- **Forward citations and family size:** available for **US patents** from PatentsView/USPTO Open Data Portal
  (free account + API key), not as an India-level aggregate from the free sources checked. PatentsView's legacy
  `search.patentsview.org` API has been transitioned to USPTO ODP; previously issued PatentsView keys are **not
  compatible** with ODP APIs, and ODP requires a free `X-API-KEY` header. [USPTO transition guide](https://data.uspto.gov/support/transition-guide/patentsview) and [USPTO getting started](https://data.uspto.gov/apis/getting-started) (both accessed 20 Nov 2026)
- **Triadic patent families:** defined by OECD as families with patents at EPO, JPO and USPTO sharing a priority;
  intended to capture the more valuable inventions and reduce office-rule bias. The OECD data are free via the
  OECD Data Explorer / MSTI, but the collection is OECD-centred; a current India-specific series could not be
  verified in this pass. [OECD triadic patent families methodology](https://www.oecd.org/content/dam/oecd/en/publications/reports/2004/03/triadic-patent-families-methodology_g17a156f/443844125004.pdf) and [OECD indicator page](https://www.oecd.org/en/data/indicators/triadic-patent-families.html) (both accessed 20 Nov 2026)
- **Forward-citation-weighted, family-size-weighted or "triadic" India indicators are therefore a paid-source gap**
  (Derwent, PatSnap, EPO PATSTAT, ORBIS/industry databases) and should be named as such in a later-report gaps
  section. [PATSTAT product description](https://link.epo.org/web/business/patstat/en-patstat-complementary-data_sets.pdf) (accessed 20 Nov 2026)

**D. Definition conflicts to flag explicitly (accessed 20 Nov 2026)**

- IPO FY2024-25 **110,375** applications (Indian fiscal year, applications received at Indian offices, includes
  foreign applicants) vs WIPO calendar-2025 **105,163** India-origin applications (worldwide, resident + abroad,
  by residence of first named applicant). Both are correct for their own definitions; neither supersedes the
  other. [IPO AR 2024-25](https://www.ipindia.gov.in/storage/uploads/docs-operator/7a8f0ca4-5a8e-416e-b8d4-5647ec352bb9.pdf) and [WIPO WIPI 2026 table A4](https://www.wipo.int/edocs/pubdocs/en/wipo-pub-941-2026-en-world-intellectual-property-indicators-2026.pdf) (both accessed 20 Nov 2026)
- IPO FY2024-25 **33,504** grants (Indian office, fiscal year) vs WIPO 2025 **15,989** India-origin grants
  (worldwide, calendar year). Same non-comparability. [IPO AR 2024-25](https://www.ipindia.gov.in/storage/uploads/docs-operator/7a8f0ca4-5a8e-416e-b8d4-5647ec352bb9.pdf) and [WIPO WIPI 2026 table A36](https://www.wipo.int/edocs/pubdocs/en/wipo-pub-941-2026-en-world-intellectual-property-indicators-2026.pdf) (both accessed 20 Nov 2026)
- WIPO patents in force **224,162 (2025)** vs IPO **230,480 (as at 1 Apr 2025)** — different reference dates and
  coverage; do not average or difference them. [WIPO WIPI 2026](https://www.wipo.int/edocs/pubdocs/en/wipo-pub-941-2026-en-world-intellectual-property-indicators-2026.pdf) and [IPO AR 2024-25](https://www.ipindia.gov.in/storage/uploads/docs-operator/7a8f0ca4-5a8e-416e-b8d4-5647ec352bb9.pdf) (both accessed 20 Nov 2026)

### Inferences
- The Indian patent system is scaling fast on filings, with a rapidly rising domestic share, but throughput
  (grants) is highly volatile because of examination/backlog cycles. Any "quality" narrative built on grant counts
  alone would be misleading.
- The very large educational-institution share of Indian filings (37,681 of 68,201 domestic filings in FY2024-25)
  is a measurable *input-to-output link* between universities and the IP system. It is not evidence that those
  patents are commercially valuable, licensed, or even maintained.
- Free public data can answer "how many, where, by whom, and what share granted"; it cannot answer "how valuable,
  how novel, how often cited, how many licensed" at aggregate India level.

### Gaps
- No free aggregate **forward-citation, family-size or renewal/lapse-rate** series for Indian patents was found;
  InPASS gives case-level status only, and PatentsView/ODP is US-centric and key-gated.
- No verified current **India observations in OECD triadic-family data**; the free OECD indicator page and
  methodology were located, but the country coverage was not confirmed in this pass.
- No free **patent-licensing / commercialisation revenue** measure (e.g. university technology-transfer income)
  was found in the sources checked.
- No peer-comparable **applicant-type** breakdown (university vs firm) outside India's annual report.

---

## Key question 3: Startups — what DPIIT recognition counts do and do not measure

### Takeaway
DPIIT-recognised startups passed **2.23 lakh by 31 Mar 2026** and **55,200+ were recognised in FY2025-26 alone**,
with state-level counts published. These are **self-declared registrations**, not firms proven to be viable: only
**6,385** were recorded as closed (dissolved/struck off) as at 31 Oct 2025, and the commonly quoted jobs and
funding figures are either self-reported or scheme-disbursement figures.

### Cited Findings

- **Latest official stock and flow:** 55,200+ startups recognised in FY2025-26 (up 51.6% from 36,400+ in
  FY2024-25); cumulative **2.23 lakh recognised as at 31 Mar 2026**; **23.36 lakh direct jobs** reported;
  1.07 lakh+ recognised startups have at least one woman director/partner (~48%). [PIB release 2253019, 17 Apr 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2253019&reg=48&lang=2) (accessed 20 Nov 2026)
- **State-wise recognised startups as at 31 Mar 2026 (top ten):** Maharashtra 38,660+; Karnataka 22,600+; Uttar
  Pradesh 21,960+; Delhi 21,120+; Gujarat 19,270+; Tamil Nadu 14,830+; Telangana 12,520+; Haryana 11,620+;
  Kerala 8,620+; Rajasthan 8,100+. [PIB release 2253019, 17 Apr 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2253019&reg=48&lang=2) (accessed 20 Nov 2026)
- **Sector distribution:** DPIIT startups are spread across **56 industries**; IT Services and Healthcare &
  Life Sciences are the largest in the certificate counts. Critically, the Startup India 9-Year Factbook states
  its numbers are certificates issued through 31 Dec 2024 **"including approved, cancelled, and expired
  startups"**, and labels its jobs figure **"as self-reported by startups"**. [Startup India 9-Year Factbook (Jan 2025)](https://www.startupindia.gov.in/content/dam/invest-india/startup-milestone/FactbookJan25.pdf) (accessed 20 Nov 2026)
- **Tier-II/III and women:** ~50% of DPIIT-recognised startups come from Tier-II/III cities (as at Dec 2025);
  >45% had at least one woman director/partner; >120 privately held firms valued above USD 1bn with combined
  valuation >USD 350bn. [PIB "A Decade of Startup India", 15 Jan 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2214872&reg=3&lang=2) (accessed 20 Nov 2026)
- **Closures:** 1,97,692 entities recognised as at 31 Oct 2025; of these **6,385 were categorised "closed"
  (dissolved/struck off) per Ministry of Corporate Affairs data shared 11 Nov 2025**. The government also stated
  it had "not observed any increase in startup closures". [PIB release 2197662, 2 Dec 2025](https://www.pib.gov.in/PressReleaseDetail.aspx?PRID=2197662&reg=6&lang=1) (accessed 20 Nov 2026)
- **Earlier job claim (for trend, with caveat):** 1,59,157 recognised as at 15 Jan 2025 and "over 16.6 lakh direct
  jobs" reportedly created as at 31 Oct 2024; IT Services 2.04 lakh, Healthcare & Lifesciences 1.47 lakh,
  Professional & Commercial Services ~94,000. Jobs are self-reported by the startups. [PIB "Nine Years of Startup India", 15 Jan 2025](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2093125) (accessed 20 Nov 2026)
- **Public funding actually disbursed (better than "funding raised" claims):** FFS had disbursed >₹7,000 crore to
  135+ AIFs by end-FY2025-26, which in turn invested >₹26,900 crore in 1,420+ startups; SISFS had selected 219
  incubators, committed the full ₹945 crore corpus, and approved >₹605 crore for 3,400+ startups; CGSS had
  guaranteed 410+ loans worth >₹1,250 crore. [PIB release 2253019, 17 Apr 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2253019&reg=48&lang=2) (accessed 20 Nov 2026)
- **Startups as patent filers:** >19,400 patent applications filed by startups cumulatively; 2,850+ in FY2024-25
  rising to 4,480+ in FY2025-26. Note this is a *flow of applications*, not grants or licensed patents. [PIB release 2253019, 17 Apr 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2253019&reg=48&lang=2) (accessed 20 Nov 2026) — compare with the IPO annual report's 2,680 startup filings in FY2024-25; the two official figures are close but not identical, likely definition/timing differences; flag rather than reconcile. [IPO AR 2024-25, p. 21](https://www.ipindia.gov.in/storage/uploads/docs-operator/7a8f0ca4-5a8e-416e-b8d4-5647ec352bb9.pdf) (accessed 20 Nov 2026)
- **Procurement as an outcome proxy:** 38,600+ startups onboarded on GeM; orders worth ₹19,190 crore placed in
  FY2025-26 (1,40,260+ orders). [PIB release 2253019, 17 Apr 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2253019&reg=48&lang=2) (accessed 20 Nov 2026)
- **Conflicting live counter:** a web-search result for the Startup India homepage displayed **263,862 DPIIT
  Recognised Startups** on 20 Nov 2026, higher than PIB's 2.23 lakh at 31 Mar 2026. The homepage counter is
  JS-loaded and could not be verified directly in this pass; **unverified**, and not used as a headline figure. [Startup India homepage](https://www.startupindia.gov.in/) (accessed 20 Nov 2026)

### Inferences
- Registration counts measure take-up of a government recognition scheme, which is genuinely useful as an
  ecosystem *input/participation* indicator and can be broken down by state. They do not measure firm survival,
  revenue, employment quality, innovation or social impact.
- The only official closure number found (6,385 of 1,97,692 = ~3.2% at Oct 2025) is a **stock of MCA-dissolved
  entities in a cumulative recognition register**, not a cohort survival rate: newer recognitions have had less
  time to fail, and struck-off entities may be counted before or after other statuses are updated.
- Jobs and valuations quoted in PIB factsheets are self-reported or market estimates; treat them as *claims by
  the ecosystem*, not audited outcomes.

### Gaps
- No public microdata linking DPIIT recognition to **survival, revenue, employment growth or patent grants** by
  cohort was found.
- No independent audit of the "23.36 lakh direct jobs" or "16.6 lakh direct jobs" figures; both are self-reported.
- No credible free public series of **private venture funding by startup cohort/sector** was located (Crunchbase and
  other paid providers would be needed); only government scheme disbursements are available free.
- Sector breakdown is available as broad industry certificate counts (56 industries) but not as a clean,
  time-consistent public table of recognised startups by sector and state in the sources read.

---

## Key question 4: Method limits — what these proxies can and cannot say, and claims that must NOT be made

### Takeaway
Citations, patent counts and startup registrations all measure **technical influence, formal rights or participation**
— not social usefulness, commercial success, or whether public money was well spent. A student-facing report must
state this before any number.

### Cited Findings

- OpenAlex's FWCI is explicitly a *citation* metric normalised for year, work type and subfield — the numerator is
  citations received, not uptake, implementation or welfare. [OpenAlex citations documentation](https://help.openalex.org/data/works/citations.md) (accessed 20 Nov 2026)
- Clarivate CNCI and Dimensions top-10% shares used in the Springer Nature report are similarly citation-based;
  the report itself notes Nature Index metrics alone should not be used to assess institutions or individuals. [Springer Nature report](https://stories.springernature.com/global-research-pulse-india/) (accessed 20 Nov 2026)
- WIPO warns that patent grants depend on examination capacity and procedural delays and should not be compared
  with same-year applications; it also warns that grant/rejection shares across offices are not directly
  comparable because examination processes differ. [WIPO WIPI 2026, pp. 18–19](https://www.wipo.int/edocs/pubdocs/en/wipo-pub-941-2026-en-world-intellectual-property-indicators-2026.pdf) (accessed 20 Nov 2026)
- OECD describes triadic families as a way to capture "more valuable inventions" and improve comparability — i.e.
  an *international-filing* proxy for value, not a measure of actual commercial or social value. [OECD triadic patent families methodology](https://www.oecd.org/content/dam/oecd/en/publications/reports/2004/03/triadic-patent-families-methodology_g17a156f/443844125004.pdf) (accessed 20 Nov 2026)
- DPIIT/Startup India factbook explicitly says its certificate counts include approved, cancelled **and expired**
  startups, and that jobs are **self-reported by startups**. [Startup India 9-Year Factbook (Jan 2025)](https://www.startupindia.gov.in/content/dam/invest-india/startup-milestone/FactbookJan25.pdf) (accessed 20 Nov 2026)

**Claims that must NOT be made from these data (each is an unsupported inference):**

1. "X% of Indian patents/startups are useful/successful/valuable." No free source yields a fraction of *useful*
   patents or startups; grant share, patents in force, registrations and GeM orders are different things.
2. "The 41.2% fall in India-origin grants in 2025 means Indian inventions got worse." Grants lag applications by
   years and move with examination capacity; WIPO explicitly says not to compare same-year applications and
   grants. [WIPO WIPI 2026, pp. 18–19](https://www.wipo.int/edocs/pubdocs/en/wipo-pub-941-2026-en-world-intellectual-property-indicators-2026.pdf) (accessed 20 Nov 2026)
3. "India has 2.23 lakh successful startups" or "startups created 23.36 lakh verified jobs." Recognition is
   self-declared; jobs are self-reported; certificates include cancelled and expired entities. [PIB release 2253019](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2253019&reg=48&lang=2) and [Startup India Factbook](https://www.startupindia.gov.in/content/dam/invest-india/startup-milestone/FactbookJan25.pdf) (both accessed 20 Nov 2026)
4. "Only ~3% of Indian startups fail" (from 6,385/1,97,692), or "90% fail." The 6,385 is a cumulative stock of
   MCA-dissolved entities at a date, not a cohort failure rate, and the denominator is a cumulative register. [PIB release 2197662](https://www.pib.gov.in/PressReleaseDetail.aspx?PRID=2197662&reg=6&lang=1) (accessed 20 Nov 2026)
5. "R&D money was wasted" or "the money produced X papers per rupee." None of these sources links a specific
   rupee of public R&D spending to a specific paper, patent or firm; attribution and lag would need a different
   design. (See the separate research on R&D spending for that side of the chain.)
6. "India's research is above world average because it is 9th in Nature Index / 3rd in top-10% cited papers."
   Nature Index is a selected-journal share; the top-10% figure comes from paid Dimensions via a publisher report;
   both can coexist with CNCI 0.89 and OpenAlex FWCI>1 share of 29.8%. [Springer Nature report](https://stories.springernature.com/global-research-pulse-india/) and [OpenAlex API](https://api.openalex.org/works?filter=institutions.country_code:IN,publication_year:2023,type:article,fwci:%3E1&select=id&per-page=1) (both accessed 20 Nov 2026)
7. "Indian university patents are low quality because universities file the most." The IPO report shows the count
   (37,681 educational-institution filings in FY2024-25) but no forward citations, renewal or licensing data. [IPO AR 2024-25, p. 21](https://www.ipindia.gov.in/storage/uploads/docs-operator/7a8f0ca4-5a8e-416e-b8d4-5647ec352bb9.pdf) (accessed 20 Nov 2026)
8. Treating the World Bank 228,174 and OpenAlex 255,226/388,686 India 2023 publication counts as a contradiction
   to be resolved, or mixing them in one series. They are different definitions. [World Bank API](https://api.worldbank.org/v2/country/IND/indicator/IP.JRN.ARTC.SC?format=json&date=2023:2023) and [OpenAlex API](https://api.openalex.org/works?filter=institutions.country_code:IN,publication_year:2023&select=id&per-page=1) (both accessed 20 Nov 2026)

### Inferences
- The honest narrative is a *chain with measured links but unmeasured conversions*: more papers and more filings,
  below-average field-normalised citation impact, volatile grants, self-reported startup participation. The
  conversion from any one link to the next (paper → cited → licensed patent → viable firm → social benefit) is
  not measured by any free public source consulted.
- A student-facing dashboard should label each series with its producer, definition, year and the word **proxy**
  where relevant, and should never display a single composite "quality score".

### Gaps
- No free source measures the conversion between R&D spending, publications, patents and firm outcomes at the
  same time and with consistent definitions; a causal claim is therefore out of scope.
- No source was found that measures the *social* usefulness of research or patents (health, environment, welfare),
  even approximately, in a way comparable across these peers.

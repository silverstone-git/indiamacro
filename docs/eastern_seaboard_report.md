# India's Eastern Seaboard: Ports, Cities, Gaps and a Master Plan for Sea Leverage

**Report on the eastern coastline of India (West Bengal → Odisha → Andhra Pradesh → Tamil Nadu → Puducherry → Kerala tip), its major port-cities, what holds back sea-leverage and logistics, the port-to-industry linkages, the global benchmark seaboard, and a phased master plan.**

**Prepared with live web data (all figures dated as of 20 Nov 2026 unless noted).**  
**Intended end-use:** a citable report, plus a set of data sources to absorb into the `indiamacro` library (see § Data sources & library integration).

---

## 1. Executive summary

India's eastern seaboard faces the Bay of Bengal and sits astride the fastest-growing trade lane in the world — Asia–ASEAN–East Asia. It hosts **7 of India's 12 major ports** (Chennai, Ennore/Kamarajar, Haldia, Kolkata/Syama Prasad Mookerjee, Paradip, Tuticorin/V.O. Chidambaranar, Visakhapatnam) and the **East Coast Economic Corridor (ECEC)**, a 2,500 km Kolkata→Kanyakumari coastal corridor whose first phase is the **Visakhapatnam–Chennai Industrial Corridor (VCIC)**.

The assets are real: Visakhapatnam is the largest east-coast port (~143.7 MTPA FY22-23; ~81 MTPA iron ore alone in FY23-24); Chennai (~136 MTPA) and Ennore (~91 MTPA) anchor the "Detroit of Asia" auto cluster; Paradip is a bulk/liquid bulk behemoth; Haldia is the petrochemicals/chemicals gateway to eastern India; Krishnapatnam and Dhamra are deep-draft, Super-Capesize-ready private ports.

What is **lacking** is not port depth alone — it is the *system around the port*:
- **Transshipment dependence:** ~75% of India's transshipped containers are handled at foreign hubs (Colombo, Singapore, Port Klang, Jebel Ali) as of May 2025; Colombo alone derives ~82% of its throughput from transshipment.
- **Last-mile evacuation:** rail, road and inland-waterway links from port gate to industrial node remain congested or missing; first/last-mile delays raise dwell time and logistics cost.
- **Draft & super-post-Panamax readiness:** only a handful of east-coast berths take fully laden Ultra Large Container Vessels / Super Capesize ships.
- **Cold-chain & reefer:** pharma (Vizag) and seafood/aquaculture (AP coast) need temperature-controlled logistics that ports don't consistently provide.
- **Logistics cost:** India is traditionally cited at 13–14% of GDP (developed-country benchmark 8–10%; US ~9.5%, Germany ~8%); newer DPIIT/NCAER estimates put it at ~7.9–8.8% (2021–23) — still above the best global ports' hinterlands.
- **Institutional fragmentation:** port, railway, highway, customs and state agencies plan separately; implementation slippage is the recurring failure mode.

The **best worldwide example of a really good seaboard** is the **Port of Rotterdam** for integrated port–hinterland–industry operation (rail Betuweroute, inland barge, pipelines, road, 5 port areas + 3 distribution parks, ~500 M consumers hinterland, 428 Mt cargo 2025, smart-port/digital-twin operations). **Singapore** is the transshipment/connectivity benchmark (DNV–Menon Leading Container Ports #1, 2025; world's busiest transshipment hub), and **Shanghai** is the scale/connectivity benchmark (51.5 M TEU 2024, top Liner Shipping Connectivity Index). India's east coast should copy Rotterdam's *hinterland integration*, Singapore's *transshipment discipline*, and Shanghai's *deep-draft, ULGV-ready terminals*.

The master plan below converts this into a 5-phase, port-by-port programme tied to industrial cities, with a data-source appendix designed to be imported into `indiamacro`.

---

## 2. The eastern seaboard: port-city inventory (as of FY22-23 / latest available)

| # | Port / city | State | Type & role | Cargo (FY22-23) | Key industrial hinterland | Principal gap |
|---|-------------|-------|-------------|-----------------|---------------------------|---------------|
| 1 | **Visakhapatnam (Vizag)** | Andhra Pradesh | Major; deepest natural harbour; gateway port for Nepal EXIM; iron ore, POL, refinery, seafood | ~143.7 MTPA | Heavy industry, steel, refinery, pharma APIs, aquaculture | Channel deepening, berth mechanisation, cold-chain/reefer, multi-modal evacuation to AP/Telangana |
| 2 | **Chennai** | Tamil Nadu | Major; 2nd-largest Indian port; containers, autos, general cargo | ~136 MTPA | "Detroit of Asia" autos (Hyundai, BMW, Renault-Nissan), electronics (Foxconn, Salcomp) | Congestion, last-mile road/rail, limited draft for largest container ships |
| 3 | **Ennore / Kamarajar** | Tamil Nadu | Major; first corporatised major port; coal, POL, cars, containers | ~91 MTPA | Chennai auto & electronics cluster; power | On-dock rail to Bengaluru exists but needs scaling; container terminal capacity |
| 4 | **Haldia (Kolkata Dock System)** | West Bengal | Major; petrochemicals, chemicals, edible oils; river-sea (Hooghly) | ~92.8 MTPA | Jute, tea, petrochemicals, chemicals; eastern India/Nepal/Bhutan/Bangladesh gateway | Siltation & draft restrictions, navigation on Hooghly, rail/road evacuation, container terminal mechanisation |
| 5 | **Kolkata (SMP Kolkata)** | West Bengal | Major; riverine dock system; largest container terminal on east coast | ~50.7 MTPA | WB, Bihar, Jharkhand, UP, Assam, Northeast, Nepal, Bhutan | Draft/tide constraints, ageing docks, connectivity to AKIC industrial nodes |
| 6 | **Paradip** | Odisha | Major; artificial deep-water; bulk & liquid bulk | (bulk 44.04%, liquid bulk 33.80% of throughput) | Iron ore, coal, crude (IOCL refinery), steel, aluminium, cement, power | Odisha–Jharkhand–Chhattisgarh mineral evacuation; dedicated freight corridor links |
| 7 | **Tuticorin (V.O. Chidambaranar)** | Tamil Nadu | Major; containers, bulk, salt, fish | (major port) | TN south districts, spices, textiles | Limited deep-draft container berths; connectivity to CBIC/Tumakuru |
| 8 | **Krishnapatnam** | Andhra Pradesh | Private (Adani); deep draft, Super-Capesize (200k DWT), 5 cape-enabled berths | 59.2 MMT throughput / 75 MMT capacity | VCIC node; Nellore; AP industrial belt | Last-mile to KRCL rail & NH16; utilization headroom (59/75) |
| 9 | **Dhamra** | Odisha | Private (Adani); deep-draft all-weather; bulk silo 4,000 tph | 48.8 MMT / 52 MMT capacity | Odisha/Jharkhand/WB minerals, steel slabs | Rail spur capacity; hinterland industrial zone build-out |
| 10 | **Gopalpur** | Odisha | Deep-draft (14.5 m), 3 multipurpose berths | (minor/intermediate) | Odisha–Jharkhand–Chhattisgarh minerals, steel, aluminium | 2.5 km entrance channel; rail link to Howrah–Chennai trunk exists, needs volume |
| 11 | **Kakinada** | Andhra Pradesh | Intermediate/developing | — | VCIC node; gas, petroleum, aquaculture | Full deep-water development; corridor links |
| 12 | **Kattupalli** | Tamil Nadu | Private; multi-cargo, Panamax-ready, on-dock CFS & rail siding | 13 MMT throughput / 37 MMT capacity | Chennai north auto/electronics | Gate-complex congestion; yard automation |

**Sources:** Wikipedia list of Indian ports (cargo FY22-23); Adani Enterprises port operational performance (2026); PIB press releases; NICDC industrial corridor project lists; ORF ECEC analysis (Nov 2025). See § Data sources.

### The corridors that bind port to city to factory
- **East Coast Economic Corridor (ECEC)** — Kolkata to Kanyakumari, ~2,500 km; hosts 7 of 12 major ports; ADB-supported; port-led industrialisation aimed at ASEAN trade.
- **Visakhapatnam–Chennai Industrial Corridor (VCIC)** — first ECEC phase, ~800 km AP–TN; four nodes: **Visakhapatnam, Kakinada, Krishnapatnam, Yerpedu–Srikalahasti**. Projects: Kopparthy (2,596 acres, ₹2,137 crore, 54,500 jobs potential), Visakhapatnam, Chittoor industrial areas.
- **Chennai–Bengaluru Industrial Corridor (CBIC)** — Krishnapatnam (AP), Tumakuru (KA), Ponneri (TN).
- **Amritsar–Kolkata Industrial Corridor (AKIC)** — Raghunathpur (WB) node serves the Kolkata–Haldia gateway.
- **Odisha Economic Corridor (OEC)** — Gopalpur–Bhubaneswar–Kalinganagar and Paradip–Kendrapada–Dhamra–Subernarekha nodes.

---

## 3. What the eastern seaboard lacks (gap analysis by theme)

### 3.1 Transshipment hub gap (the single biggest leak)
About **three-quarters of India's transshipped containers are handled overseas** (May 2025, Economic Times/ports report). Indian east-coast cargo feeds **Colombo** (~82% transshipment share of its throughput), **Singapore**, **Port Klang** and **Jebel Ali**. That adds a feeder leg, extra handling, dwell time and cost, and sends maritime-services value (warehousing, ship repair, bunkering, freight forwarding) abroad. India's answer — the **Galathea Bay International Container Transshipment Port** (Great Nicobar) — is strategic but far from the east-coast industrial belt; the east coast itself needs a **domestic transshipment/feeder hub** (Krishnapatnam–Ennore–Chennai cluster is the natural candidate).

### 3.2 Last-mile & hinterland evacuation
Port efficiency gains (average major-port vessel turnaround fell ~18% to ~49 hours; JNPA/Mundra/Pipavud in World Bank CPPI top 30, 2025) are undermined beyond the port gate: inadequate rail sidings, road congestion at port gates, limited inland-waterway and coastal-shipping integration, and inefficient first/last-mile evacuation raise dwell time and logistics cost (IMPRI/Indian Ports Act 2025 analysis). The east-coast trunk rail (Howrah–Chennai) and NH16 run the length of the seaboard but are congested at port interfaces.

### 3.3 Draft & Ultra Large Container Vessel (ULCV) readiness
Only a few east-coast berths (Krishnapatnam, Dhamra, Gopalpur at 14.5 m; Vizag outer harbour SPM) take fully laden Super Capesize / large container vessels. Chennai and Kolkata are draft-constrained (tidal/riverine). To capture mainline calls rather than feeder-only calls, the seaboard needs sustained **dredging** and deeper container berths — a particular weakness for the Kolkata–Haldia riverine approach.

### 3.4 Cold chain & reefer logistics
Vizag is a pharma/API hub and the AP coast a major seafood/aquaculture exporter; both need **temperature-controlled "reefer" containers and cold-storage** at the port gate. Current provision is patchy (Reefer Express-style services exist but are not port-integrated), which forces time-sensitive exports through costlier routings.

### 3.5 Logistics cost
Traditional figure: **13–14% of GDP** vs 8–10% in advanced economies (US ~9.5%, Germany ~8%, Japan ~11%). Newer official estimates (DPIIT assessment; NCAER) put India at **~7.9–8.8% of GDP (2021–23)**, and PIB cites **7.97%**. Direction is improving, but the east coast's port-hinterland system is still a cost driver, not a cost cutter, for exporters.

### 3.6 Institutional coordination
Ports (Ministry of Ports, Shipping & Waterways), rail (Ministry of Railways), roads (NHAI), customs and state governments plan separately. The recurring failure mode is announced projects that stall at implementation (Sagarmala-linked port connectivity, rail evacuation, corridor nodes). PM Gati Shakti and the Indian Ports Act 2025/Major Port Authorities Act 2021 aim to fix this, but ground-level coordination remains the binding constraint (ORF, Nov 2025).

---

## 4. Port → industrial city linkages (the "sea leverage" chain)

| Seaboard node | Port(s) | Direct industrial city/cluster | What moves | What's missing for full leverage |
|---|---|---|---|---|
| Kolkata–Haldia | SMP Kolkata, Haldia DC | Kolkata, Durgapur–Asansol (WB), Jharkhand | Jute, tea, petrochemicals, chemicals, edible oils, containers to Nepal/Bhutan/Bangladesh | Draft, Hooghly navigation, mechanised container terminal, AKIC rail links |
| Paradip–Dhamra–Gopalpur | Paradip, Dhamra, Gopalpur | Bhubaneswar, Kalinganagar, Rourkela, Jharkhand, Chhattisgarh | Iron ore, coal, crude, steel slabs, cement, power | Dedicated mineral freight corridor, OEC node build-out, silo/loading capacity |
| Visakhapatnam | Vizag Port | Visakhapatnam, Vijayawada, Hyderabad (via rail) | Iron ore (Japan/Korea), POL/refinery, pharma APIs, seafood | Channel deepening, reefer/cold chain, pharma-grade logistics |
| Kakinada–Krishnapatnam | Krishnapatnam, Kakinada | Nellore, Tirupati, VCIC nodes | Containers, bulk, project cargo | VCIC node last-mile, NH16 + KRCL rail integration, transshipment feeder |
| Chennai–Ennore–Kattupalli–Tuticorin | Chennai, Kamarajar, Kattupalli, Tuticorin | Chennai, Bengaluru (CBIC), Coimbatore, Madurai | Autos, electronics, textiles, containers | "Detroit of Asia" export rail to Bengaluru, on-dock CFS, LUCV-ready berths |

**The lever:** a port only creates industrial value when the **dock-to-factory mile** is as efficient as the deep-sea leg. On the east coast today, the port side is modernising (Vizag, Krishnapatnam, Dhamra, Ennore), but the city/factory side is the bottleneck.

---

## 5. The best worldwide example of a really good seaboard

### 5.1 Primary benchmark: Port of Rotterdam (Netherlands)
Why it is the best *overall* seaboard model:
- **Hinterland integration, not just a port:** 5 port areas + 3 distribution parks; ~**500 million European consumers** in the hinterland; **428.4 Mt cargo (2025)**; 28,876 sea ships + **99,558 inland vessels (2021)**.
- **Modal balance:** rail (**Betuweroute** freight line "from sea to Zevenaar"), inland barge on the Rhine–Meuse–Scheldt delta, pipelines, and road (A15 bundled road+rail corridor) — no single-mode dependence.
- **Land scale:** 7,903 ha; Maasvlakte 2 reclamation for deep-draft ULCV terminals; Europort petrochemical/industrial cluster directly on the port.
- **Digital/smart port:** Port Vision, Digital Twin, real-time vessel/berth planning; ~49-hour turnaround comparable to India's best but at far larger scale and with full hinterland evacuation.
- **Green:** shore power, green shipping corridors, alternative-fuel bunkering, emissions reduction.

### 5.2 Secondary benchmarks
- **Singapore** — DNV–Menon *Leading Container Ports of the World* **#1 (2025)**; world's busiest **transshipment** port; automation, early alternative-fuel bunkering, green corridors, transparent governance. This is the transshipment model India needs (to replace Colombo dependence).
- **Shanghai (China)** — world's busiest container port (**51.5 M TEU 2024**); top **Liner Shipping Connectivity Index**; smart-tech ULCV handling. The scale/connectivity model.

**Verdict for India's east coast:** adopt **Rotterdam's port–hinterland–industry integration** as the master-plan template, **Singapore's transshipment hub discipline** for the container/feeder problem, and **Shanghai's deep-draft ULCV readiness** for terminal design.

---

## 6. Master plan: making India's eastern seaboard a sea-leverage platform

**Goal:** cut seaboard logistics cost, capture transshipment value, and bind each port directly to its industrial city/corridor node.

### Phase 1 (0–24 months): Fix the gate
1. **Dredge & deepen** Kolkata–Haldia (Hooghly approach), Chennai, Ennore and Vizag outer-harbour container berths to ULCV/Super-Capesize draft.
2. **Mechanise berths** at Haldia container terminal, Kolkata Netaji Subhas Dock, and Vizag; install reach stackers/RTGCs.
3. **Port gate decongestion:** appointment-slot systems, RFID/gate automation (Ennore/Kattupalli six-lane gate is the template), pre-gate customs clearance.
4. **Reefer/cold-chain pilot** at Vizag (pharma/seafood) and Tuticorin (fish/agri).

### Phase 2 (2–5 years): Build the rail–road spine
1. **Dedicated port rail evacuation:** double the Vizag–Krishnapatnam–Ennore rail links; on-dock rail sidings at Krishnapatnam, Dhamra, Gopalpur; extend Ennore–Bengaluru on-dock rail frequency.
2. **NH16 + Howrah–Chennai trunk de-bottlenecking** at all port interfaces (grade separators, dedicated port corridors).
3. **Coastal shipping & inland waterways:** National Waterway usage along the east coast to shift bulk (coal, iron ore, cement) off roads.
4. **PM Gati Shakti / NICDP coordination:** single-window clearance for port–corridor–node projects (VCIC, CBIC, OEC, AKIC).

### Phase 3 (3–7 years): Capture transshipment & port-led industry
1. **East-coast transshipment/feeder hub:** develop Krishnapatnam–Chennai–Ennore cluster as a regional feeder hub feeding mainline calls, reducing Colombo/Singapore dependence (target: cut the ~75% overseas transshipment share materially).
2. **VCIC node completion:** Visakhapatnam, Kakinada, Krishnapatnam, Yerpedu–Srikalahasti with plug-and-play industrial plots, power, water, and direct port rail/road links.
3. **OEC & AKIC nodes:** Paradip–Kendrapada–Dhamra–Subernarekha; Raghunathpur (WB) linked to Kolkata–Haldia.
4. **Galathea Bay (Great Nicobar)** transshipment port as the national hub, with east-coast feeder connectivity.

### Phase 4 (5–10 years): Rotterdam-style integration
1. **Distribution parks & logistics zones** adjacent to each major port (bonded warehouses, CFS, empty-container depots).
2. **Smart-port platform** across east-coast ports: single vessel-booking, berth and yard visibility, digital twin (Rotterdam model).
3. **Multi-modal shift target:** raise rail/inland-water share of port evacuation; lower logistics cost toward the 8–10% advanced-economy band.
4. **Bunkering & alternative fuels:** LNG/LNG-ready, methanol/ammonia bunkering at Vizag, Chennai, Paradip (green corridor with ASEAN).

### Success metrics (to track)
- Transshipment share handled in India (from ~25% domestic toward 50%+)
- Average vessel turnaround & port dwell time
- Rail share of port hinterland evacuation
- Logistics cost % of GDP (east-coast corridor)
- ULCV/Super-Capesize vessel calls at east-coast ports
- VCIC/OEC/AKIC node occupancy & export value

---

## 7. Data sources useful for this job (and for the indiamacro library)

These are the free, citable, online sources used above. They are candidates to be wrapped as `indiamacro` source modules (see §8).

| Source | What it gives | URL / notes | Frequency |
|---|---|---|---|
| **World Bank — Logistics Performance Index (LPI)** | Country logistics benchmarking (customs, infrastructure, tracking, timeliness); dwell time | lpi.worldbank.org | ~3-yearly (2023 latest) |
| **World Bank — Container Port Performance Index (CPPI)** | Port-level vessel time in port; JNPA 99.7 / Mundra 97.3 (2024); Visakhapatnam rank 18 (2023 UNCTAD/CPPI) | openknowledge.worldbank.org; documents1.worldbank.org | Annual (2020–2025) |
| **UNCTAD — Review of Maritime Transport** | Liner Shipping Connectivity Index (LSCI); port performance; maritime trade | unctad.org/rmt | Annual |
| **Ministry of Ports, Shipping & Waterways (India)** | Port capacity/throughput updates; Sagarmala; Maritime India Vision 2030/2047; transshipment share (~75% overseas, May 2025) | shipmin.nic.in; pib.gov.in | Annual/periodic |
| **Indian Ports Association (IPA)** | Major-port traffic and performance statistics | indianportsassociation.com | Monthly/annual |
| **Adani Ports (APSEZ) digital reports** | East-coast private port capacity/throughput (Krishnapatnam 59.2 MMT, Dhamra 48.8 MMT, Gopalpur 14.5 m draft, Kattupalli/Ennore) | adaniports.com | Annual |
| **NICDC (National Industrial Corridor Development Corp.)** | VCIC, CBIC, AKIC, OEC node project lists, area, cost, jobs | nicdc.in | Project-based |
| **Asian Development Bank (ADB)** | VCIC/ECEC financing and concept development plans | adb.org | Project-based |
| **PIB (Press Information Bureau)** | Industrial corridor projects, Sagarmala, port capacity ₹5.79 lakh crore/839 projects | pib.gov.in | Press releases |
| **ORF (Observer Research Foundation)** | ECEC port–industry synergy analysis (Nov 2025) | orfonline.org | Analysis |
| **DNV / Menon Economics — Leading Container Ports** | Singapore #1, Shanghai #2, Ningbo-Zhoushan #3, Rotterdam #4 (2025) | dnv.com | Annual (new 2025) |
| **UN Comtrade** | India's imports/exports by partner (crude suppliers etc.) | comtrade.un.org | Monthly (free tier limited) |
| **PPAC** | Indian crude basket (energy context for POL ports) | ppac.gov.in | Daily/monthly |

**Citation convention (per CLADE.md "Docs and tone"):** cite the original producer (e.g. "Ministry of Ports, Shipping and Waterways, accessed via PIB on 20 Nov 2026"), not this package; date live-data facts ("as of 20 Nov 2026").

---

## 8. Adding maritime/logistics data to the indiamacro library

Per `CLAUDE.md`, adding a source means: (1) new module in `src/indiamacro/sources/`, (2) export in `src/indiamacro/__init__.py`, (3) a `Check` in `ping.py`, (4) docs in `SOURCES.md`/`LIMITATIONS.md`, (5) offline tests in `tests/test_offline.py` using canned payloads. Note the known issue: `sources.energy` is not imported in `__init__.py`, so any new module (e.g. `maritime`) must be explicitly exported or imported ad hoc.

### Sketch — `src/indiamacro/sources/maritime.py` (convention-stub)

```python
"""Maritime and port-logistics indicators for India's seaboard.

Sources
  * worldbank   - Container Port Performance Index (vessel time in port)
  * worldbank   - Logistics Performance Index (country logistics)
  * unctad      - Liner Shipping Connectivity Index (LSCI)
  * shipmin/pib - Indian major-port capacity & throughput, Sagarmala updates
"""
from __future__ import annotations

import pandas as pd

from .. import _http
from ..utils import fy_label

SOURCE = "maritime"
BASE = "https://api.worldbank.org/v2"


def cppi(economy: str = "IND", year: int = 2024) -> pd.DataFrame:
    """Container Port Performance Index for India's ports (vessel time in port)."""
    ...
    df.attrs.update(source="World Bank CPPI", unit="index points", note="...")
    return df


def lpi(indicator: str, country: str = "IND") -> pd.DataFrame:
    """World Bank Logistics Performance Index."""
    ...


def lsci(country: str = "IND") -> pd.DataFrame:
    """UNCTAD Liner Shipping Connectivity Index."""
    ...
```

Each function returns long-format `date, country, series, value` (+ `port`, `base_year`, `projection` where relevant), with `df.attrs["source"]` set, dates as period-starts, and `_http.get_json(source=SOURCE, ttl=...)`. Offline tests would parse canned World Bank/UNCTAD JSON, never hit the network.

---

## 9. Limitations & caveats (to keep honest)

- **Cargo figures are FY22-23 for major ports** (Wikipedia) vs FY23-24/FY24-25 for some private ports (Adani) — do not splice across years without labelling.
- **Transshipment ~75% overseas** is a May 2025 press estimate; official figures vary by methodology.
- **Logistics cost % of GDP is contested** (13–14% traditional vs 7.9–8.8% newer NCAER/DPIIT vs PIB 7.97%) — state the definition used.
- **Galathea Bay phase 1 expected ~2028** — transshipment relief is not immediate.
- Port-led industrialisation depends on **state-level execution** (land, power, water) beyond the port's control.
- This report is an aggregation of secondary/public sources; verify against primary port authority data before citation in a formal study.

---

## 10. References (accessed 20 Nov 2026)

1. Wikipedia, "List of ports in India" — major-port cargo FY22-23 (Chennai 136, Kamarajar 91, Haldia 92.77, Kolkata 50.7, Visakhapatnam 143.68 MTPA).
2. Adani Enterprises, "Operational Performance — Ports" (2026) — Krishnapatnam, Dhamra, Gopalpur, Kattupalli, Ennore, Vizhinjam capacity/throughput.
3. ORF, "Assessing Port–Industry Synergy in India's East Coast Economic Corridor" (27 Nov 2025) — VCIC four nodes, port–industry thesis.
4. PIB, "Travelling Across the Industrial Corridors of India" — VCIC/CBIC/AKIC/OEC project lists.
5. Economic Times (infrastructure), "Logistics links, shipping services emerge as key drivers" — ~75% of transshipment containers overseas (May 2025), turnaround ~49 hours.
6. PIB / Shipmin India — India logistics cost 13–14% of GDP (traditional) vs developed 8–10%; US 9.5%, Germany 8%.
7. DPIIT "Assessment of Logistics Cost in India" — 8.84% of GDP (2022–23); NCAER 7.8–8.9% (2021–22); PIB 7.97%.
8. World Bank CPPI 2024/2025 — JNPA 99.7, Mundra 97.3; UNCTAD RMT 2024 ch.4 — Visakhapatnam CPPI rank 18 (129.6 pts).
9. DNV–Menon, "Leading Container Ports of the World" (2025) — Singapore #1, Shanghai #2, Rotterdam #4.
10. Wikipedia, "Port of Rotterdam" — 428.4 Mt (2025), 7,903 ha, 5 port areas, 3 distribution parks, 500 M hinterland consumers, 99,558 inland vessels (2021).
11. Ministry of Ports, Shipping & Waterways — Sagarmala (200+ connectivity projects), Maritime India Vision 2030/2047, Galathea Bay transshipment port; Indian Ports Act 2025; Major Port Authorities Act 2021.
12. IMPRI, "Indian Ports Act (2025): Reforming India's Port Governance" — hinterland connectivity & transshipment dependence gaps.

---
*End of report. Next step: convert §8 into a real `sources/maritime.py` module and register it, if the team wants live port-logistics indicators inside indiamacro.*
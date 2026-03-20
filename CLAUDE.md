# CLAUDE.md — Strava Fitness Analyzer

Project guidelines for Claude Code. Read this before making any changes.

---

## Core Philosophy

**Heuristic-first, no external AI.** Every insight is computed directly from the data using established sports science formulas and published population norms. No LLM API calls, no cloud services — just math the athlete can verify themselves.

**Opinionated and honest.** Don't soften findings. If someone is overreaching, say "OVERREACHED". If their sleep is poor, say "Poor". Use graded labels (Excellent / Good / Average / Below Average / Poor) backed by published sources.

**Raw data always, proprietary scores never.** Every fitness wearable sells a high-order "score" — Whoop's Recovery Score, Oura's Readiness Score, Garmin's Body Battery, Fitbit's Daily Readiness. These are black-box models trained on their own user populations, tuned for retention and marketing, and not reproducible. We extract the raw physiological signals (HRV in ms, RHR in bpm, sleep stage durations, skin temperature delta) and apply our own formulas grounded in published research. This is the entire point.

When adding a new data source:
- ✓ Extract: raw HRV (ms), raw RHR (bpm), sleep stage durations (min), temperature deviation (°C), SpO2 (%)
- ✗ Never import: Recovery Score, Readiness Score, Body Battery, Strain Score, Sleep Score from the vendor — these are their IP, not science

---

## Package Structure

```
analyze.py          ← thin argparse entry point (do not add logic here)
strava/
  utils.py          ← pure math helpers (no I/O)
  auth.py           ← Strava OAuth only
  fetch.py          ← Strava API calls only
  health_parse.py   ← Apple Health XML/zip → structured dicts
  health_analysis.py← cross-analysis: correlations, outliers, histograms, collisions
  benchmarks.py     ← population norms, sport profiles, goal evaluation
  race_predict.py   ← Riegel race time predictions, best-effort extraction
  export_data.py    ← CSV export of 90-day aligned series
  compute.py        ← master analyze() pipeline — calls all sub-modules
  report.py         ← Rich terminal output
  dashboard.py      ← self-contained HTML (Chart.js 4.4, no external deps at runtime)
  interact.py       ← --chat REPL, keyword intent parsing
```

**Rule:** Each module owns its domain. `compute.py` orchestrates but does not format output. `report.py` and `dashboard.py` read from `data` dict but never mutate it. `benchmarks.py` is pure functions — no I/O.

---

## Key Analysis Algorithms

### Training Load (CTL / ATL / TSB)
Banister TRIMP-based exponential rolling averages. Computed in `compute.py`.

```python
# TRIMP per activity
hrr = (avg_hr - rest_hr) / (max_hr - rest_hr)   # heart rate reserve
trimp = duration_min * hrr * 0.64 * exp(1.92 * hrr)

# Rolling averages over daily TRIMP array
ctl = rolling_avg(daily_trimp, 42)   # Chronic Training Load — fitness
atl = rolling_avg(daily_trimp, 7)    # Acute Training Load  — fatigue
tsb = ctl - atl                      # Training Stress Balance — form
```

### ACWR — Acute:Chronic Workload Ratio (Gabbett 2016)
Stored in `data["load"]["acwr"]` and `data["load"]["acwr_risk"]`.

```python
acwr = current_atl / current_ctl   # ATL ÷ CTL

# Risk bands:
# < 0.8   → "under"   (undertraining)
# 0.8–1.3 → "optimal" (sweet spot)
# 1.3–1.5 → "caution" (workload spike)
# > 1.5   → "high"    (critical injury risk — generates verdict flag)
```

### HRV Daily Readiness
Stored in `data["apple_health"]["hrv_readiness"]` (integer %).

```python
hrv_readiness = round(hrv_7d_avg / hrv_60d_baseline * 100)

# Thresholds:
# ≥ 95% → Ready (green)
# 80–94% → Reduced (yellow)
# < 80%  → Low — consider rest (red)
```

### Race Time Predictions — Riegel Formula
Implemented in `strava/race_predict.py`.

```python
T2 = T1 × (D2 / D1) ^ 1.06     # Riegel 1981

# Reference: Peter Riegel, "Athletic Records and Human Endurance", American Scientist 1981
# Accuracy note: degrades when ratio D2/D1 > 4× (flagged as ratio_warning=True)
```

Distance bins for best-effort matching (activity distance must fall within):
- 5K: 4500–5800 m
- 10K: 9000–11000 m
- Half Marathon: 19000–22500 m
- Marathon: 40000–44000 m

`data["race_predictions"]` keys: `best_efforts`, `predictions`
Each prediction has: `time_str`, `pace_str`, `ref_name`, `ref_date`, `is_actual`, `ratio_warning`

### CSV Export
`python analyze.py --export` → `strava_analysis.csv`

Columns: `date, ctl, atl, tsb, acwr, rhr, hrv, hrv_readiness, sleep_h, sleep_score, deep_pct, rem_pct, km_trained`

Falls back to load-series only (no health columns) if Apple Health data is absent.

### Form status thresholds:
- TSB > 10   → FRESH (good to race)
- TSB > -10  → NEUTRAL
- TSB > -25  → TIRED
- TSB ≤ -25  → OVERREACHED (flag as critical)

### Sleep Score (0–100)
Computed per night from Apple Watch stage data. Implemented in `health_parse.py`.

```python
dur_score  = max(0.0, 40.0 * (1.0 - abs(total_h - 8.0) / 4.0))  # peaks at 8h
eff_score  = min(20.0, efficiency * 23.5)                          # target ≥ 85%
deep_score = min(20.0, deep_pct / 20.0 * 20.0)  # target 20% deep
rem_score  = min(20.0, rem_pct  / 22.0 * 20.0)  # target 22% REM
score = round(dur_score + eff_score + deep_score + rem_score)
```

Night date assignment: if wake-up time is between 03:00–14:00, use the wake-up date as the canonical "night of" date. Otherwise use start date.

Sleep stage values from Apple Health XML:
- 0 = InBed, 1 = Asleep (legacy → treat as Core), 2 = Awake
- 3 = Core, 4 = Deep, 5 = REM

### Health × Training Correlations (14 pairs)
Pearson r computed inline (no scipy). Minimum 10 paired data points required.
Defined in `health_analysis.py` as `CORR_DEFS`:

```
("Resting HR",  "ATL (fatigue)",  "rhr", "atl", expected="pos")
("Resting HR",  "TSB (form)",     "rhr", "tsb", expected="neg")
("Resting HR",  "CTL (fitness)",  "rhr", "ctl", expected="neg")
("HRV",         "ATL (fatigue)",  "hrv", "atl", expected="neg")
("HRV",         "TSB (form)",     "hrv", "tsb", expected="pos")
("HRV",         "CTL (fitness)",  "hrv", "ctl", expected="pos")
("Sleep h",     "ATL (fatigue)",  "sleep","atl", expected=None)
("Sleep h",     "TSB (form)",     "sleep","tsb", expected=None)
("Sleep score", "ATL (fatigue)",  "sleep_score","atl", expected="neg")
("Sleep score", "TSB (form)",     "sleep_score","tsb", expected="pos")
("Sleep score", "HRV",            "sleep_score","hrv", expected="pos")
("Deep %",      "ATL (fatigue)",  "deep_pct","atl",    expected="neg")
("REM %",       "TSB (form)",     "rem_pct","tsb",      expected="pos")
("Resting HR",  "km trained",     "rhr","km",           expected="pos")
```

### Outlier Detection
IQR method over 90-day aligned window. Applied to: rhr, hrv, sleep, sleep_score.
```python
lo, hi = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
```

### Stress Collision Events
Days where ≥ 3 of these signals coincide (75th/25th percentile thresholds):
- ATL ≥ 75th pct  → "High fatigue (ATL)"
- RHR ≥ 75th pct  → "Elevated RHR"
- HRV ≤ 25th pct  → "Suppressed HRV"
- Sleep ≤ 25th pct → "Poor sleep"
- TSB < -15        → "Negative form (TSB)"

Severity: "critical" if ≥ 4 signals, else "warning".

---

## Population Norms (sources)

**VO2max** — ACSM Guidelines for Exercise Testing and Prescription, 11th ed.
Thresholds by age bracket × sex in `benchmarks._VO2MAX_M` / `_VO2MAX_F`.

**Resting HR** — AHA categories:
- < 50 = Athlete, 50–59 = Excellent, 60–69 = Good, 70–79 = Average, 80–89 = Below Average, ≥ 90 = Poor

**HRV (SDNN)** — Shaffer & Ginsberg 2017:
- ≥ 50 ms = Good, 30–49 ms = Average, < 30 ms = Poor

**Sleep score** grades:
- ≥ 85 = Excellent, ≥ 75 = Good, ≥ 60 = Fair, ≥ 45 = Poor, < 45 = Very Poor

---

## Sport Profiles (10 events)

Defined in `benchmarks.SPORT_PROFILES`. Each profile has:
`min_ctl`, `weekly_run_km`, `weekly_ride_km`, `long_run_km`, `long_ride_km`, `swim_sessions`, `notes`

| Sport | Min CTL | Weekly run | Long run |
|---|---|---|---|
| 5K | 20 | 30 km | 12 km |
| 10K | 25 | 40 km | 16 km |
| Half Marathon | 35 | 55 km | 21 km |
| Marathon | 50 | 70 km | 30 km |
| Sprint Tri | 25 | 20 km + 60 km bike | — |
| Olympic Tri | 40 | 30 km + 100 km bike | — |
| Half Ironman | 60 | 45 km + 160 km bike | — |
| Ironman | 80 | 55 km + 230 km bike | — |
| Gran Fondo | 45 | — | 100 km ride |
| General Fitness | 15 | 15 km | — |

Gap urgency: urgent if current < 40% of requirement, gap if current < 70%.
Readiness score: `max(0, 100 - n_gaps * 15 - n_urgent * 20)`

---

## UI Style Guide

### Terminal (Rich)
- **Box styles**: `rbox.ROUNDED` for all content panels, `rbox.HEAVY_HEAD` for the header, `rbox.HEAVY` for the final verdict panel
- **Title style**: `[bold cyan]SECTION NAME[/bold cyan]`
- **Status colors**: green = good, yellow = warning, red = critical/bad
- **Progress bars**: `█` filled, `░` empty — always 20–22 chars wide
- **Current week marker**: `◄` appended in `bright_green`
- **Apple Health panel title**: `[bold magenta]APPLE HEALTH[/bold magenta]`
- **Verdict panel**: `[bold white]VERDICT[/bold white]`, box style `HEAVY`

Status color mapping:
```
green       → improving HR efficiency, active weeks ≥ 10, good sleep, CTL building
yellow      → warnings, declining trends, moderate gaps
red         → critical flags, poor metrics, urgent gaps
bold red    → OVERREACHED, critical verdict items
dim         → secondary info, zero weeks, missing data
```

### HTML Dashboard
- **Color palette** (CSS vars):
  ```
  --bg: #0d0f1a        dark navy background
  --card: #13162a      card surface
  --border: #1e2235    subtle borders
  --orange: #FC4C02    Strava brand color (stat values, CTL bars)
  --green: #22c55e     positive / CTL line
  --red: #ef4444       negative / ATL line
  --yellow: #f59e0b    warnings
  --blue: #60a5fa      hours line, HRV
  --purple: #a78bfa    sleep score, weight
  --muted: #64748b     labels, secondary text
  ```
- **Grid**: 4-column CSS grid, cards use `.s1` `.s2` `.s3` `.s4` span classes
- **Charts**: Chart.js 4.4.0 from jsdelivr CDN — bar, line, scatter, no pie
- **Data injection**: `__CHART_DATA__` placeholder replaced by `json.dumps(payload)` — never use f-strings on the HTML template (CSS curly braces conflict)
- **Benchmarks card**: readiness bars use `.rbar` / `.rbar-bg` / `.rbar-fill` classes with inline color

### Verdict / Flag Priorities
Always list critical before warning before good. Icons:
- `⚡` critical (bold red)
- `⚠ ` warning (yellow)
- `✓ ` good (bold green)

---

## Data Flow

```
fetch_activities()  ──┐
fetch_athlete()     ──┤
                      ├─→ compute.analyze() ──→ data dict
load_apple_health() ──┘        │
                               ├─→ health_analysis.cross_analyze()
                               ├─→ race_predict.predict_races()
                               ├─→ benchmarks.assess_athlete()
                               └─→ benchmarks.sport_recommendations()

data dict ──→ report.print_report()     (terminal)
          ──→ dashboard.generate_html() (HTML file)
          ──→ interact.run_chat()        (REPL reads data, calls benchmarks)
          ──→ export_data.export_csv()   (--export flag)
```

`data` dict keys:
`overview`, `weekly`, `load` (includes `acwr`, `acwr_risk`), `load_series`, `hr`, `zones`,
`running`, `cycling`, `swimming`, `consistency`,
`apple_health` (includes `hrv_readiness`), `health_analysis`,
`race_predictions`, `benchmarks`, `sport_recs`, `verdict`

---

## --chat REPL Intent Patterns

Keyword matching in `benchmarks.match_sport()`. Key triggers:

| Keywords | → Sport |
|---|---|
| "marathon", "42k", "26.2" | Marathon |
| "half marathon", "21k", "hm" | Half Marathon |
| "10k", "ten k" | 10K |
| "5k", "parkrun" | 5K |
| "ironman", "140.6" | Ironman |
| "70.3", "half ironman", "half im" | Half Ironman |
| "olympic tri", "oly tri" | Olympic Triathlon |
| "sprint tri" | Sprint Triathlon |
| "gran fondo", "century ride" | Gran Fondo |
| "fitness", "get fit", "lose weight" | General Fitness |

Special commands (checked before sport matching):
- Contains "recommend" / "what should" / "suggest" → `_show_recommendations()`
- Contains "benchmark" / "norms" / "compare me" → `_show_benchmarks()`
- Contains "help" → `_show_help()`

---

## What NOT to Change

- **No scipy / pandas / numpy** — all math is inline Python. Keep it that way for portability.
- **No external AI API calls** — heuristic-only is a core design constraint.
- **CLIENT_ID / CLIENT_SECRET in auth.py** — these are personal Strava API credentials, do not rotate or move them.
- **`__CHART_DATA__` placeholder** — do not convert the HTML template to an f-string; CSS `{}` will break it.
- **Sleep stage int mapping** — Apple Health uses 0–5, not string labels. Do not change the mapping.
- **Token file name** `strava_token.json` — hardcoded in auth.py, excluded from git.

---

## CLI Reference

```
python analyze.py              # Rich terminal report
python analyze.py --html       # Generate + open dashboard.html
python analyze.py --chat       # Interactive goal assessment REPL
python analyze.py --export     # Export 90-day series to strava_analysis.csv
python analyze.py --months 6   # Limit to last N months (default 12)
```

---

## Feature Request Log

Tracks the owner's prompts in their own words. When building something new, check here first for context and intent. Mark completed items `[x]`, in-progress `[~]`, pending `[ ]`.

---

### Completed

**[x] Beautify the analysis results**
> "Beautify the analysis results"

Rebuilt terminal output using `rich` — panels, colored metrics, progress bars, badge-style status indicators.

---

**[x] Apple Health integration**
> "Also consider adding my apple health data"

Parses `export.zip` / `export.xml`. Extracts resting HR, HRV, VO2max, weight, and full sleep stage breakdown (Deep, REM, Core, Awake). Per-night sleep score 0–100.

---

**[x] HTML dashboard**
> "Can you generate an HTML based dashboard for me to check data and trend"

Self-contained `dashboard.html` via `--html`. Chart.js 4.4, dark theme. All charts embedded inline — no server needed, no external runtime dependencies.

---

**[x] Health × Strava cross-analysis**
> "Add Apple Health measurement, identify trend colliding with Strava and find outlier and distribution"

14 Pearson correlations, IQR outlier detection on RHR / HRV / sleep / sleep score, 12-bin histograms, stress collision event detector (3+ signals coinciding).

---

**[x] Sleep score in analysis**
> "Make sure the sleep analysis data like its score is in the analysis"

Sleep score (0–100) propagated through terminal report, HTML dashboard, cross-analysis correlations, outlier detection, and histograms.

---

**[x] Benchmarks + interactive goal chat**
> "Next step is to parse articles from JAMA, Men's Health, Runner's World to put the data and trend into general public and verdict what kind of sports I need to test next"
> "I also want some interaction like: I want to do xxx, can you give me a verdict with this idea"

Built population norms from published sources (ACSM, AHA, Shaffer & Ginsberg) rather than scraping articles. 10 sport profiles from 5K to Ironman with gap analysis and readiness scores. `--chat` REPL with keyword intent parsing.

---

**[x] Refactor**
> "Also refactor the code, it is huge and unreadable"

Split 1835-line monolithic `analyze.py` into `strava/` package with 13 focused modules. Each module owns one domain. Thin entry point with argparse.

---

**[x] ACWR injury risk, HRV readiness, race predictions, CSV export**
> "Build what you will actually do first" (following: ACWR, export CSV, race predictor, HRV readiness score)

- ACWR: ATL/CTL with Gabbett 2016 injury bands, verdict flags at >1.3 and >1.5
- HRV readiness: 7-day vs personal 60-day baseline, shown as %
- Race predictor: Riegel formula T₂ = T₁ × (D₂/D₁)^1.06, auto-detects best efforts
- CSV export: `--export` → `strava_analysis.csv` with all aligned training + health columns

---

### Pending / Partially done

**[ ] Article parsing from fitness publications**
> "Parse articles from JAMA, Men's Health, Runner's World to put the data and trend into general public"

The benchmarks module uses published norms directly from source papers. What's NOT done: scraping/parsing live articles, extracting study findings programmatically, or mapping article claims to the user's personal metrics with citations. If implementing: store parsed findings in `strava/articles.py` as structured dicts (metric, threshold, source, url), surface them in the `--chat` REPL when discussing a goal.

---

**[ ] Time series / pattern recognition for other domains**
> "I'm thinking of using data science or pattern recognition to analyze some of my trend curves. So I can reuse a lot of ideas from this app in other time series analysis such as stock market"

CSV export (`--export`) was added as the enabling step. The architecture discussion established: CTL/ATL/TSB ≡ slow/fast EMA / MACD; IQR outliers transfer cleanly; collision events transfer if signals are independent. Key caution: fitness correlations have physiological ground truth; market correlations are regime-dependent and adversarial. A separate repo is the right call — don't pollute this one with market logic.

---

### Suggested backlog (not yet requested)

These were proposed by Claude and not yet actioned. Add a date and move to Pending when you decide to build one.

**[ ] Periodization detector** — sliding window over weekly CTL to identify base / build / peak / taper / recovery blocks. Flag if in a build block > 6 weeks without a step-back week.

**[ ] Recovery curve projector** — forward-simulate TSB assuming zero training for 14 days. Answer: "when will I be fresh?"

**[ ] Personal Best tracker** — fastest average-pace efforts by distance bracket with CTL/TSB context at the time of each PR.

**[ ] Garmin Connect integration** — `garminconnect` Python library. Unlocks running dynamics (vertical oscillation, GCT, stride ratio), overnight HRV, power for cycling. `health_parse.py` architecture absorbs it cleanly.

**[ ] Periodization planner** — given current CTL, target sport, race date → generate week-by-week CTL target curve using sport profile min_ctl as the peak.

**[ ] Garmin Connect integration**
Library: `garminconnect` (Python, unofficial but stable).
Raw data to extract: running dynamics (vertical oscillation, ground contact time, stride ratio), overnight HRV, sleep stages, VO2max estimate, training history.
Skip entirely: Body Battery, Training Readiness Score, Training Load Focus, Performance Condition — all proprietary Garmin models.
Priority: high. Garmin is the dominant device among serious runners and triathletes who are the core users.

**[ ] Whoop integration**
API: unofficial (`whoop-python` or direct REST).
Raw data to extract: overnight HRV (5-min intervals → compute RMSSD), RHR, sleep stages (SWS / REM / Light / Awake durations), respiratory rate, skin temperature.
Skip entirely: Recovery Score (0–100%), Strain Score, Sleep Performance % — Whoop's proprietary black boxes, tuned for engagement not physiology.
Note: Whoop's marketing leans heavily on Recovery Score. Their raw HRV and sleep stage data is what's actually valuable.

**[ ] Oura Ring integration**
API: official Oura REST v2 (personal access token, free tier available).
Raw data to extract: overnight HRV (RMSSD), RHR, skin temperature deviation from baseline (°C), sleep stage durations, respiratory rate, SpO2.
Skip entirely: Readiness Score, Sleep Score, Activity Score — all Oura proprietary composites.
Note: Oura temperature deviation is uniquely useful — it's a leading indicator of illness and menstrual cycle phase that no other consumer device surfaces as well.

**[ ] Polar integration**
API: Accesslink API (OAuth2, official).
Raw data to extract: nightly HRV (RMSSD from orthostatic test), sleep staging, training session HR data.
Skip entirely: Recovery Pro score, Nightly Recharge — Polar proprietary.
Note: Polar's orthostatic test (lying → standing HR delta) is a validated readiness protocol worth surfacing if the user does it.

**[ ] Withings integration**
API: official Health Mate API (OAuth2).
Raw data to extract: body weight, body fat %, muscle mass, blood pressure, resting HR from smart scale, sleep stages from Sleep Analyzer mat.
Skip entirely: their Wellness Score.
Note: Withings scale body composition is the best consumer-grade weight + fat % data. Useful for tracking body composition alongside training load.

**[ ] Setup wizard** — `python setup.py` interactive flow: walks through Strava OAuth, locates Apple Health export, writes a config file. No source code editing required. Removes the credential-in-source-code barrier for non-technical users.

**[ ] Web UI / local server** — simple Flask dev server serving the dashboard locally with live data refresh. Removes the CLI barrier entirely. Prerequisite: setup wizard should land first.

---

### How to add a new request

When you ask Claude to build something new, paste your prompt here under **Pending** with a date:

```
**[ ] <feature name>** — <date>
> "your exact words"

<one sentence on intent>
```

Claude will move it to Completed with implementation notes when done.

---

## When Adding New Features

1. **New metric from Apple Health** → add to `QUANTITIES` dict in `health_parse.py`, then propagate through `compute.py` enrichment section and add to `data["apple_health"]`
2. **New correlation pair** → add tuple to `CORR_DEFS` list in `health_analysis.py`
3. **New sport profile** → add entry to `SPORT_PROFILES` dict in `benchmarks.py`, add keywords to `_SPORT_KEYWORDS`
4. **New terminal panel** → add to `print_report()` in `report.py`, follow ROUNDED box style with bold cyan title
5. **New HTML card** → add HTML markup in `_HTML` template in `dashboard.py`, add JS block, add key to `payload` dict in `generate_html()`
6. **New verdict flag** → add to the verdict block at the bottom of `compute.analyze()`

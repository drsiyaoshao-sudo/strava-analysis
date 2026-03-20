# Strava Fitness Analyzer

Personal fitness analyzer built on Strava + Apple Health data. No external AI — every insight is computed directly from your data using established sports science formulas.

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue) ![License MIT](https://img.shields.io/badge/license-MIT-green)

---

## What it does

**Terminal report** — rich, color-coded analysis you can read in 60 seconds

**HTML dashboard** — interactive charts you can open in any browser, no server needed

**Goal assessment REPL** — tell it what you want to do, get a data-backed verdict

**CSV export** — dump your aligned training + health series for further analysis

---

## Features

### Training analysis
- **CTL / ATL / TSB** — Banister TRIMP-based fitness, fatigue, and form (42-day / 7-day rolling averages)
- **ACWR** — Acute:Chronic Workload Ratio with Gabbett 2016 injury risk bands
- **Intensity zones** — Z1–Z5 distribution with polarized model verdict
- **HR efficiency trend** — aerobic efficiency improving or declining across time
- **Consistency** — active weeks, streak, gaps, training monotony score
- **Race time predictions** — Riegel formula projections (5K → Marathon) from your actual best efforts

### Apple Health integration
- **Resting HR** — 30-day trend vs prior month
- **HRV (SDNN)** — trend + daily readiness score (7-day vs personal 60-day baseline)
- **VO2max** — Apple Watch estimate
- **Sleep staging** — Deep %, REM %, Core %, efficiency, per-night score 0–100
- **Weight** — 14-day avg with monthly delta

### Health × Training cross-analysis
- **14 Pearson correlations** — HRV vs ATL, RHR vs TSB, Sleep score vs form, etc.
- **IQR outlier detection** — flags anomalous days in RHR, HRV, sleep, sleep score
- **Metric distributions** — 12-bin histograms over the last 90 days
- **Stress collision events** — days where 3+ signals (high ATL, elevated RHR, suppressed HRV, poor sleep, negative TSB) coincide simultaneously

### Benchmarks & goal assessment
- **Population norms** — ACSM VO2max tables by age/sex, AHA RHR categories, Shaffer HRV norms
- **10 sport profiles** — from 5K to Ironman 140.6; gap analysis vs your current fitness
- **Interactive REPL** (`--chat`) — "I want to do a marathon" → readiness score, gaps, timeline

---

## Setup

### 1. Install dependencies

```bash
pip install requests rich
```

### 2. Create a Strava API application

1. Go to [strava.com/settings/api](https://www.strava.com/settings/api)
2. Create an app — set **Authorization Callback Domain** to `localhost`
3. Copy your **Client ID** and **Client Secret** into `strava/auth.py`

```python
CLIENT_ID     = "your_client_id"
CLIENT_SECRET = "your_client_secret"
```

### 3. (Optional) Export Apple Health data

On your iPhone: **Health app → profile picture → Export All Health Data**

Place `export.zip` in the project folder or `~/Downloads/`. The analyzer finds it automatically.

---

## Usage

```bash
# Rich terminal report (default)
python analyze.py

# Open interactive HTML dashboard
python analyze.py --html

# Interactive goal assessment chat
python analyze.py --chat

# Export 90-day aligned series to CSV
python analyze.py --export

# Limit history to last N months
python analyze.py --months 6
```

### --chat examples

```
You: I want to run a marathon
You: can I do an Ironman?
You: show recommendations
You: benchmark me
You: quit
```

---

## How the numbers are calculated

### TRIMP (Training Impulse)
```
hrr   = (avg_hr - rest_hr) / (max_hr - rest_hr)
trimp = duration_min × hrr × 0.64 × e^(1.92 × hrr)
```

### CTL / ATL / TSB
```
CTL = 42-day rolling average of daily TRIMP  (chronic fitness)
ATL =  7-day rolling average of daily TRIMP  (acute fatigue)
TSB = CTL − ATL                              (form)
ACWR = ATL / CTL                             (injury risk: optimal 0.8–1.3)
```

### Sleep score (0–100)
```
Duration score   = 40 pts  (peaks at 8h, decays either side)
Efficiency score = 20 pts  (target ≥ 85%)
Deep sleep score = 20 pts  (target 20% of total)
REM score        = 20 pts  (target 22% of total)
```

### Race predictions — Riegel formula
```
T₂ = T₁ × (D₂ / D₁)^1.06
```
Reference: Peter Riegel, *American Scientist* 1981. Most accurate within 3× the reference distance.

### HRV readiness
```
readiness = (7-day HRV avg) / (personal 60-day baseline) × 100
≥ 95% Ready  ·  80–94% Reduced  ·  < 80% Low
```

---

## Population norm sources

| Metric | Source |
|---|---|
| VO2max by age/sex | ACSM Guidelines for Exercise Testing and Prescription, 11th ed. |
| Resting HR categories | American Heart Association |
| HRV (SDNN) | Shaffer & Ginsberg, *Frontiers in Public Health* 2017 |
| ACWR injury risk | Gabbett, *British Journal of Sports Medicine* 2016 |
| Riegel exponent | Riegel, *American Scientist* 1981 |

---

## Project structure

```
analyze.py              Entry point (argparse)
strava/
  auth.py               Strava OAuth 2.0
  fetch.py              Strava API
  health_parse.py       Apple Health XML/zip parser
  health_analysis.py    Correlations, outliers, histograms, collision events
  race_predict.py       Riegel race time predictions
  export_data.py        CSV export
  compute.py            Master analysis pipeline
  benchmarks.py         Population norms + sport profiles
  report.py             Rich terminal report
  dashboard.py          Self-contained HTML dashboard
  interact.py           --chat REPL
  utils.py              Math helpers (TRIMP, rolling avg, pace formatting)
```

---

## CSV export columns

`date, ctl, atl, tsb, acwr, rhr, hrv, hrv_readiness, sleep_h, sleep_score, deep_pct, rem_pct, km_trained`

Useful as input for further time series analysis — the ACWR, CTL/ATL/TSB, and HRV readiness columns are structurally similar to momentum / moving-average signals used in other domains.

---

## Security note

`strava_token.json` is excluded from git (contains your OAuth access token). Never commit it.

---

## License

MIT

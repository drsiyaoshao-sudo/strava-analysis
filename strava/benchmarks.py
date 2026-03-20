"""
benchmarks.py — Population norms and sport readiness profiles.

Sources:
  - ACSM Guidelines for Exercise Testing and Prescription, 11th ed.
  - Shaffer & Ginsberg 2017 (HRV/SDNN norms)
  - AHA resting heart rate categories
"""
from __future__ import annotations


# ── VO2max norms (ACSM, mL/kg/min) ──────────────────────────────────────────
# Thresholds: (excellent, good, above_avg, average, below_avg)
# Below below_avg → "Poor"

_VO2MAX_M: dict[tuple[int, int], tuple[int, int, int, int, int]] = {
    (18, 25): (60, 52, 47, 42, 37),
    (26, 35): (56, 49, 43, 40, 35),
    (36, 45): (51, 43, 39, 35, 31),
    (46, 55): (45, 39, 36, 32, 28),
    (56, 65): (41, 36, 32, 30, 26),
    (66, 99): (37, 33, 29, 26, 22),
}
_VO2MAX_F: dict[tuple[int, int], tuple[int, int, int, int, int]] = {
    (18, 25): (56, 47, 42, 38, 33),
    (26, 35): (52, 45, 38, 35, 31),
    (36, 45): (45, 38, 34, 31, 26),
    (46, 55): (40, 34, 31, 28, 23),
    (56, 65): (37, 32, 28, 25, 22),
    (66, 99): (32, 28, 25, 22, 19),
}


def _vo2max_rating(vo2: float, age: int = 35, sex: str = "M") -> str:
    table = _VO2MAX_M if sex.upper() != "F" else _VO2MAX_F
    thresholds = None
    for (lo, hi), t in table.items():
        if lo <= age <= hi:
            thresholds = t
            break
    if thresholds is None:
        thresholds = list(table.values())[-1]
    exc, gd, abv, avg, blw = thresholds
    if vo2 >= exc:  return "Excellent"
    if vo2 >= gd:   return "Good"
    if vo2 >= abv:  return "Above Average"
    if vo2 >= avg:  return "Average"
    if vo2 >= blw:  return "Below Average"
    return "Poor"


# ── Resting HR categories (AHA) ──────────────────────────────────────────────
def _rhr_rating(rhr: float) -> str:
    if rhr < 50:  return "Athlete"
    if rhr < 60:  return "Excellent"
    if rhr < 70:  return "Good"
    if rhr < 80:  return "Average"
    if rhr < 90:  return "Below Average"
    return "Poor"


# ── HRV norms (Shaffer & Ginsberg 2017, SDNN ms) ────────────────────────────
def _hrv_rating(hrv: float) -> str:
    if hrv >= 50:  return "Good"
    if hrv >= 30:  return "Average"
    return "Poor"


# ── Sleep score grades ────────────────────────────────────────────────────────
def _sleep_grade(score: float) -> tuple[str, str]:
    """Returns (grade, color_key)."""
    if score >= 85:  return "Excellent", "green"
    if score >= 75:  return "Good",      "green"
    if score >= 60:  return "Fair",      "yellow"
    if score >= 45:  return "Poor",      "red"
    return "Very Poor", "red"


# ── Sport profiles ────────────────────────────────────────────────────────────
SPORT_PROFILES: dict[str, dict] = {
    "5K": {
        "label": "5K Race",
        "min_ctl": 20, "weekly_run_km": 30, "weekly_ride_km": 0,
        "long_run_km": 12, "long_ride_km": 0, "swim_sessions": 0,
        "notes": "Speed emphasis over 4–6 weeks; 3 runs/wk including intervals",
        "gap_checks": ["ctl", "weekly_run_km", "long_run_km"],
    },
    "10K": {
        "label": "10K Race",
        "min_ctl": 25, "weekly_run_km": 40, "weekly_ride_km": 0,
        "long_run_km": 16, "long_ride_km": 0, "swim_sessions": 0,
        "notes": "Threshold work 2×/wk; long run ≥16 km at easy pace",
        "gap_checks": ["ctl", "weekly_run_km", "long_run_km"],
    },
    "Half Marathon": {
        "label": "Half Marathon",
        "min_ctl": 35, "weekly_run_km": 55, "weekly_ride_km": 0,
        "long_run_km": 21, "long_ride_km": 0, "swim_sessions": 0,
        "notes": "16–20 wk build; long run ≥21 km; tempo 1×/wk",
        "gap_checks": ["ctl", "weekly_run_km", "long_run_km"],
    },
    "Marathon": {
        "label": "Marathon",
        "min_ctl": 50, "weekly_run_km": 70, "weekly_ride_km": 0,
        "long_run_km": 30, "long_ride_km": 0, "swim_sessions": 0,
        "notes": "20+ wk plan; long run ≥30 km; back-to-back weekends helpful",
        "gap_checks": ["ctl", "weekly_run_km", "long_run_km"],
    },
    "Sprint Triathlon": {
        "label": "Sprint Triathlon",
        "min_ctl": 25, "weekly_run_km": 20, "weekly_ride_km": 60,
        "long_run_km": 8, "long_ride_km": 30, "swim_sessions": 2,
        "notes": "750m swim / 20km bike / 5km run; 10 wk multi-sport base",
        "gap_checks": ["ctl", "weekly_run_km", "weekly_ride_km"],
    },
    "Olympic Triathlon": {
        "label": "Olympic Triathlon",
        "min_ctl": 40, "weekly_run_km": 30, "weekly_ride_km": 100,
        "long_run_km": 12, "long_ride_km": 60, "swim_sessions": 3,
        "notes": "1500m / 40km / 10km; 16 wk plan; brick sessions critical",
        "gap_checks": ["ctl", "weekly_run_km", "weekly_ride_km"],
    },
    "Half Ironman": {
        "label": "Half Ironman (70.3)",
        "min_ctl": 60, "weekly_run_km": 45, "weekly_ride_km": 160,
        "long_run_km": 20, "long_ride_km": 90, "swim_sessions": 3,
        "notes": "1.9km / 90km / 21km; 20–24 wk plan; 12+ h/wk training",
        "gap_checks": ["ctl", "weekly_run_km", "weekly_ride_km", "long_ride_km"],
    },
    "Ironman": {
        "label": "Ironman 140.6",
        "min_ctl": 80, "weekly_run_km": 55, "weekly_ride_km": 230,
        "long_run_km": 30, "long_ride_km": 150, "swim_sessions": 4,
        "notes": "3.8km / 180km / 42km; 28–32 wk plan; lifestyle commitment",
        "gap_checks": ["ctl", "weekly_run_km", "weekly_ride_km", "long_ride_km"],
    },
    "Gran Fondo": {
        "label": "Gran Fondo (130km+)",
        "min_ctl": 45, "weekly_run_km": 0, "weekly_ride_km": 180,
        "long_run_km": 0, "long_ride_km": 100, "swim_sessions": 0,
        "notes": "12–16 wk build; weekly long rides ≥100 km; climbing volume",
        "gap_checks": ["ctl", "weekly_ride_km", "long_ride_km"],
    },
    "General Fitness": {
        "label": "General Fitness",
        "min_ctl": 15, "weekly_run_km": 15, "weekly_ride_km": 0,
        "long_run_km": 6, "long_ride_km": 0, "swim_sessions": 0,
        "notes": "150+ min/wk moderate activity (WHO guideline); mix modalities",
        "gap_checks": ["ctl"],
    },
}

# ── Keyword → sport mapping ────────────────────────────────────────────────────
_SPORT_KEYWORDS: dict[str, list[str]] = {
    "5K":               ["5k", "5 km", "five k", "parkrun", "five kilometer"],
    "10K":              ["10k", "10 km", "ten k", "ten kilometer"],
    "Half Marathon":    ["half marathon", "half", "21k", "21 km", "1/2 marathon", "hm"],
    "Marathon":         ["marathon", "42k", "42 km", "full marathon", "26.2"],
    "Sprint Triathlon": ["sprint tri", "sprint triathlon"],
    "Olympic Triathlon":["olympic tri", "olympic triathlon", "oly tri"],
    "Half Ironman":     ["70.3", "half iron", "half ironman", "half im"],
    "Ironman":          ["ironman", "140.6", "full iron", "full im", " im "],
    "Gran Fondo":       ["gran fondo", "sportive", "century ride", "granfondo", "century"],
    "General Fitness":  ["fitness", "get fit", "lose weight", "stay active", "health"],
}


def match_sport(text: str) -> str | None:
    """Return sport name from free-text input, or None."""
    t = text.lower()
    for sport, keywords in _SPORT_KEYWORDS.items():
        for kw in keywords:
            if kw in t:
                return sport
    return None


# ── Gap analysis ───────────────────────────────────────────────────────────────
def _gap_analysis(profile: dict, data: dict) -> list[dict]:
    """Compare current fitness vs sport profile. Returns list of gap dicts."""
    gaps = []
    ld  = data.get("load", {})
    wk  = data.get("weekly", {})
    run = data.get("running") or {}
    ride = data.get("cycling") or {}

    current_ctl = ld.get("ctl", 0)
    req_ctl = profile["min_ctl"]
    if current_ctl < req_ctl:
        pct = int(req_ctl / max(current_ctl, 1) * 100 - 100)
        gaps.append({
            "metric": "Training Load (CTL)",
            "current": f"{current_ctl:.0f}",
            "required": f"{req_ctl}",
            "gap": f"+{pct}% needed",
            "urgent": pct > 100,
        })

    km_list = wk.get("km", [])
    avg_km = sum(km_list) / max(len(km_list), 1) if km_list else 0
    req_run = profile["weekly_run_km"]
    if req_run > 0 and avg_km < req_run * 0.7:
        gaps.append({
            "metric": "Weekly running km",
            "current": f"{avg_km:.0f} km",
            "required": f"{req_run} km",
            "gap": f"+{req_run - avg_km:.0f} km/wk",
            "urgent": avg_km < req_run * 0.4,
        })

    long_run = run.get("avg_long_km", 0) or 0
    req_long = profile["long_run_km"]
    if req_long > 0 and long_run < req_long * 0.7:
        gaps.append({
            "metric": "Long run distance",
            "current": f"{long_run:.0f} km",
            "required": f"{req_long} km",
            "gap": f"+{req_long - long_run:.0f} km to build",
            "urgent": long_run < req_long * 0.3,
        })

    req_ride_wk = profile["weekly_ride_km"]
    if req_ride_wk > 0:
        total_ride_km = ride.get("total_km", 0) or 0
        # rough weekly avg over 12 months
        ride_wk_avg = total_ride_km / 52
        if ride_wk_avg < req_ride_wk * 0.7:
            gaps.append({
                "metric": "Cycling volume",
                "current": f"{ride_wk_avg:.0f} km/wk avg",
                "required": f"{req_ride_wk} km/wk",
                "gap": f"+{req_ride_wk - ride_wk_avg:.0f} km/wk",
                "urgent": ride_wk_avg < req_ride_wk * 0.2,
            })

    return gaps


# ── Public API ────────────────────────────────────────────────────────────────
def assess_athlete(data: dict, age: int = 35, sex: str = "M") -> dict:
    """Compare athlete metrics against population norms."""
    result = {}
    ah = data.get("apple_health") or {}

    if ah.get("vo2max"):
        vo2 = ah["vo2max"]
        result["vo2max"] = {
            "value": vo2, "unit": "mL/kg/min",
            "rating": _vo2max_rating(vo2, age, sex),
            "label": "VO2max (Apple Watch est.)",
        }

    if ah.get("rhr_recent"):
        rhr = ah["rhr_recent"]
        result["rhr"] = {
            "value": rhr, "unit": "bpm",
            "rating": _rhr_rating(rhr),
            "label": "Resting Heart Rate",
        }

    if ah.get("hrv_recent"):
        hrv = ah["hrv_recent"]
        result["hrv"] = {
            "value": hrv, "unit": "ms",
            "rating": _hrv_rating(hrv),
            "label": "HRV (SDNN)",
        }

    if ah.get("sleep_avg_score"):
        score = ah["sleep_avg_score"]
        grade, _ = _sleep_grade(score)
        result["sleep_score"] = {
            "value": score, "unit": "/100",
            "rating": grade,
            "label": "Sleep Score",
        }

    return result


def sport_recommendations(data: dict) -> list[dict]:
    """Score each sport profile against current fitness. Returns sorted list."""
    recs = []
    for sport, profile in SPORT_PROFILES.items():
        gaps     = _gap_analysis(profile, data)
        n_urgent = sum(1 for g in gaps if g["urgent"])
        n_gaps   = len(gaps)
        readiness = max(0, 100 - n_gaps * 15 - n_urgent * 20)
        recs.append({
            "sport": sport,
            "label": profile["label"],
            "readiness": readiness,
            "gaps": gaps,
            "notes": profile["notes"],
            "ready": readiness >= 60,
        })
    recs.sort(key=lambda r: r["readiness"], reverse=True)
    return recs


def evaluate_goal(sport: str, data: dict) -> dict:
    """Deep evaluation for a specific sport goal."""
    profile = SPORT_PROFILES.get(sport)
    if not profile:
        return {"error": f"Unknown sport: {sport}"}

    gaps      = _gap_analysis(profile, data)
    n_urgent  = sum(1 for g in gaps if g["urgent"])
    readiness = max(0, 100 - len(gaps) * 15 - n_urgent * 20)

    ld          = data.get("load", {})
    current_ctl = ld.get("ctl", 0)
    req_ctl     = profile["min_ctl"]
    ctl_deficit = max(0, req_ctl - current_ctl)
    weeks_ctl   = int(ctl_deficit / 5 * 5)  # ~5 wks per 5 CTL points

    if readiness >= 80:
        timeline = "You could race with 4–8 weeks of sport-specific prep"
        color    = "green"
    elif readiness >= 60:
        timeline = f"Target in ~{max(8, weeks_ctl)} weeks with consistent training"
        color    = "yellow"
    elif readiness >= 40:
        timeline = f"Realistic in ~{max(12, weeks_ctl)} weeks — build base first"
        color    = "yellow"
    else:
        timeline = f"Plan for ~{max(20, weeks_ctl)} weeks — significant base work needed"
        color    = "red"

    return {
        "sport":       sport,
        "label":       profile["label"],
        "readiness":   readiness,
        "color":       color,
        "gaps":        gaps,
        "timeline":    timeline,
        "notes":       profile["notes"],
        "current_ctl": current_ctl,
        "req_ctl":     req_ctl,
    }

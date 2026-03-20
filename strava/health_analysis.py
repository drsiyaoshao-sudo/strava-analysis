"""health_analysis.py — Health × Training cross-analysis (correlations, outliers, distributions, collisions)."""
from __future__ import annotations
import math
from datetime import datetime, timedelta
from .utils import km


def cross_analyze(
    health: dict,
    ctl_series: list[float],
    atl_series: list[float],
    tsb_series: list[float],
    day0: datetime,
    activities: list[dict],
    now: datetime,
) -> dict:
    """
    Build 90-day aligned health+training records and compute:
      - Pearson correlations (14 pairs)
      - IQR outliers (rhr, hrv, sleep, sleep_score)
      - 12-bin histograms
      - Stress collision events
    Returns dict suitable for data["health_analysis"].
    """
    _dh = health["daily"]
    _sh = health["sleep"]

    # 90-day aligned daily records
    aligned = []
    for i in range(89, -1, -1):
        ds   = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        off  = (datetime.strptime(ds, "%Y-%m-%d") - day0).days
        dd   = _dh.get(ds, {})
        sn   = _sh.get(ds, {})
        aligned.append({
            "date":        ds,
            "ctl":         round(ctl_series[off], 1) if 0 <= off < len(ctl_series) else None,
            "atl":         round(atl_series[off], 1) if 0 <= off < len(atl_series) else None,
            "tsb":         round(tsb_series[off], 1) if 0 <= off < len(tsb_series) else None,
            "rhr":         round(dd["resting_hr"], 1) if dd.get("resting_hr") else None,
            "hrv":         round(dd["hrv"], 1)        if dd.get("hrv")        else None,
            "sleep":       sn.get("total_h")   or None,
            "sleep_score": sn.get("score")     or None,
            "deep_pct":    sn.get("deep_pct")  or None,
            "rem_pct":     sn.get("rem_pct")   or None,
            "km":          round(km(sum(
                a.get("distance", 0) for a in activities if a["start_date"][:10] == ds
            )), 2),
        })

    # ── Pearson r ─────────────────────────────────────────────────────────────
    def _pearson(kx, ky):
        pairs = [(r[kx], r[ky]) for r in aligned
                 if r.get(kx) is not None and r.get(ky) is not None]
        if len(pairs) < 10:
            return None
        n = len(pairs)
        xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
        mx, my = sum(xs) / n, sum(ys) / n
        num = sum((x - mx) * (y - my) for x, y in pairs)
        den = math.sqrt(sum((x - mx) ** 2 for x in xs) *
                        sum((y - my) ** 2 for y in ys))
        return round(num / den, 3) if den else None

    CORR_DEFS = [
        ("Resting HR",  "ATL (fatigue)",  "rhr",         "atl", "pos",
         "Fatigue load elevates resting HR"),
        ("Resting HR",  "TSB (form)",     "rhr",         "tsb", "neg",
         "Better form → lower resting HR"),
        ("Resting HR",  "CTL (fitness)",  "rhr",         "ctl", "neg",
         "Higher fitness base → lower baseline HR"),
        ("HRV",         "ATL (fatigue)",  "hrv",         "atl", "neg",
         "Training stress suppresses HRV"),
        ("HRV",         "TSB (form)",     "hrv",         "tsb", "pos",
         "Better form → higher HRV recovery"),
        ("HRV",         "CTL (fitness)",  "hrv",         "ctl", "pos",
         "Higher fitness → higher baseline HRV"),
        ("Sleep h",     "ATL (fatigue)",  "sleep",       "atl", None,
         "Training load vs sleep duration"),
        ("Sleep h",     "TSB (form)",     "sleep",       "tsb", None,
         "Form quality vs sleep hours"),
        ("Sleep score", "ATL (fatigue)",  "sleep_score", "atl", "neg",
         "High fatigue suppresses sleep quality score"),
        ("Sleep score", "TSB (form)",     "sleep_score", "tsb", "pos",
         "Better form correlates with better sleep score"),
        ("Sleep score", "HRV",            "sleep_score", "hrv", "pos",
         "Good sleep → higher HRV next day"),
        ("Deep %",      "ATL (fatigue)",  "deep_pct",    "atl", "neg",
         "Training load reduces deep sleep proportion"),
        ("REM %",       "TSB (form)",     "rem_pct",     "tsb", "pos",
         "Better form → more REM sleep"),
        ("Resting HR",  "km trained",     "rhr",         "km",  "pos",
         "Same-day training volume impact on RHR"),
    ]

    correlations = []
    for lx, ly, kx, ky, exp_dir, desc in CORR_DEFS:
        rv = _pearson(kx, ky)
        if rv is None:
            continue
        direction = "pos" if rv > 0 else "neg"
        strength  = "strong" if abs(rv) >= 0.5 else "moderate" if abs(rv) >= 0.3 else "weak"
        expected  = (exp_dir is None) or (direction == exp_dir)
        correlations.append({
            "x": lx, "y": ly, "r": rv,
            "strength": strength, "direction": direction,
            "expected": expected, "desc": desc,
        })

    # ── IQR outlier detection ──────────────────────────────────────────────────
    def _outliers(key):
        vd = [(r["date"], r[key]) for r in aligned if r.get(key) is not None]
        if len(vd) < 8:
            return []
        vals = sorted(v for _, v in vd)
        n = len(vals)
        q1, q3 = vals[n // 4], vals[3 * n // 4]
        iqr = q3 - q1
        if iqr == 0:
            return []
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        return [{"date": d, "value": round(v, 1),
                 "direction": "high" if v > hi else "low"}
                for d, v in vd if v < lo or v > hi]

    outlier_res = {
        "rhr":         _outliers("rhr"),
        "hrv":         _outliers("hrv"),
        "sleep":       _outliers("sleep"),
        "sleep_score": _outliers("sleep_score"),
    }

    # ── 12-bin histograms ──────────────────────────────────────────────────────
    def _histogram(key):
        vals = [r[key] for r in aligned if r.get(key) is not None]
        if len(vals) < 5:
            return None
        lo, hi = min(vals), max(vals)
        if lo == hi:
            return None
        bw = (hi - lo) / 12
        counts = [0] * 12
        for v in vals:
            counts[min(int((v - lo) / bw), 11)] += 1
        edges = [round(lo + i * bw, 1) for i in range(12)]
        svals = sorted(vals)
        return {
            "labels": [str(e) for e in edges],
            "counts": counts,
            "mean":   round(sum(vals) / len(vals), 1),
            "median": round(svals[len(svals) // 2], 1),
            "n":      len(vals),
        }

    distributions = {
        "rhr":         _histogram("rhr"),
        "hrv":         _histogram("hrv"),
        "sleep":       _histogram("sleep"),
        "sleep_score": _histogram("sleep_score"),
    }

    # ── Stress collision events ────────────────────────────────────────────────
    def _pct(lst, p):
        s = sorted(lst)
        return s[int(len(s) * p)] if s else None

    atl_v  = [r["atl"]   for r in aligned if r.get("atl")   is not None]
    rhr_v  = [r["rhr"]   for r in aligned if r.get("rhr")   is not None]
    hrv_v  = [r["hrv"]   for r in aligned if r.get("hrv")   is not None]
    slp_v  = [r["sleep"] for r in aligned if r.get("sleep") is not None]

    atl_hi = _pct(atl_v, 0.75)
    rhr_hi = _pct(rhr_v, 0.75)
    hrv_lo = _pct(hrv_v, 0.25)
    slp_lo = _pct(slp_v, 0.25)

    collisions = []
    for rec in aligned:
        sigs = []
        if atl_hi and rec.get("atl") and rec["atl"] >= atl_hi:
            sigs.append("High fatigue (ATL)")
        if rhr_hi and rec.get("rhr") and rec["rhr"] >= rhr_hi:
            sigs.append("Elevated RHR")
        if hrv_lo and rec.get("hrv") and rec["hrv"] <= hrv_lo:
            sigs.append("Suppressed HRV")
        if slp_lo and rec.get("sleep") and rec["sleep"] <= slp_lo:
            sigs.append("Poor sleep")
        if rec.get("tsb") and rec["tsb"] < -15:
            sigs.append("Negative form (TSB)")
        if len(sigs) >= 3:
            collisions.append({
                "date": rec["date"], "signals": sigs,
                "severity": "critical" if len(sigs) >= 4 else "warning",
            })

    return {
        "correlations":   correlations,
        "outliers":       outlier_res,
        "distributions":  distributions,
        "collisions":     collisions[-15:],
        "aligned_series": {
            "dates":       [r["date"]            for r in aligned],
            "rhr":         [r.get("rhr")         for r in aligned],
            "hrv":         [r.get("hrv")         for r in aligned],
            "atl":         [r.get("atl")         for r in aligned],
            "tsb":         [r.get("tsb")         for r in aligned],
            "sleep":       [r.get("sleep")       for r in aligned],
            "sleep_score": [r.get("sleep_score") for r in aligned],
            "deep_pct":    [r.get("deep_pct")    for r in aligned],
            "rem_pct":     [r.get("rem_pct")     for r in aligned],
            "km":          [r.get("km")          for r in aligned],
        },
    }

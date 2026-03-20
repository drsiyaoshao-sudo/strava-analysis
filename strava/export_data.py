"""export_data.py — Export analyzed data to CSV for further analysis."""
from __future__ import annotations
import csv
import os
from datetime import datetime


def export_csv(data: dict, athlete: dict, output_path: str = "strava_analysis.csv") -> str | None:
    """
    Export the 90-day aligned training + health series to CSV.

    Columns:
      date, ctl, atl, tsb, acwr, rhr, hrv, hrv_readiness,
      sleep_h, sleep_score, deep_pct, rem_pct, km_trained
    """
    rows: list[dict] = []
    ha  = data.get("health_analysis")
    ld  = data.get("load", {})
    ah  = data.get("apple_health") or {}

    if ha and ha.get("aligned_series"):
        s = ha["aligned_series"]
        for i, date in enumerate(s["dates"]):
            atl = s["atl"][i]
            ctl = s["ctl"][i]
            rows.append({
                "date":          date,
                "ctl":           ctl,
                "atl":           atl,
                "tsb":           s["tsb"][i],
                "acwr":          round(atl / ctl, 3) if ctl and ctl > 0 else None,
                "rhr":           s["rhr"][i],
                "hrv":           s["hrv"][i],
                "hrv_readiness": None,   # per-day readiness not stored; use summary below
                "sleep_h":       s["sleep"][i],
                "sleep_score":   s["sleep_score"][i],
                "deep_pct":      s["deep_pct"][i],
                "rem_pct":       s["rem_pct"][i],
                "km_trained":    s["km"][i],
            })
    else:
        # Fallback: 90-day load series without health columns
        ls    = data.get("load_series", {})
        dates = ls.get("dates", [])
        for i, date in enumerate(dates):
            atl = ls["atl"][i] if ls.get("atl") else None
            ctl = ls["ctl"][i] if ls.get("ctl") else None
            rows.append({
                "date":          date,
                "ctl":           ctl,
                "atl":           atl,
                "tsb":           ls["tsb"][i] if ls.get("tsb") else None,
                "acwr":          round(atl / ctl, 3) if ctl and ctl > 0 else None,
                "rhr":           None, "hrv": None, "hrv_readiness": None,
                "sleep_h":       None, "sleep_score": None,
                "deep_pct":      None, "rem_pct":     None, "km_trained": None,
            })

    if not rows:
        print("No data to export.")
        return None

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    abs_path = os.path.abspath(output_path)
    name     = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
    print(f"Exported {len(rows)} days of data for {name} → {abs_path}")
    return abs_path

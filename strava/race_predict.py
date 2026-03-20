"""
race_predict.py — Race time predictions via Riegel formula.

T2 = T1 × (D2 / D1) ^ 1.06

Reference: Riegel, P.S. (1981). Athletic Records and Human Endurance. American Scientist.
Accuracy degrades when predicting more than ~3× beyond the reference distance.
"""
from __future__ import annotations

# Standard race distances in meters
RACE_DISTANCES: dict[str, int] = {
    "5K":           5_000,
    "10K":         10_000,
    "15K":         15_000,
    "Half Marathon":21_097,
    "Marathon":    42_195,
}

# Distance bins for matching best-effort activities (min_m, max_m)
_REF_BINS: dict[str, tuple[int, int]] = {
    "5K":            (4_500,  5_800),
    "10K":           (9_000, 11_000),
    "Half Marathon": (19_000, 22_500),
    "Marathon":      (40_000, 44_000),
}

# Riegel exponent degrades accuracy beyond these ratios
_MAX_RATIO = 4.0


def _riegel(t1_secs: float, d1_m: float, d2_m: float) -> float:
    return t1_secs * (d2_m / d1_m) ** 1.06


def _fmt_time(secs: float) -> str:
    h, rem = divmod(int(secs), 3600)
    m, s   = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _fmt_pace(secs: float, dist_m: float) -> str:
    sec_per_km = secs / (dist_m / 1000)
    m, s = divmod(int(sec_per_km), 60)
    return f"{m}:{s:02d}/km"


def find_best_efforts(runs: list[dict]) -> dict[str, dict]:
    """
    Scan run history and return the fastest average-pace activity
    for each reference distance bin.
    """
    best: dict[str, dict] = {}
    for name, (lo, hi) in _REF_BINS.items():
        candidates = [
            a for a in runs
            if lo <= a.get("distance", 0) <= hi
            and a.get("moving_time", 0) > 0
        ]
        if not candidates:
            continue
        # Fastest = highest distance/time (m/s)
        fastest = max(candidates, key=lambda a: a["distance"] / a["moving_time"])
        d_m     = fastest["distance"]
        t_s     = fastest["moving_time"]
        best[name] = {
            "distance_m":   d_m,
            "time_secs":    t_s,
            "pace_sec_km":  t_s / (d_m / 1000),
            "time_str":     _fmt_time(t_s),
            "pace_str":     _fmt_pace(t_s, d_m),
            "date":         fastest["start_date"][:10],
        }
    return best


def predict_races(runs: list[dict]) -> dict | None:
    """
    Given run history, find best known efforts and predict all RACE_DISTANCES.

    Returns:
      {
        "best_efforts":  {name: {distance_m, time_secs, time_str, pace_str, date}},
        "predictions":   {name: {distance_m, time_str, pace_str, ref_name, ref_date,
                                  is_actual, ratio_warning}},
      }
    or None if no qualifying runs found.
    """
    best_efforts = find_best_efforts(runs)
    if not best_efforts:
        return None

    predictions: dict[str, dict] = {}
    for target_name, target_m in RACE_DISTANCES.items():
        # Pick the reference effort closest in distance to the target
        ref_name, ref_data = min(
            best_efforts.items(),
            key=lambda kv: abs(kv[1]["distance_m"] - target_m),
        )

        ratio      = max(target_m, ref_data["distance_m"]) / min(target_m, ref_data["distance_m"])
        is_actual  = target_name == ref_name
        pred_secs  = _riegel(ref_data["time_secs"], ref_data["distance_m"], target_m)

        predictions[target_name] = {
            "distance_m":    target_m,
            "predicted_secs": round(pred_secs),
            "time_str":      _fmt_time(pred_secs),
            "pace_str":      _fmt_pace(pred_secs, target_m),
            "ref_name":      ref_name,
            "ref_date":      ref_data["date"],
            "is_actual":     is_actual,
            "ratio_warning": ratio > _MAX_RATIO,  # flag low-confidence extrapolation
        }

    return {"best_efforts": best_efforts, "predictions": predictions}

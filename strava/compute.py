"""compute.py — Core analysis pipeline: training stats + health enrichment + verdict."""
from __future__ import annotations
import math
from datetime import datetime, timedelta
from collections import defaultdict

from .utils import km, hms, pace, linear_trend, trimp, rolling_avg
from . import health_analysis
from . import benchmarks


def analyze(activities: list[dict], athlete: dict, health: dict | None = None) -> dict:
    """
    Full analysis pipeline.

    Returns data dict with keys:
      overview, weekly, load, load_series, hr, zones,
      running, cycling, swimming, consistency,
      apple_health, health_analysis, benchmarks, sport_recs, verdict
    """
    now  = datetime.now()
    data: dict = {}

    runs   = [a for a in activities if a.get("type") in ("Run", "TrailRun", "VirtualRun")]
    rides  = [a for a in activities if a.get("type") in ("Ride", "VirtualRide", "EBikeRide", "MountainBikeRide")]
    swims  = [a for a in activities if a.get("type") == "Swim"]

    # ── Overview ──────────────────────────────────────────────────────────────
    total_km_all = km(sum(a.get("distance", 0) for a in activities))
    total_h      = sum(a.get("moving_time", 0) for a in activities) / 3600
    weeks_span   = max(1, (now - datetime.strptime(activities[0]["start_date"][:10], "%Y-%m-%d")).days / 7)

    data["overview"] = {
        "total": len(activities), "runs": len(runs), "rides": len(rides),
        "swims": len(swims), "other": len(activities) - len(runs) - len(rides) - len(swims),
        "total_km": total_km_all, "total_h": total_h,
        "avg_km_week": total_km_all / weeks_span,
        "avg_h_week":  total_h / weeks_span,
    }

    # ── Weekly Volume ─────────────────────────────────────────────────────────
    weekly_km, weekly_h, weekly_trimp, week_labels = [], [], [], []
    for i in range(15, -1, -1):
        ws   = now - timedelta(weeks=i + 1)
        we   = now - timedelta(weeks=i)
        acts = [a for a in activities
                if ws <= datetime.strptime(a["start_date"][:10], "%Y-%m-%d") < we]
        wkm  = km(sum(a.get("distance", 0) for a in acts))
        wh   = sum(a.get("moving_time", 0) for a in acts) / 3600
        wt   = sum(trimp(a.get("moving_time", 0) / 60, a.get("average_heartrate"))
                   for a in acts if a.get("average_heartrate"))
        weekly_km.append(wkm)
        weekly_h.append(wh)
        weekly_trimp.append(wt)
        week_labels.append(we.strftime("%b %d"))

    trend_km   = linear_trend(weekly_km)
    zero_weeks = sum(1 for k in weekly_km if k == 0)

    data["weekly"] = {
        "labels": week_labels, "km": weekly_km,
        "hours": weekly_h, "trimp": weekly_trimp,
        "trend_pct": trend_km, "zero_weeks": zero_weeks,
    }

    # ── Training Load (CTL / ATL / TSB) ──────────────────────────────────────
    day0       = datetime.strptime(activities[0]["start_date"][:10], "%Y-%m-%d")
    days_total = (now - day0).days + 1
    daily_trimp = [0.0] * days_total
    for a in activities:
        d  = (datetime.strptime(a["start_date"][:10], "%Y-%m-%d") - day0).days
        hr = a.get("average_heartrate")
        if hr:
            daily_trimp[d] += trimp(a.get("moving_time", 0) / 60, hr)
        else:
            daily_trimp[d] += a.get("suffer_score", 0) or (a.get("moving_time", 0) / 60 * 0.3)

    ctl_series = rolling_avg(daily_trimp, 42)
    atl_series = rolling_avg(daily_trimp, 7)
    tsb_series = [c - a for c, a in zip(ctl_series, atl_series)]

    current_ctl = ctl_series[-1]
    current_atl = atl_series[-1]
    current_tsb = tsb_series[-1]
    ctl_6w_ago  = ctl_series[-43] if len(ctl_series) > 43 else ctl_series[0]
    ctl_delta   = current_ctl - ctl_6w_ago

    if current_tsb > 10:
        form_status, form_label = "fresh",      "FRESH"
        form_msg = "Good time to race or hit a key session"
    elif current_tsb > -10:
        form_status, form_label = "neutral",    "NEUTRAL"
        form_msg = "Training stress and recovery balanced"
    elif current_tsb > -25:
        form_status, form_label = "tired",      "TIRED"
        form_msg = "Accumulated fatigue — back off or you'll dig a hole"
    else:
        form_status, form_label = "overreached","OVERREACHED"
        form_msg = "You are digging a hole — rest now"

    data["load"] = {
        "ctl": current_ctl, "atl": current_atl, "tsb": current_tsb,
        "form_status": form_status, "form_label": form_label, "form_msg": form_msg,
        "ctl_delta": ctl_delta,
    }

    n90 = min(90, len(ctl_series))
    s0  = len(ctl_series) - n90
    data["load_series"] = {
        "dates": [(day0 + timedelta(days=i)).strftime("%b %d") for i in range(s0, len(ctl_series))],
        "ctl":   [round(v, 1) for v in ctl_series[s0:]],
        "atl":   [round(v, 1) for v in atl_series[s0:]],
        "tsb":   [round(v, 1) for v in tsb_series[s0:]],
    }

    # ── Heart Rate Trends ─────────────────────────────────────────────────────
    hr_data = []
    for label, sport_acts in [("Run", runs), ("Ride", rides)]:
        acts_with_hr = [a for a in sport_acts if a.get("average_heartrate") and a.get("distance", 0) > 500]
        if len(acts_with_hr) < 5:
            hr_data.append({"sport": label, "insufficient": True})
            continue
        mid         = len(acts_with_hr) // 2
        first_half  = acts_with_hr[:mid]
        second_half = acts_with_hr[mid:]

        def avg_hr_efficiency(acts):
            vals = []
            for a in acts:
                spd = a.get("average_speed", 0) * 3.6
                if spd > 0:
                    vals.append(a["average_heartrate"] / spd)
            return sum(vals) / len(vals) if vals else None

        eff_early    = avg_hr_efficiency(first_half)
        eff_late     = avg_hr_efficiency(second_half)
        avg_hr_early = sum(a["average_heartrate"] for a in first_half) / len(first_half)
        avg_hr_late  = sum(a["average_heartrate"] for a in second_half) / len(second_half)

        eff_change, eff_dir = None, "flat"
        if eff_early and eff_late:
            eff_change = (eff_late - eff_early) / eff_early * 100
            if eff_change < -3:   eff_dir = "improving"
            elif eff_change > 3:  eff_dir = "declining"

        max_hrs = [a.get("max_heartrate") for a in acts_with_hr if a.get("max_heartrate")]
        hr_data.append({
            "sport": label, "insufficient": False,
            "avg_hr_early": avg_hr_early, "avg_hr_late": avg_hr_late,
            "eff_change": eff_change, "eff_dir": eff_dir,
            "max_hr": max(max_hrs) if max_hrs else None,
            "n": len(acts_with_hr),
        })
    data["hr"] = hr_data

    # ── Intensity Distribution ────────────────────────────────────────────────
    def classify_zone(avg_hr, max_hr=190, rest_hr=50):
        if not avg_hr: return None
        hrr = (avg_hr - rest_hr) / (max_hr - rest_hr)
        if hrr < 0.60: return "Z1"
        if hrr < 0.70: return "Z2"
        if hrr < 0.80: return "Z3"
        if hrr < 0.90: return "Z4"
        return "Z5"

    zone_labels = {
        "Z1": "Easy", "Z2": "Aerobic Base",
        "Z3": "Tempo", "Z4": "Threshold", "Z5": "VO2max+"
    }
    zone_counts = defaultdict(int)
    zone_time   = defaultdict(float)
    for a in activities:
        z = classify_zone(a.get("average_heartrate"))
        if z:
            zone_counts[z] += 1
            zone_time[z]   += a.get("moving_time", 0) / 60

    if zone_counts:
        total_z_time = sum(zone_time.values()) or 1
        z1z2_pct = (zone_time.get("Z1", 0) + zone_time.get("Z2", 0)) / total_z_time * 100
        z3_pct   = zone_time.get("Z3", 0) / total_z_time * 100
        z4z5_pct = (zone_time.get("Z4", 0) + zone_time.get("Z5", 0)) / total_z_time * 100

        zone_warnings = []
        if z3_pct > 30:
            zone_warnings.append(("warning", "Too much Z3 grey zone — go easy on easy days, hard on hard days"))
        if z1z2_pct < 60:
            zone_warnings.append(("warning", "Not enough easy work — aerobic base development compromised"))
        if z4z5_pct < 5:
            zone_warnings.append(("warning", "Almost no high-intensity work — you won't build speed or VO2max"))
        if 75 <= z1z2_pct <= 85 and z4z5_pct >= 10 and z3_pct <= 15:
            zone_warnings.append(("good", "Intensity distribution close to optimal polarized model"))

        data["zones"] = {
            "no_data": False,
            "zone_counts": dict(zone_counts), "zone_time": dict(zone_time),
            "total_z_time": total_z_time, "zone_labels": zone_labels,
            "z1z2_pct": z1z2_pct, "z3_pct": z3_pct, "z4z5_pct": z4z5_pct,
            "warnings": zone_warnings,
        }
    else:
        z1z2_pct = z3_pct = z4z5_pct = 0
        data["zones"] = {"no_data": True}

    # ── Sport-Specific Metrics ────────────────────────────────────────────────
    if runs:
        run_dists = [a.get("distance", 0) for a in runs]
        run_times = [a.get("moving_time", 0) for a in runs]
        third = max(1, len(runs) // 3)

        def avg_speed_mps(acts):
            d = sum(a.get("distance", 0) for a in acts)
            t = sum(a.get("moving_time", 0) for a in acts)
            return d / t if t else 0

        p_early = avg_speed_mps(runs[:third])
        p_late  = avg_speed_mps(runs[-third:])
        pace_change_pct = (p_late - p_early) / p_early * 100 if p_early else 0
        long_runs = sorted(runs, key=lambda a: a.get("distance", 0), reverse=True)[:5]
        avg_long  = km(sum(a.get("distance", 0) for a in long_runs) / len(long_runs))
        cadences  = [a.get("average_cadence") for a in runs if a.get("average_cadence")]
        data["running"] = {
            "total_km": km(sum(run_dists)), "count": len(runs),
            "avg_km": km(sum(run_dists) / len(runs)), "avg_long_km": avg_long,
            "overall_pace": pace(sum(run_times), sum(run_dists)),
            "pace_change_pct": pace_change_pct,
            "cadence": sum(cadences) / len(cadences) if cadences else None,
        }
    else:
        data["running"] = None

    if rides:
        ride_dists = [a.get("distance", 0) for a in rides]
        ride_times = [a.get("moving_time", 0) for a in rides]
        watts = [a.get("average_watts") for a in rides if a.get("average_watts")]
        data["cycling"] = {
            "total_km": km(sum(ride_dists)), "count": len(rides),
            "avg_km": km(sum(ride_dists) / len(rides)),
            "avg_speed": sum(ride_dists) / sum(ride_times) * 3.6 if ride_times else None,
            "avg_watts": sum(watts) / len(watts) if watts else None,
        }
    else:
        data["cycling"] = None

    if swims:
        data["swimming"] = {
            "total_km": km(sum(a.get("distance", 0) for a in swims)),
            "count": len(swims),
        }
    else:
        data["swimming"] = None

    # ── Consistency ───────────────────────────────────────────────────────────
    active_wks = 0
    for i in range(12):
        ws = now - timedelta(weeks=i + 1)
        we = now - timedelta(weeks=i)
        if any(ws <= datetime.strptime(a["start_date"][:10], "%Y-%m-%d") < we for a in activities):
            active_wks += 1

    dates = sorted(set(a["start_date"][:10] for a in activities))
    max_streak = streak = 1
    for i in range(1, len(dates)):
        d1 = datetime.strptime(dates[i - 1], "%Y-%m-%d")
        d2 = datetime.strptime(dates[i],     "%Y-%m-%d")
        streak    = streak + 1 if (d2 - d1).days == 1 else 1
        max_streak = max(max_streak, streak)

    gaps = [(datetime.strptime(dates[i],     "%Y-%m-%d") -
             datetime.strptime(dates[i - 1], "%Y-%m-%d")).days
            for i in range(1, len(dates))] if len(dates) > 1 else []

    monotony = None
    if len(weekly_trimp) >= 4:
        mean_t = sum(weekly_trimp) / len(weekly_trimp)
        std_t  = math.sqrt(sum((x - mean_t) ** 2 for x in weekly_trimp) / len(weekly_trimp))
        monotony = mean_t / std_t if std_t else 0

    data["consistency"] = {
        "active_weeks": active_wks, "max_streak": max_streak,
        "avg_gap": sum(gaps) / len(gaps) if gaps else None,
        "max_gap": max(gaps) if gaps else None,
        "monotony": monotony,
    }

    # ── Apple Health Enrichment ───────────────────────────────────────────────
    if health:
        daily_h = health["daily"]
        sleep_h = health["sleep"]

        def avg_metric(daily, key, days_ago_start, days_ago_end):
            vals = []
            for d in range(days_ago_end, days_ago_start):
                day_str = (now - timedelta(days=d)).strftime("%Y-%m-%d")
                v = daily.get(day_str, {}).get(key)
                if v: vals.append(v)
            return sum(vals) / len(vals) if vals else None

        rhr_recent  = avg_metric(daily_h, "resting_hr", 0, 30)
        rhr_prior   = avg_metric(daily_h, "resting_hr", 30, 60)
        hrv_recent  = avg_metric(daily_h, "hrv", 0, 30)
        hrv_prior   = avg_metric(daily_h, "hrv", 30, 60)
        vo2max_vals = [v.get("vo2max") for v in daily_h.values() if v.get("vo2max")]
        weight_vals = [v.get("weight") for v in daily_h.values() if v.get("weight")]

        def _sleep_avg(key, n=30):
            vals = [
                sleep_h[(now - timedelta(days=d)).strftime("%Y-%m-%d")][key]
                for d in range(1, n + 1)
                if (now - timedelta(days=d)).strftime("%Y-%m-%d") in sleep_h
                and sleep_h[(now - timedelta(days=d)).strftime("%Y-%m-%d")].get(key) is not None
                and sleep_h[(now - timedelta(days=d)).strftime("%Y-%m-%d")][key] > 0
            ]
            return round(sum(vals) / len(vals), 2) if vals else None

        sleep_nights_30 = sum(
            1 for d in range(1, 31)
            if (now - timedelta(days=d)).strftime("%Y-%m-%d") in sleep_h
        )

        data["apple_health"] = {
            "rhr_recent":    rhr_recent,   "rhr_prior":    rhr_prior,
            "hrv_recent":    hrv_recent,   "hrv_prior":    hrv_prior,
            "vo2max":        max(vo2max_vals) if vo2max_vals else None,
            "weight_recent": avg_metric(daily_h, "weight", 0, 14),
            "weight_prior":  avg_metric(daily_h, "weight", 30, 60),
            "sleep_avg_h":     _sleep_avg("total_h"),
            "sleep_avg_score": _sleep_avg("score"),
            "sleep_avg_deep":  _sleep_avg("deep_pct"),
            "sleep_avg_rem":   _sleep_avg("rem_pct"),
            "sleep_avg_eff":   _sleep_avg("efficiency"),
            "sleep_nights":    sleep_nights_30,
        }

        # 30-day series for mini-charts
        labels_30, rhr_30, hrv_30, sleep_30, sleepscore_30 = [], [], [], [], []
        for d in range(29, -1, -1):
            day_str = (now - timedelta(days=d)).strftime("%Y-%m-%d")
            labels_30.append((now - timedelta(days=d)).strftime("%b %d"))
            dd  = daily_h.get(day_str, {})
            sn  = sleep_h.get(day_str, {})
            rhr_30.append(round(dd["resting_hr"], 1) if dd.get("resting_hr") else None)
            hrv_30.append(round(dd["hrv"], 1)        if dd.get("hrv")        else None)
            sleep_30.append(sn.get("total_h") or None)
            sleepscore_30.append(sn.get("score") or None)
        data["apple_health"]["series"] = {
            "labels": labels_30, "rhr": rhr_30, "hrv": hrv_30,
            "sleep": sleep_30, "sleep_score": sleepscore_30,
        }

        # Cross-analysis
        data["health_analysis"] = health_analysis.cross_analyze(
            health, ctl_series, atl_series, tsb_series, day0, activities, now
        )
    else:
        data["apple_health"]   = None
        data["health_analysis"] = None

    # ── Benchmarks & sport recommendations ────────────────────────────────────
    data["benchmarks"]  = benchmarks.assess_athlete(data)
    data["sport_recs"]  = benchmarks.sport_recommendations(data)[:5]

    # ── Verdict ───────────────────────────────────────────────────────────────
    flags = []
    if zero_weeks >= 4:
        flags.append(("critical", "CONSISTENCY PROBLEM: 4+ weeks with zero activity in last 4 months"))
    if trend_km < -5:
        flags.append(("warning", "VOLUME DECLINING: You are doing less than 2 months ago"))
    if trend_km > 8:
        flags.append(("warning", "VOLUME BUILDING FAST: >8%/wk — back off before you break"))
    if zone_counts and z3_pct > 30:
        flags.append(("warning", "GREY ZONE TRAP: Too much moderate-intensity work. Easy days easy, hard days hard"))
    if current_tsb < -25:
        flags.append(("critical", "OVERREACHED: TSB critically negative. Rest now"))
    if current_tsb > 15 and current_ctl < 30:
        flags.append(("warning", "LOW FITNESS BASE: Fresh but not fit — need more accumulated work"))
    if ctl_delta < -5:
        flags.append(("warning", "FITNESS DECLINING: CTL dropped >5 points in 6 weeks"))
    if data["apple_health"]:
        ah = data["apple_health"]
        if ah["rhr_recent"] and ah["rhr_prior"] and ah["rhr_recent"] > ah["rhr_prior"] + 3:
            flags.append(("warning",
                f"RESTING HR RISING: +{ah['rhr_recent']-ah['rhr_prior']:.0f} bpm vs last month — possible fatigue or illness"))
        if ah["hrv_recent"] and ah["hrv_prior"] and ah["hrv_recent"] < ah["hrv_prior"] * 0.85:
            flags.append(("warning", "HRV DECLINING: >15% drop vs last month — your body is under stress"))
        if ah["sleep_avg_h"] and ah["sleep_avg_h"] < 7:
            flags.append(("warning",
                f"SLEEP DEBT: Averaging {ah['sleep_avg_h']:.1f}h/night — recovery is compromised"))
    if not flags:
        flags.append(("good", "No critical red flags. Focus: consistent execution and optimized intensity distribution"))

    data["verdict"] = flags
    return data

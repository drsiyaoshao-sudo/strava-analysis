"""health_parse.py — Apple Health export parser (zip or xml)."""
from __future__ import annotations
import os
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from collections import defaultdict


def find_apple_health_export() -> str | None:
    """Look for export.xml or export.zip in common locations."""
    search_paths = [
        os.path.expanduser("~/Downloads/apple_health_export"),
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~/Desktop"),
        os.path.dirname(os.path.abspath(__file__)),
    ]
    for base in search_paths:
        xml_path = os.path.join(base, "export.xml")
        if os.path.exists(xml_path):
            return xml_path
        zip_path = os.path.join(base, "export.zip")
        if os.path.exists(zip_path):
            return zip_path
    return None


def load_apple_health(path: str | None = None) -> dict | None:
    """
    Parse Apple Health export and return structured data.
    Accepts either export.xml or export.zip.

    Returns dict with keys:
      "daily"  — {date_str: {metric_key: float}}
      "sleep"  — {date_str: {total_h, deep_h, rem_h, core_h, awake_h, inbed_h,
                              efficiency, deep_pct, rem_pct, score}}
    """
    if path is None:
        path = find_apple_health_export()
    if path is None:
        return None

    print(f"Loading Apple Health data from {os.path.basename(path)}...", end="", flush=True)

    if path.endswith(".zip"):
        try:
            zf = zipfile.ZipFile(path)
            names = zf.namelist()
            xml_name = next((n for n in names if n.endswith("export.xml")), None)
            if xml_name is None:
                print(" no export.xml inside zip.")
                return None
            xml_source = zf.open(xml_name)
        except Exception as e:
            print(f" error: {e}")
            return None
    else:
        xml_source = open(path, "rb")

    QUANTITIES = {
        "HKQuantityTypeIdentifierRestingHeartRate":         "resting_hr",
        "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": "hrv",
        "HKQuantityTypeIdentifierVO2Max":                   "vo2max",
        "HKQuantityTypeIdentifierBodyMass":                 "weight",
        "HKQuantityTypeIdentifierHeartRate":                "heart_rate",
    }
    SLEEP_TYPE = "HKCategoryTypeIdentifierSleepAnalysis"

    cutoff = datetime.now() - timedelta(days=366)
    daily: dict[str, dict] = defaultdict(lambda: defaultdict(list))
    sleep_sessions: list[dict] = []

    try:
        for _, elem in ET.iterparse(xml_source, events=("end",)):
            if elem.tag == "Record":
                t = elem.get("type", "")
                key = QUANTITIES.get(t)
                if key:
                    try:
                        start = datetime.strptime(elem.get("startDate", "")[:10], "%Y-%m-%d")
                        if start >= cutoff:
                            val = float(elem.get("value", 0))
                            daily[start.strftime("%Y-%m-%d")][key].append(val)
                    except (ValueError, TypeError):
                        pass
                elif t == SLEEP_TYPE:
                    try:
                        sd = datetime.strptime(elem.get("startDate", ""), "%Y-%m-%d %H:%M:%S %z")
                        ed = datetime.strptime(elem.get("endDate", ""), "%Y-%m-%d %H:%M:%S %z")
                        val = int(elem.get("value", -1))
                        # 0=InBed, 1=Asleep(legacy), 2=Awake, 3=Core, 4=Deep, 5=REM
                        if val in (0, 1, 2, 3, 4, 5) and sd >= cutoff.replace(tzinfo=sd.tzinfo):
                            sleep_sessions.append({
                                "start_dt": sd, "end_dt": ed,
                                "stage": val,
                                "duration_h": (ed - sd).total_seconds() / 3600,
                            })
                    except (ValueError, TypeError, AttributeError):
                        pass
                elem.clear()
    except ET.ParseError as e:
        print(f" XML parse error: {e}")
        return None
    finally:
        if hasattr(xml_source, "close"):
            xml_source.close()

    # Aggregate daily → scalar
    health = {}
    for day_str, metrics in daily.items():
        health[day_str] = {k: sum(v) / len(v) for k, v in metrics.items()}

    # ── Sleep: group records into nights and compute per-night stats + score ──
    night_buckets: dict[str, dict] = defaultdict(lambda: {
        "inbed_h": 0.0, "core_h": 0.0, "deep_h": 0.0,
        "rem_h": 0.0, "awake_h": 0.0,
    })
    for s in sleep_sessions:
        ed = s["end_dt"]
        # If waking between 03:00 and 14:00 → that date is the "morning of" date
        if 3 <= ed.hour <= 14:
            night_key = ed.strftime("%Y-%m-%d")
        else:
            night_key = s["start_dt"].strftime("%Y-%m-%d")
        stage = s["stage"]
        dur   = s["duration_h"]
        b = night_buckets[night_key]
        if   stage == 0: b["inbed_h"]  += dur
        elif stage == 2: b["awake_h"]  += dur
        elif stage == 3: b["core_h"]   += dur
        elif stage == 4: b["deep_h"]   += dur
        elif stage == 5: b["rem_h"]    += dur
        elif stage == 1: b["core_h"]   += dur  # legacy "Asleep" → core

    sleep_by_date: dict[str, dict] = {}
    for date_str, b in night_buckets.items():
        total_h  = b["core_h"] + b["deep_h"] + b["rem_h"]
        inbed_h  = b["inbed_h"] if b["inbed_h"] > total_h * 0.5 else total_h + b["awake_h"]
        eff      = total_h / inbed_h if inbed_h > 0 else 0
        deep_pct = b["deep_h"] / total_h * 100 if total_h > 0 else 0
        rem_pct  = b["rem_h"]  / total_h * 100 if total_h > 0 else 0
        has_stages = b["deep_h"] > 0 or b["rem_h"] > 0

        # Sleep score 0–100
        dur_score  = max(0.0, 40.0 * (1.0 - abs(total_h - 8.0) / 4.0))
        eff_score  = min(20.0, eff * 23.5)
        deep_score = min(20.0, deep_pct / 20.0 * 20.0) if has_stages else 0.0
        rem_score  = min(20.0, rem_pct  / 22.0 * 20.0) if has_stages else 0.0
        score = round(dur_score + eff_score + deep_score + rem_score) if total_h > 2 else None

        sleep_by_date[date_str] = {
            "total_h":    round(total_h, 2),
            "core_h":     round(b["core_h"], 2),
            "deep_h":     round(b["deep_h"], 2),
            "rem_h":      round(b["rem_h"],  2),
            "awake_h":    round(b["awake_h"], 2),
            "inbed_h":    round(inbed_h, 2),
            "efficiency": round(eff * 100, 1),
            "deep_pct":   round(deep_pct, 1),
            "rem_pct":    round(rem_pct,  1),
            "score":      score,
        }

    print(f" {len(health)} days of health data, {len(sleep_by_date)} sleep nights.")
    return {"daily": health, "sleep": sleep_by_date}

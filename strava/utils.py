"""utils.py — Shared math/formatting helpers."""
from __future__ import annotations
import math


def km(m: float) -> float:
    return m / 1000


def hms(s: float) -> str:
    h, r = divmod(int(s), 3600)
    m, sec = divmod(r, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m{sec:02d}s"


def pace(secs: float, meters: float) -> str | None:
    if not meters:
        return None
    s = secs / (meters / 1000)
    m, sec = divmod(int(s), 60)
    return f"{m}:{sec:02d}/km"


def linear_trend(values: list[float]) -> float:
    if len(values) < 3:
        return 0
    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return (num / den / y_mean * 100) if (den and y_mean) else 0


def trimp(duration_min: float, avg_hr: float | None,
          rest_hr: float = 50, max_hr: float = 190, gender_k: float = 1.92) -> float:
    if not avg_hr:
        return 0
    hrr = (avg_hr - rest_hr) / (max_hr - rest_hr)
    hrr = max(0, min(1, hrr))
    return duration_min * hrr * 0.64 * math.exp(gender_k * hrr)


def rolling_avg(series: list[float], window: int) -> list[float]:
    result = []
    for i in range(len(series)):
        w = series[max(0, i - window + 1): i + 1]
        result.append(sum(w) / len(w))
    return result

"""fetch.py — Strava API data retrieval."""
from __future__ import annotations
import requests
from datetime import datetime, timedelta


def fetch_athlete(token: str) -> dict:
    r = requests.get(
        "https://www.strava.com/api/v3/athlete",
        headers={"Authorization": f"Bearer {token}"},
    )
    return r.json()


def fetch_activities(token: str, months: int = 12) -> list[dict]:
    after = int((datetime.now() - timedelta(days=months * 30)).timestamp())
    activities, page = [], 1
    print(f"Fetching activities (last {months} months)...", end="", flush=True)
    while True:
        r = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers={"Authorization": f"Bearer {token}"},
            params={"after": after, "per_page": 100, "page": page},
        )
        batch = r.json()
        if not batch or not isinstance(batch, list):
            break
        activities.extend(batch)
        print(".", end="", flush=True)
        if len(batch) < 100:
            break
        page += 1
    print(f" {len(activities)} activities.")
    return sorted(activities, key=lambda a: a["start_date"])

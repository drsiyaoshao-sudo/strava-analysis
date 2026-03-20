#!/usr/bin/env python3
"""
Strava Fitness Analyzer — heuristic, no-BS analysis.
No external AI API. All signal extracted directly from your data.

Usage:
  python analyze.py              # Rich terminal report
  python analyze.py --html       # Generate + open dashboard.html
  python analyze.py --chat       # Interactive goal assessment REPL
  python analyze.py --months 6   # Limit to last N months (default 12)
"""
import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Strava Fitness Analyzer")
    parser.add_argument("--html",   action="store_true", help="Generate HTML dashboard")
    parser.add_argument("--chat",   action="store_true", help="Interactive goal assessment")
    parser.add_argument("--months", type=int, default=12, help="Months of history (default 12)")
    args = parser.parse_args()

    # Run from the script's directory so token file / health export are found
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    from strava.auth         import get_token
    from strava.fetch        import fetch_athlete, fetch_activities
    from strava.health_parse import load_apple_health
    from strava.compute      import analyze
    from strava.report       import print_report
    from strava.dashboard    import generate_html
    from strava.interact     import run_chat

    token      = get_token()
    athlete    = fetch_athlete(token)
    activities = fetch_activities(token, months=args.months)

    if not activities:
        print("No activities found.")
        sys.exit(0)

    health = load_apple_health()
    data   = analyze(activities, athlete, health=health)

    if args.html:
        generate_html(data, athlete)
    elif args.chat:
        print_report(data, athlete)
        run_chat(data, athlete)
    else:
        print_report(data, athlete)


if __name__ == "__main__":
    main()

"""Test the schedule fetcher API integration."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from src.schedule_fetcher import _api_get, LEAGUE_IDS, normalize_team_name

# Test fetching upcoming matches for major leagues
test_leagues = ["LCS", "LEC", "LCK", "LPL"]

for league_name in test_leagues:
    lid = LEAGUE_IDS.get(league_name)
    print(f"\n{'='*50}")
    print(f"  {league_name} (id={lid})")
    print(f"{'='*50}")

    data = _api_get("getSchedule", f"&leagueId={lid}")
    if not data:
        print("  FAILED to fetch")
        continue

    events = data["data"]["schedule"]["events"]
    upcoming = [e for e in events if e.get("state") in ("unstarted", "inProgress")]
    completed = [e for e in events if e.get("state") == "completed"]

    print(f"  Total events: {len(events)}, Completed: {len(completed)}, Upcoming: {len(upcoming)}")

    if upcoming:
        print(f"\n  Upcoming matches:")
        for e in upcoming[:5]:
            match = e.get("match", {})
            teams = match.get("teams", [])
            t1 = teams[0]["name"] if len(teams) > 0 else "TBD"
            t2 = teams[1]["name"] if len(teams) > 1 else "TBD"
            strategy = match.get("strategy", {})
            bo = strategy.get("count", 1)
            print(f"    {e['startTime'][:16]} | {e['blockName']:15s} | {t1:20s} vs {t2:20s} | Bo{bo}")
    else:
        print("  No upcoming matches in this page")

print(f"\n{'='*50}")
print("  SCHEDULE FETCHER TEST COMPLETE")
print(f"{'='*50}")

"""Fetch league IDs and upcoming schedule from the LoL Esports API."""
import urllib.request
import json

API_KEY = "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"
BASE = "https://esports-api.lolesports.com/persisted/gw"
HEADERS = {"x-api-key": API_KEY}


def api_get(endpoint, params=""):
    url = f"{BASE}/{endpoint}?hl=en-US{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


# 1. Get all leagues
print("=== LEAGUES ===")
data = api_get("getLeagues")
leagues = data["data"]["leagues"]
print(f"Total leagues: {len(leagues)}")
for l in leagues:
    print(f"  {l['slug']:25s} {l['name']:35s} id={l['id']}")

# 2. Get schedule for LCS (try the first few league IDs)
target_leagues = {
    "lcs": None,
    "lec": None,
    "lck": None,
    "lpl": None,
}

for l in leagues:
    slug = l["slug"].lower()
    if slug in target_leagues:
        target_leagues[slug] = l["id"]

print("\n=== TARGET LEAGUE IDS ===")
for name, lid in target_leagues.items():
    print(f"  {name}: {lid}")

# 3. Fetch schedule for LCS and look for unstarted matches
print("\n=== LCS SCHEDULE (checking for upcoming) ===")
if target_leagues["lcs"]:
    data = api_get("getSchedule", f"&leagueId={target_leagues['lcs']}")
    schedule = data["data"]["schedule"]
    events = schedule.get("events", [])
    pages = schedule.get("pages", {})
    print(f"Events: {len(events)}")
    print(f"Pages info: {pages}")

    states = {}
    for e in events:
        s = e.get("state", "unknown")
        states[s] = states.get(s, 0) + 1
    print(f"States: {states}")

    # Show upcoming events
    upcoming = [e for e in events if e.get("state") == "unstarted"]
    print(f"\nUpcoming matches: {len(upcoming)}")
    for e in upcoming[:10]:
        match = e.get("match", {})
        teams = match.get("teams", [])
        t1 = teams[0]["name"] if len(teams) > 0 else "TBD"
        t2 = teams[1]["name"] if len(teams) > 1 else "TBD"
        print(f"  {e['startTime']} | {e.get('blockName','')} | {t1} vs {t2}")

    # If no upcoming in current page, check older pages
    older_token = pages.get("newer")
    if older_token:
        print(f"\nFetching newer page: {older_token}")
        data2 = api_get("getSchedule", f"&leagueId={target_leagues['lcs']}&pageToken={older_token}")
        events2 = data2["data"]["schedule"].get("events", [])
        upcoming2 = [e for e in events2 if e.get("state") == "unstarted"]
        print(f"Upcoming in next page: {len(upcoming2)}")
        for e in upcoming2[:10]:
            match = e.get("match", {})
            teams = match.get("teams", [])
            t1 = teams[0]["name"] if len(teams) > 0 else "TBD"
            t2 = teams[1]["name"] if len(teams) > 1 else "TBD"
            print(f"  {e['startTime']} | {e.get('blockName','')} | {t1} vs {t2}")

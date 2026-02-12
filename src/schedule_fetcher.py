"""
schedule_fetcher.py — Fetch upcoming LoL esports schedules from the LoL Esports API.

Uses the public lolesports API (free, no auth key required beyond the static token).
Fetches future/upcoming matches for any league and caches results for 30 minutes.
"""

import urllib.request
import json
from datetime import datetime, timezone
from typing import Optional

import streamlit as st
import pandas as pd

# ---------------------------------------------------------------------------
# API Config
# ---------------------------------------------------------------------------
API_KEY = "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"
BASE_URL = "https://esports-api.lolesports.com/persisted/gw"
HEADERS = {"x-api-key": API_KEY}

# League ID mapping (official lolesports API IDs)
LEAGUE_IDS = {
    "LCS":   "98767991299243165",
    "LEC":   "98767991302996019",
    "LCK":   "98767991310872058",
    "LPL":   "98767991314006698",
    "CBLOL": "98767991332355509",
    "LJL":   "98767991349978712",
    "TCL":   "98767991343597634",
    "LFL":   "105266103462388553",
    "LCP":   "113476371197627891",
    "NLC":   "105266098308571975",
    "LIT":   "105266094998946936",
    "ROL":   "107407335299756365",
    "EBL":   "105266111679554379",
    "HLL":   "105266108767593290",
    "AL":    "109545772895506419",
    "LCKC":  "98767991335774713",
    "HW":    "105266106309666619",  # Hitpoint Masters
    "CCWS":  "113673877956508505",  # Rift Legends (closest match)
}


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------
def _api_get(endpoint: str, params: str = "") -> Optional[dict]:
    """Make a GET request to the LoL Esports API."""
    url = f"{BASE_URL}/{endpoint}?hl=en-US{params}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except Exception as e:
        st.warning(f"Failed to fetch schedule data: {e}")
        return None


# ---------------------------------------------------------------------------
# Schedule fetching
# ---------------------------------------------------------------------------
@st.cache_data(ttl=1800, show_spinner="Fetching upcoming matches…")
def fetch_league_schedule(league: str) -> pd.DataFrame:
    """
    Fetch the full schedule (completed + upcoming) for a league from the API.
    Returns a DataFrame with columns:
        date, block, team_a, team_b, state, match_id, league
    """
    league_id = LEAGUE_IDS.get(league)
    if not league_id:
        return pd.DataFrame()

    all_events = []
    page_token = None

    # Fetch all pages (API paginates)
    for _ in range(5):  # max 5 pages to avoid infinite loops
        params = f"&leagueId={league_id}"
        if page_token:
            params += f"&pageToken={page_token}"

        data = _api_get("getSchedule", params)
        if not data:
            break

        schedule = data.get("data", {}).get("schedule", {})
        events = schedule.get("events", [])
        pages = schedule.get("pages", {})

        for event in events:
            if event.get("type") != "match":
                continue

            match = event.get("match", {})
            teams = match.get("teams", [])
            team_a = teams[0].get("name", "TBD") if len(teams) > 0 else "TBD"
            team_b = teams[1].get("name", "TBD") if len(teams) > 1 else "TBD"
            team_a_code = teams[0].get("code", "") if len(teams) > 0 else ""
            team_b_code = teams[1].get("code", "") if len(teams) > 1 else ""

            # Win info for completed matches
            team_a_wins = 0
            team_b_wins = 0
            if teams and len(teams) >= 2:
                r0 = teams[0].get("result")
                r1 = teams[1].get("result")
                if r0:
                    team_a_wins = r0.get("gameWins", 0)
                if r1:
                    team_b_wins = r1.get("gameWins", 0)

            all_events.append({
                "date": event.get("startTime", ""),
                "block": event.get("blockName", ""),
                "team_a": team_a,
                "team_b": team_b,
                "team_a_code": team_a_code,
                "team_b_code": team_b_code,
                "team_a_wins": team_a_wins,
                "team_b_wins": team_b_wins,
                "state": event.get("state", ""),
                "match_id": match.get("id", ""),
                "league": league,
                "strategy_type": match.get("strategy", {}).get("type", ""),
                "strategy_count": match.get("strategy", {}).get("count", 1),
            })

        # Check for next page
        newer = pages.get("newer")
        if newer and newer != page_token:
            page_token = newer
        else:
            break

    if not all_events:
        return pd.DataFrame()

    df = pd.DataFrame(all_events)
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def get_upcoming_matches(league: str) -> pd.DataFrame:
    """Get only upcoming (unstarted/inProgress) matches for a league."""
    sched = fetch_league_schedule(league)
    if sched.empty:
        return sched
    return sched[sched["state"].isin(["unstarted", "inProgress"])].copy()


def get_completed_matches(league: str) -> pd.DataFrame:
    """Get only completed matches from the API schedule."""
    sched = fetch_league_schedule(league)
    if sched.empty:
        return sched
    return sched[sched["state"] == "completed"].copy()


def get_available_leagues() -> list[str]:
    """Return leagues that have API schedule support."""
    return sorted(LEAGUE_IDS.keys())


# ---------------------------------------------------------------------------
# Team name normalization
# ---------------------------------------------------------------------------
# The API sometimes uses slightly different names than Oracle's Elixir.
# This mapping helps bridge the gap.
TEAM_NAME_MAP = {
    "Cloud9 Kia": "Cloud9",
    "G2 Esports": "G2 Esports",
    "T1": "T1",
    "Gen.G": "Gen.G",
    # Add more as needed
}


def normalize_team_name(api_name: str) -> str:
    """Normalize API team names to match Oracle's Elixir names."""
    return TEAM_NAME_MAP.get(api_name, api_name)

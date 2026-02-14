"""
polymarket.py — Fetch LoL season-winner odds from the Polymarket Gamma API.

Pulls active League of Legends futures markets (e.g. LCK 2026 Season Winner)
and returns team-level odds for display alongside model projections.
"""

import urllib.request
import json
from typing import Optional

import streamlit as st

# ---------------------------------------------------------------------------
# API Config
# ---------------------------------------------------------------------------
GAMMA_API_URL = "https://gamma-api.polymarket.com"

# ---------------------------------------------------------------------------
# Team name normalization: Polymarket name → LoL Esports API name
# ---------------------------------------------------------------------------
POLYMARKET_NAME_MAP = {
    "Gen.G Esports": "Gen.G",
    "Hanwha Life Esports": "Hanwha Life Esports",
    "Nongshim RedForce": "Nongshim RedForce",
    "KT Rolster": "KT Rolster",
    "Dplus": "Dplus KIA",
    "FEARX": "FEARX",
    "Freecs": "Kwangdong Freecs",
    "BRION": "OKSavingsBank BRION",
    "DRX": "DRX",
    "T1": "T1",
    # LPL teams
    "Bilibili Gaming": "Bilibili Gaming",
    "Top Esports": "Top Esports",
    "JD Gaming": "JDG Intel",
    "EDward Gaming": "EDward Gaming",
    "Weibo Gaming": "Weibo Gaming",
    "LNG Esports": "LNG Esports",
    "ThunderTalk Gaming": "ThunderTalk Gaming",
    "FunPlus Phoenix": "FunPlus Phoenix",
    "Invictus Gaming": "Invictus Gaming",
    "Royal Never Give Up": "Royal Never Give Up",
    "Team WE": "Team WE",
    "Oh My God": "Oh My God",
    "TT Gaming": "TT Gaming",
    "Anyone's Legend": "Anyone's Legend",
    "Rare Atom": "Rare Atom",
    "Ultra Prime": "Ultra Prime",
    "Ninjas in Pyjamas": "Ninjas in Pyjamas",
}

# Reverse map: LoL Esports API name → Polymarket name
_REVERSE_MAP = {v: k for k, v in POLYMARKET_NAME_MAP.items()}


# ---------------------------------------------------------------------------
# League → Polymarket event title pattern mapping
# ---------------------------------------------------------------------------
LEAGUE_MARKET_MAP = {
    "LCK": "lck",
    "LPL": "lpl",
}


# ---------------------------------------------------------------------------
# API Fetching
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner="Fetching Polymarket odds…")
def fetch_polymarket_odds() -> dict[str, dict]:
    """
    Fetch all active LoL events from Polymarket and return a dict mapping
    normalized team names to their market odds data.

    Returns
    -------
    dict[str, dict]
        Keys are team names (normalized to LoL Esports API names).
        Values contain: odds, change_1w, change_1mo, volume, liquidity,
                        league (LCK/LPL), best_bid, best_ask, spread,
                        polymarket_name (original name on Polymarket).
    """
    url = f"{GAMMA_API_URL}/events?tag_slug=league-of-legends&active=true&closed=false&limit=50"

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "LoLHub/1.0")
        resp = urllib.request.urlopen(req, timeout=10)
        events = json.loads(resp.read())
    except Exception:
        return {}

    team_odds = {}

    for event in events:
        title = event.get("title", "")
        markets = event.get("markets", [])

        # Determine which league this event belongs to
        event_league = None
        for league_code, pattern in LEAGUE_MARKET_MAP.items():
            if pattern.lower() in title.lower():
                event_league = league_code
                break

        if not event_league:
            continue

        for market in markets:
            pm_name = market.get("groupItemTitle", "")
            if not pm_name or pm_name == "Other":
                continue

            # Skip inactive / zero-volume placeholder markets
            prices_str = market.get("outcomePrices", "")
            if not prices_str:
                continue

            try:
                prices = json.loads(prices_str)
                odds = float(prices[0])  # "Yes" price = implied probability
            except (json.JSONDecodeError, IndexError, ValueError):
                continue

            if odds <= 0:
                continue

            # Normalize team name to match LoL Esports API
            esports_name = POLYMARKET_NAME_MAP.get(pm_name, pm_name)

            team_odds[esports_name] = {
                "odds": odds,
                "polymarket_name": pm_name,
                "league": event_league,
                "change_1w": market.get("oneWeekPriceChange", 0) or 0,
                "change_1mo": market.get("oneMonthPriceChange", 0) or 0,
                "volume": float(market.get("volume", 0) or 0),
                "liquidity": float(market.get("liquidity", 0) or 0),
                "best_bid": float(market.get("bestBid", 0) or 0),
                "best_ask": float(market.get("bestAsk", 0) or 0),
                "spread": float(market.get("spread", 0) or 0),
            }

    return team_odds


def get_team_odds(team_a: str, team_b: str) -> Optional[dict]:
    """
    Look up Polymarket odds for two teams.

    Returns
    -------
    dict or None
        If at least one team has Polymarket data:
        {
            "team_a": {...odds dict...} or None,
            "team_b": {...odds dict...} or None,
            "league": "LCK" / "LPL",
        }
        Returns None if neither team has Polymarket data.
    """
    all_odds = fetch_polymarket_odds()

    odds_a = all_odds.get(team_a)
    odds_b = all_odds.get(team_b)

    if not odds_a and not odds_b:
        return None

    league = (odds_a or odds_b or {}).get("league", "")

    return {
        "team_a": odds_a,
        "team_b": odds_b,
        "league": league,
    }


def format_trend(change: float) -> str:
    """Format a price change as a colored trend string."""
    if change > 0:
        return f"🟢 +{change:.1%}"
    elif change < 0:
        return f"🔴 {change:.1%}"
    else:
        return "➖ 0%"

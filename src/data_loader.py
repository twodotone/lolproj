"""
data_loader.py — Central data ingestion for Oracle's Elixir LoL esports data.
Uses Streamlit caching so reloads are instant until the CSV changes on disk.
"""

import os
import streamlit as st
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "Data", "csv",
                        "2026_LoL_esports_match_data_from_OraclesElixir.csv")


# ---------------------------------------------------------------------------
# Raw loading (cached on file mtime so daily updates auto-refresh)
# ---------------------------------------------------------------------------
def _csv_mtime() -> float:
    """Return the modification time of the CSV for cache-busting."""
    try:
        return os.path.getmtime(CSV_PATH)
    except OSError:
        return 0.0


@st.cache_data(ttl=300, show_spinner="Loading Oracle's Elixir data…")
def load_raw_data(_mtime: float | None = None) -> pd.DataFrame:
    """Read the full CSV, parse dates, sort chronologically."""
    df = pd.read_csv(CSV_PATH, low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def get_data() -> pd.DataFrame:
    """Convenience wrapper that passes mtime for auto-refresh."""
    return load_raw_data(_mtime=_csv_mtime())


# ---------------------------------------------------------------------------
# Filtered views
# ---------------------------------------------------------------------------
def get_team_games(league: str | None = None) -> pd.DataFrame:
    """Return only team-level rows, optionally filtered by league."""
    df = get_data()
    mask = df["position"] == "team"
    if league:
        mask &= df["league"] == league
    return df.loc[mask].copy()


def get_player_games(league: str | None = None) -> pd.DataFrame:
    """Return only player-level rows, optionally filtered by league."""
    df = get_data()
    mask = df["position"] != "team"
    if league:
        mask &= df["league"] == league
    return df.loc[mask].copy()


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------
def get_leagues() -> list[str]:
    """Sorted list of all unique leagues in the dataset."""
    return sorted(get_data()["league"].unique().tolist())


def get_teams(league: str) -> list[str]:
    """Sorted list of teams in a specific league."""
    tg = get_team_games(league)
    return sorted(tg["teamname"].unique().tolist())


def get_all_teams() -> list[str]:
    """Sorted list of every team across all leagues."""
    tg = get_team_games()
    return sorted(tg["teamname"].unique().tolist())


# ---------------------------------------------------------------------------
# Schedule helpers
# ---------------------------------------------------------------------------
def get_schedule(league: str) -> pd.DataFrame:
    """
    Build a per-game schedule: date, blue team, red team, winner, game length.
    Each gameid appears once (we pivot the two team rows into one row).
    """
    tg = get_team_games(league)
    blue = tg[tg["side"] == "Blue"].set_index("gameid")
    red = tg[tg["side"] == "Red"].set_index("gameid")

    common = blue.index.intersection(red.index)
    sched = pd.DataFrame({
        "date": blue.loc[common, "date"].values,
        "blue_team": blue.loc[common, "teamname"].values,
        "red_team": red.loc[common, "teamname"].values,
        "blue_kills": blue.loc[common, "kills"].values,
        "red_kills": red.loc[common, "kills"].values,
        "blue_result": blue.loc[common, "result"].values,
        "gamelength": blue.loc[common, "gamelength"].values,
        "blue_gold": blue.loc[common, "totalgold"].values,
        "red_gold": red.loc[common, "totalgold"].values,
        "blue_dragons": blue.loc[common, "dragons"].values,
        "red_dragons": red.loc[common, "dragons"].values,
        "blue_barons": blue.loc[common, "barons"].values,
        "red_barons": red.loc[common, "barons"].values,
        "blue_towers": blue.loc[common, "towers"].values,
        "red_towers": red.loc[common, "towers"].values,
    }, index=common)

    sched["winner"] = np.where(sched["blue_result"] == 1,
                               sched["blue_team"], sched["red_team"])
    sched["game_length_min"] = (sched["gamelength"] / 60).round(1)
    sched["gold_diff"] = sched["blue_gold"] - sched["red_gold"]
    sched.sort_values("date", inplace=True)
    sched.reset_index(inplace=True)
    return sched


# ---------------------------------------------------------------------------
# Team stats
# ---------------------------------------------------------------------------
# Key metrics we want to aggregate per-team
TEAM_STAT_COLS = [
    "kills", "deaths", "assists", "teamkills", "teamdeaths",
    "gamelength", "totalgold", "earned gpm",
    "firstblood", "firstdragon", "firstbaron", "firsttower",
    "dragons", "barons", "towers", "heralds", "void_grubs",
    "team kpm", "dpm", "damageshare",
    "wardsplaced", "wpm", "wardskilled", "wcpm", "visionscore", "vspm",
    "golddiffat10", "golddiffat15", "xpdiffat10", "csdiffat10",
    "golddiffat20", "golddiffat25",
    "gspd", "gpr",
]


def get_team_stats(team: str, last_n: int | None = None) -> dict:
    """
    Aggregate a team's per-game averages for all key metrics.
    Optionally limit to the last N games.
    """
    tg = get_team_games()
    team_df = tg[tg["teamname"] == team].copy()
    if last_n:
        team_df = team_df.tail(last_n)

    stats = {"games_played": len(team_df)}
    wins = team_df["result"].sum()
    stats["wins"] = int(wins)
    stats["losses"] = stats["games_played"] - stats["wins"]
    stats["win_rate"] = round(wins / max(len(team_df), 1), 3)

    for col in TEAM_STAT_COLS:
        if col in team_df.columns:
            stats[col] = round(team_df[col].mean(), 2)

    return stats


def get_head_to_head(team_a: str, team_b: str) -> pd.DataFrame:
    """Return only games where team_a and team_b faced each other."""
    tg = get_team_games()
    # Find gameids where both teams appear
    games_a = set(tg[tg["teamname"] == team_a]["gameid"])
    games_b = set(tg[tg["teamname"] == team_b]["gameid"])
    common_games = games_a & games_b
    return tg[tg["gameid"].isin(common_games)].copy()


# ---------------------------------------------------------------------------
# Player helpers
# ---------------------------------------------------------------------------
def get_roster(team: str) -> pd.DataFrame:
    """Get the team's current roster with per-player averages."""
    pg = get_player_games()
    team_players = pg[pg["teamname"] == team]

    if team_players.empty:
        return pd.DataFrame()

    # Use only the most recent games to get the "current" roster
    recent_games = team_players["gameid"].unique()[-10:]
    recent = team_players[team_players["gameid"].isin(recent_games)]

    roster = recent.groupby(["playername", "position"]).agg({
        "kills": "mean",
        "deaths": "mean",
        "assists": "mean",
        "dpm": "mean",
        "cspm": "mean",
        "golddiffat10": "mean",
        "xpdiffat10": "mean",
        "visionscore": "mean",
        "champion": lambda x: x.value_counts().index[0],  # most played
    }).round(2).reset_index()

    roster.rename(columns={"champion": "most_played"}, inplace=True)

    # Sort by role order
    role_order = {"top": 0, "jng": 1, "mid": 2, "bot": 3, "sup": 4}
    roster["_order"] = roster["position"].map(role_order)
    roster.sort_values("_order", inplace=True)
    roster.drop(columns=["_order"], inplace=True)
    return roster


def get_champion_stats(team: str) -> pd.DataFrame:
    """Champion pick/ban stats for a team."""
    pg = get_player_games()
    team_champs = pg[pg["teamname"] == team]

    if team_champs.empty:
        return pd.DataFrame()

    champ_stats = team_champs.groupby("champion").agg(
        games=("gameid", "nunique"),
        wins=("result", "sum"),
        avg_kills=("kills", "mean"),
        avg_deaths=("deaths", "mean"),
        avg_assists=("assists", "mean"),
    ).round(2)
    champ_stats["win_rate"] = (champ_stats["wins"] / champ_stats["games"]).round(3)
    champ_stats.sort_values("games", ascending=False, inplace=True)
    return champ_stats.reset_index()


# ---------------------------------------------------------------------------
# Data freshness
# ---------------------------------------------------------------------------
def get_data_freshness() -> str:
    """Human-readable timestamp of when the CSV was last modified."""
    mtime = _csv_mtime()
    if mtime == 0:
        return "Unknown"
    from datetime import datetime
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

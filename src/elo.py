"""
elo.py — ELO rating engine tuned for LoL esports.

Features:
  • Margin-of-victory scaling (stomps shift ratings more)
  • Per-league computation so cross-league ELOs don't bleed
  • Full ELO history for trend charting
"""

import math
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STARTING_ELO = 1500
BASE_K = 32
HOME_ADVANTAGE = 0  # LoL has no real home advantage (side advantage is minor)


# ---------------------------------------------------------------------------
# Core ELO math
# ---------------------------------------------------------------------------
def expected_win_prob(elo_a: float, elo_b: float) -> float:
    """Standard logistic expected-score formula."""
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400))


def _margin_multiplier(winner_gold: float, loser_gold: float,
                       game_length: float) -> float:
    """
    Scale K by how dominant the victory was.
    Uses gold differential as a % of average gold, capped to avoid runaway.
    """
    if pd.isna(winner_gold) or pd.isna(loser_gold) or winner_gold + loser_gold == 0:
        return 1.0
    gold_diff_pct = abs(winner_gold - loser_gold) / ((winner_gold + loser_gold) / 2)
    # Shorter games with big gold leads = more dominant
    length_factor = 1.0
    if not pd.isna(game_length) and game_length > 0:
        # Normalize around 30 min (1800s); shorter = slightly higher multiplier
        length_factor = max(0.8, min(1.3, 1800 / max(game_length, 600)))
    return max(1.0, min(2.5, (1 + math.log(1 + gold_diff_pct * 3)) * length_factor))


# ---------------------------------------------------------------------------
# Compute ELO for a set of games
# ---------------------------------------------------------------------------
def compute_elo(games_df: pd.DataFrame) -> tuple[dict[str, float],
                                                   list[dict]]:
    """
    Walk through games chronologically and compute ELO updates.

    Parameters
    ----------
    games_df : DataFrame
        Team-level rows (position == 'team') with columns:
        gameid, date, teamname, side, result, totalgold, gamelength

    Returns
    -------
    elo_dict : {team_name: current_elo}
    elo_history : list of dicts with team, elo, date, gameid for charting
    """
    elos: dict[str, float] = {}
    history: list[dict] = []

    # Pair up games: group by gameid
    grouped = games_df.sort_values("date").groupby("gameid")

    for gameid, group in grouped:
        if len(group) != 2:
            continue  # skip malformed

        rows = group.sort_values("side")  # Blue first, Red second
        blue_row = rows.iloc[0]
        red_row = rows.iloc[1]

        blue_team = blue_row["teamname"]
        red_team = red_row["teamname"]

        # Initialize if new
        if blue_team not in elos:
            elos[blue_team] = STARTING_ELO
        if red_team not in elos:
            elos[red_team] = STARTING_ELO

        elo_blue = elos[blue_team]
        elo_red = elos[red_team]

        # Expected
        exp_blue = expected_win_prob(elo_blue, elo_red)
        exp_red = 1 - exp_blue

        # Actual
        blue_won = blue_row["result"] == 1
        actual_blue = 1.0 if blue_won else 0.0
        actual_red = 1.0 - actual_blue

        # Margin-of-victory K multiplier
        if blue_won:
            mov = _margin_multiplier(blue_row.get("totalgold", 0),
                                     red_row.get("totalgold", 0),
                                     blue_row.get("gamelength", 1800))
        else:
            mov = _margin_multiplier(red_row.get("totalgold", 0),
                                     blue_row.get("totalgold", 0),
                                     red_row.get("gamelength", 1800))

        k = BASE_K * mov

        # Update
        elos[blue_team] = elo_blue + k * (actual_blue - exp_blue)
        elos[red_team] = elo_red + k * (actual_red - exp_red)

        # Record history
        date = blue_row["date"]
        history.append({"team": blue_team, "elo": round(elos[blue_team], 1),
                        "date": date, "gameid": gameid})
        history.append({"team": red_team, "elo": round(elos[red_team], 1),
                        "date": date, "gameid": gameid})

    return elos, history


def compute_all_elo(games_df: pd.DataFrame, by_league: bool = True
                    ) -> tuple[dict[str, float], pd.DataFrame]:
    """
    Compute ELO ratings, optionally per-league.

    Returns
    -------
    elo_dict : {team_name: current_elo}
    history_df : DataFrame with columns [team, elo, date, gameid, league]
    """
    all_elos: dict[str, float] = {}
    all_history: list[dict] = []

    if by_league:
        for league in games_df["league"].unique():
            league_games = games_df[games_df["league"] == league]
            elos, hist = compute_elo(league_games)
            all_elos.update(elos)
            for h in hist:
                h["league"] = league
            all_history.extend(hist)
    else:
        elos, hist = compute_elo(games_df)
        all_elos.update(elos)
        for h in hist:
            h["league"] = "Global"
        all_history.extend(hist)

    history_df = pd.DataFrame(all_history)
    if not history_df.empty:
        history_df.sort_values("date", inplace=True)
        history_df.reset_index(drop=True, inplace=True)

    return all_elos, history_df


def get_elo_history(team: str, history_df: pd.DataFrame) -> pd.DataFrame:
    """Filter ELO history for a specific team."""
    return history_df[history_df["team"] == team].copy()


def get_league_elo_rankings(elo_dict: dict[str, float],
                             league_teams: list[str]) -> list[tuple[str, float]]:
    """Return teams sorted by ELO descending within a league."""
    rankings = [(t, elo_dict.get(t, STARTING_ELO)) for t in league_teams]
    rankings.sort(key=lambda x: x[1], reverse=True)
    return rankings

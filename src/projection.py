"""
projection.py — Multi-factor matchup projection model for LoL esports.

Factors (default weights):
  1. ELO Rating         30%
  2. Early Game         20%
  3. Objective Control  20%
  4. Team Fighting      15%
  5. Vision & Macro     15%

Each factor is computed as a z-score relative to all teams in the dataset,
then combined into a composite score → logistic win probability.
"""

import numpy as np
import pandas as pd

from src.elo import expected_win_prob, STARTING_ELO


# ---------------------------------------------------------------------------
# Factor definitions — columns used for each factor
# ---------------------------------------------------------------------------
FACTOR_COLS = {
    "early_game": {
        "golddiffat10": 1.0,
        "golddiffat15": 1.0,
        "xpdiffat10": 0.8,
        "csdiffat10": 0.6,
        "firstblood": 0.5,
    },
    "objective_control": {
        "firstdragon": 0.8,
        "firstbaron": 0.8,
        "firsttower": 0.7,
        "dragons": 1.0,
        "barons": 1.0,
        "heralds": 0.6,
        "void_grubs": 0.5,
        "towers": 0.8,
    },
    "team_fighting": {
        "team kpm": 1.0,
        "kills": 0.8,
        "deaths": -1.0,   # negative = fewer deaths is better
        "assists": 0.5,
        "dpm": 0.7,
    },
    "vision_macro": {
        "vspm": 1.0,
        "wpm": 0.8,
        "wcpm": 0.7,
        "earned gpm": 1.0,
        "gspd": 0.8,
    },
}

# Default factor weights (must sum to ~1.0 excluding elo)
FACTOR_WEIGHTS = {
    "elo": 0.30,
    "early_game": 0.20,
    "objective_control": 0.20,
    "team_fighting": 0.15,
    "vision_macro": 0.15,
}


# ---------------------------------------------------------------------------
# Playstyle classification
# ---------------------------------------------------------------------------
PLAYSTYLE_THRESHOLDS = {
    "Early Aggressor":      lambda p: p.get("early_game", 0) > 0.7,
    "Lane Kingdom":         lambda p: p.get("early_game", 0) > 0.5 and p.get("vision_macro", 0) > 0.5,
    "Objective Focused":    lambda p: p.get("objective_control", 0) > 0.7,
    "Team Fight Monsters":  lambda p: p.get("team_fighting", 0) > 0.7,
    "Vision Control":       lambda p: p.get("vision_macro", 0) > 0.7,
    "Late-Game Scaling":    lambda p: p.get("early_game", 0) < -0.3 and p.get("team_fighting", 0) > 0.3,
    "Balanced":             lambda p: True,  # fallback
}


# ---------------------------------------------------------------------------
# Team profile computation
# ---------------------------------------------------------------------------
def _compute_league_stats(games_df: pd.DataFrame) -> dict[str, dict]:
    """Compute mean and std for each stat column across all teams."""
    team_avgs = games_df.groupby("teamname").mean(numeric_only=True)
    stats = {}
    for col in team_avgs.columns:
        mean = team_avgs[col].mean()
        std = team_avgs[col].std()
        if std == 0 or pd.isna(std):
            std = 1.0
        stats[col] = {"mean": mean, "std": std}
    return stats


def compute_team_profile(team: str, games_df: pd.DataFrame,
                         last_n: int | None = None) -> dict[str, float]:
    """
    Compute a team's z-score profile across all factors.

    Returns dict like:
      {"early_game": 0.72, "objective_control": -0.15, ...}
    """
    team_df = games_df[games_df["teamname"] == team]
    if last_n:
        team_df = team_df.tail(last_n)
    if team_df.empty:
        return {f: 0.0 for f in FACTOR_COLS}

    league_stats = _compute_league_stats(games_df)
    team_means = team_df.mean(numeric_only=True)

    profile = {}
    for factor, cols in FACTOR_COLS.items():
        weighted_z = 0.0
        total_weight = 0.0
        for col, weight in cols.items():
            if col not in team_means or col not in league_stats:
                continue
            val = team_means[col]
            if pd.isna(val):
                continue
            z = (val - league_stats[col]["mean"]) / league_stats[col]["std"]
            weighted_z += z * weight
            total_weight += abs(weight)
        profile[factor] = round(weighted_z / max(total_weight, 1), 3)

    return profile


def get_playstyle_label(profile: dict[str, float]) -> str:
    """Classify a team's playstyle based on its profile scores."""
    for label, condition in PLAYSTYLE_THRESHOLDS.items():
        if condition(profile):
            return label
    return "Balanced"


# ---------------------------------------------------------------------------
# Matchup projection
# ---------------------------------------------------------------------------
def project_matchup(team_a: str, team_b: str,
                    games_df: pd.DataFrame,
                    elo_dict: dict[str, float],
                    last_n: int | None = None,
                    weights: dict | None = None) -> dict:
    """
    Project the outcome of a matchup between team_a and team_b.

    Returns
    -------
    dict with keys:
      - win_prob_a, win_prob_b : float (0-1)
      - factor_breakdown : dict of {factor: {team_a: score, team_b: score}}
      - composite_a, composite_b : float
      - playstyle_a, playstyle_b : str
      - strengths_a, weaknesses_a, strengths_b, weaknesses_b : list[str]
      - elo_a, elo_b : float
      - elo_edge : str (which team has ELO advantage)
    """
    w = weights or FACTOR_WEIGHTS

    profile_a = compute_team_profile(team_a, games_df, last_n)
    profile_b = compute_team_profile(team_b, games_df, last_n)

    elo_a = elo_dict.get(team_a, STARTING_ELO)
    elo_b = elo_dict.get(team_b, STARTING_ELO)

    # ELO component: convert to a z-score-like value
    elo_diff = (elo_a - elo_b) / 200  # ~1 std = 200 ELO points

    # Composite score = weighted sum of z-scores
    composite_a = w["elo"] * elo_diff
    composite_b = -w["elo"] * elo_diff

    factor_breakdown = {}
    for factor in FACTOR_COLS:
        fa = profile_a.get(factor, 0)
        fb = profile_b.get(factor, 0)
        composite_a += w.get(factor, 0) * fa
        composite_b += w.get(factor, 0) * fb
        factor_breakdown[factor] = {"team_a": round(fa, 3), "team_b": round(fb, 3)}

    # Convert composite diff to win probability (logistic)
    diff = composite_a - composite_b
    win_prob_a = 1 / (1 + np.exp(-diff * 3))  # scale factor for sensitivity
    win_prob_b = 1 - win_prob_a

    # Strengths / weaknesses
    def _classify(profile):
        strengths = [f.replace("_", " ").title()
                     for f, v in profile.items() if v > 0.3]
        weaknesses = [f.replace("_", " ").title()
                      for f, v in profile.items() if v < -0.3]
        return strengths or ["Balanced"], weaknesses or ["None"]

    str_a, weak_a = _classify(profile_a)
    str_b, weak_b = _classify(profile_b)

    return {
        "win_prob_a": round(win_prob_a, 3),
        "win_prob_b": round(win_prob_b, 3),
        "composite_a": round(composite_a, 3),
        "composite_b": round(composite_b, 3),
        "elo_a": round(elo_a, 1),
        "elo_b": round(elo_b, 1),
        "elo_edge": team_a if elo_a > elo_b else team_b,
        "factor_breakdown": factor_breakdown,
        "profile_a": profile_a,
        "profile_b": profile_b,
        "playstyle_a": get_playstyle_label(profile_a),
        "playstyle_b": get_playstyle_label(profile_b),
        "strengths_a": str_a,
        "weaknesses_a": weak_a,
        "strengths_b": str_b,
        "weaknesses_b": weak_b,
    }


# ---------------------------------------------------------------------------
# Global power rankings
# ---------------------------------------------------------------------------
def global_power_rankings(games_df: pd.DataFrame,
                          elo_dict: dict[str, float],
                          top_n: int = 30) -> pd.DataFrame:
    """
    Rank all teams globally by composite strength.
    Combines ELO + statistical profile.
    """
    teams = games_df["teamname"].unique()
    rows = []
    for team in teams:
        profile = compute_team_profile(team, games_df)
        composite = sum(
            FACTOR_WEIGHTS.get(f, 0) * v
            for f, v in profile.items()
        )
        elo = elo_dict.get(team, STARTING_ELO)
        composite += FACTOR_WEIGHTS["elo"] * ((elo - STARTING_ELO) / 200)

        league = games_df[games_df["teamname"] == team]["league"].iloc[0]
        team_games = games_df[games_df["teamname"] == team]
        wins = int(team_games["result"].sum())
        games_played = len(team_games)

        rows.append({
            "team": team,
            "league": league,
            "elo": round(elo, 1),
            "composite": round(composite, 3),
            "playstyle": get_playstyle_label(profile),
            "record": f"{wins}-{games_played - wins}",
            "win_rate": round(wins / max(games_played, 1), 3),
        })

    df = pd.DataFrame(rows)
    df.sort_values("composite", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.index += 1  # 1-indexed ranking
    df.index.name = "rank"
    return df.head(top_n)

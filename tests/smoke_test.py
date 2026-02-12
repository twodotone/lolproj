"""Smoke test for all core modules."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Suppress streamlit cache warnings in headless mode
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"

import pandas as pd

# --- Test data_loader (bypass st.cache_data) ---
print("=" * 60)
print("TESTING DATA LOADER")
print("=" * 60)

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "Data", "csv",
                         "2026_LoL_esports_match_data_from_OraclesElixir.csv")
df = pd.read_csv(CSV_PATH, low_memory=False)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df.sort_values("date", inplace=True)

print(f"  Rows loaded: {len(df)}")
print(f"  Leagues: {sorted(df['league'].unique().tolist())}")

team_df = df[df["position"] == "team"].copy()
print(f"  Team rows: {len(team_df)}")
print(f"  Unique teams: {team_df['teamname'].nunique()}")
print(f"  Date range: {df['date'].min()} to {df['date'].max()}")

lcs_teams = sorted(team_df[team_df["league"] == "LCS"]["teamname"].unique().tolist())
print(f"  LCS teams: {lcs_teams}")

# --- Test ELO ---
print()
print("=" * 60)
print("TESTING ELO ENGINE")
print("=" * 60)

from src.elo import compute_all_elo, expected_win_prob

elo_dict, elo_hist = compute_all_elo(team_df)
print(f"  Teams with ELO: {len(elo_dict)}")
print(f"  ELO history entries: {len(elo_hist)}")

# Show top 10 by ELO
sorted_elo = sorted(elo_dict.items(), key=lambda x: x[1], reverse=True)
print("  Top 10 ELO:")
for i, (team, elo) in enumerate(sorted_elo[:10], 1):
    league = team_df[team_df["teamname"] == team]["league"].iloc[0]
    print(f"    {i}. {team} ({league}): {elo:.1f}")

# Win prob test
p = expected_win_prob(1600, 1400)
print(f"  Expected win prob (1600 vs 1400): {p:.3f}")

# --- Test Projection ---
print()
print("=" * 60)
print("TESTING PROJECTION MODEL")
print("=" * 60)

from src.projection import project_matchup, compute_team_profile, get_playstyle_label

# Pick two LCS teams if available
if len(lcs_teams) >= 2:
    t_a, t_b = lcs_teams[0], lcs_teams[1]
else:
    t_a, t_b = sorted_elo[0][0], sorted_elo[1][0]

profile = compute_team_profile(t_a, team_df)
print(f"  {t_a} profile: {profile}")
print(f"  {t_a} playstyle: {get_playstyle_label(profile)}")

result = project_matchup(t_a, t_b, team_df, elo_dict)
print(f"\n  MATCHUP: {t_a} vs {t_b}")
print(f"    {t_a} win prob: {result['win_prob_a']:.1%}")
print(f"    {t_b} win prob: {result['win_prob_b']:.1%}")
print(f"    {t_a} ELO: {result['elo_a']:.0f}")
print(f"    {t_b} ELO: {result['elo_b']:.0f}")
print(f"    {t_a} playstyle: {result['playstyle_a']}")
print(f"    {t_b} playstyle: {result['playstyle_b']}")
print(f"    {t_a} strengths: {result['strengths_a']}")
print(f"    {t_b} strengths: {result['strengths_b']}")

print()
print("=" * 60)
print("ALL SMOKE TESTS PASSED!")
print("=" * 60)

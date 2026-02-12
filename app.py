"""
app.py — Main entry point for the LoL Esports Calendar & Projection Model.
Run with:  streamlit run app.py
"""

import streamlit as st
from src.data_loader import get_data, get_leagues, get_data_freshness
from src.elo import compute_all_elo
from src.projection import global_power_rankings

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="LoL Esports Hub",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for premium LoL feel
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Main header styling */
    .main-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 2.8rem;
        font-weight: 900;
        background: linear-gradient(135deg, #C89B3C 0%, #F0E6D2 50%, #C89B3C 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0;
        letter-spacing: 3px;
    }

    .sub-title {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        color: #A09B8C;
        text-align: center;
        margin-top: -10px;
        margin-bottom: 30px;
        letter-spacing: 2px;
    }

    /* Card styling */
    .stat-card {
        background: linear-gradient(145deg, #1E2D3D 0%, #0D1B2A 100%);
        border: 1px solid #C89B3C33;
        border-radius: 12px;
        padding: 20px;
        margin: 8px 0;
        transition: all 0.3s ease;
    }
    .stat-card:hover {
        border-color: #C89B3C;
        box-shadow: 0 0 20px #C89B3C22;
        transform: translateY(-2px);
    }

    .stat-value {
        font-family: 'Orbitron', sans-serif;
        font-size: 2rem;
        font-weight: 700;
        color: #C89B3C;
    }

    .stat-label {
        font-size: 0.85rem;
        color: #A09B8C;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Badge styling */
    .playstyle-badge {
        display: inline-block;
        background: linear-gradient(135deg, #C89B3C22, #C89B3C44);
        border: 1px solid #C89B3C;
        border-radius: 20px;
        padding: 4px 16px;
        font-size: 0.85rem;
        color: #F0E6D2;
        font-weight: 600;
        letter-spacing: 1px;
    }

    /* Win indicator */
    .win { color: #00C9A7; font-weight: 700; }
    .loss { color: #FF6B6B; font-weight: 700; }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #091428 0%, #0A1428 100%);
        border-right: 1px solid #C89B3C33;
    }

    /* Table styling */
    .dataframe {
        border: 1px solid #C89B3C33 !important;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #1E2D3D 0%, #0D1B2A 100%);
        border: 1px solid #C89B3C33;
        border-radius: 12px;
        padding: 15px;
    }

    [data-testid="stMetricValue"] {
        font-family: 'Orbitron', sans-serif;
        color: #C89B3C;
    }

    /* Divider */
    .gold-divider {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #C89B3C, transparent);
        margin: 30px 0;
    }

    /* Footer */
    .footer {
        text-align: center;
        color: #5B5A56;
        font-size: 0.75rem;
        padding: 20px;
        border-top: 1px solid #C89B3C22;
        margin-top: 40px;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar — League selector (shared state)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<p style="font-family: Orbitron; font-size: 1.2rem; color: #C89B3C; letter-spacing: 2px;">⚔️ NAVIGATION</p>',
                unsafe_allow_html=True)
    st.markdown("---")

    leagues = get_leagues()
    # Friendly league names
    LEAGUE_NAMES = {
        "LCS": "🇺🇸 LCS (Americas)",
        "LEC": "🇪🇺 LEC (EMEA)",
        "LCK": "🇰🇷 LCK (Korea)",
        "LPL": "🇨🇳 LPL (China)",
        "CBLOL": "🇧🇷 CBLOL (Brazil)",
        "LJL": "🇯🇵 LJL (Japan)",
        "LFL": "🇫🇷 LFL (France)",
        "TCL": "🇹🇷 TCL (Turkey)",
        "LCKC": "🇰🇷 LCK CL (Korea Acad.)",
        "LCP": "🇦🇺 LCP (Pacific)",
        "NLC": "🌍 NLC (Northern EU)",
    }

    display_leagues = [LEAGUE_NAMES.get(l, l) for l in leagues]
    selected_display = st.selectbox("🏆 Select League", display_leagues,
                                     index=display_leagues.index(LEAGUE_NAMES.get("LCS", "LCS"))
                                     if LEAGUE_NAMES.get("LCS", "LCS") in display_leagues
                                     else 0)

    # Map back to code
    reverse_map = {v: k for k, v in LEAGUE_NAMES.items()}
    selected_league = reverse_map.get(selected_display, selected_display)

    st.session_state["selected_league"] = selected_league

    st.markdown("---")
    st.markdown(f'<div class="footer">📊 Data: Oracle\'s Elixir<br>🕐 Updated: {get_data_freshness()}</div>',
                unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main landing page — Dashboard
# ---------------------------------------------------------------------------
st.markdown('<h1 class="main-title">⚔️ LOL ESPORTS HUB</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">ORACLE\'S ELIXIR ANALYTICS & PROJECTION ENGINE</p>', unsafe_allow_html=True)
st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

# Quick stats
df = get_data()
team_df = df[df["position"] == "team"]

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🏆 Leagues", len(get_leagues()))
with col2:
    st.metric("🎮 Teams", team_df["teamname"].nunique())
with col3:
    st.metric("⚔️ Games Played", team_df["gameid"].nunique())
with col4:
    date_range = f"{df['date'].min().strftime('%b %d')} — {df['date'].max().strftime('%b %d, %Y')}"
    st.metric("📅 Date Range", date_range)

st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Global Power Rankings
# ---------------------------------------------------------------------------
st.markdown("### 🌍 Global Power Rankings")
st.caption("Composite ranking across all leagues — ELO + statistical profile")

elo_dict, elo_hist = compute_all_elo(team_df)
rankings = global_power_rankings(team_df, elo_dict, top_n=20)

# Style the rankings table
def color_win_rate(val):
    if isinstance(val, float):
        if val >= 0.7:
            return "color: #00C9A7; font-weight: 700;"
        elif val >= 0.5:
            return "color: #F0E6D2;"
        else:
            return "color: #FF6B6B;"
    return ""

styled_rankings = rankings[["team", "league", "elo", "record", "win_rate", "playstyle", "composite"]].copy()
styled_rankings.columns = ["Team", "League", "ELO", "Record", "Win%", "Playstyle", "Power"]

st.dataframe(
    styled_rankings.style.map(color_win_rate, subset=["Win%"]),
    use_container_width=True,
    height=500,
)

# ---------------------------------------------------------------------------
# League snapshot for selected league
# ---------------------------------------------------------------------------
st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
st.markdown(f"### 📊 {selected_display} Snapshot")

league_games = team_df[team_df["league"] == selected_league]
if not league_games.empty:
    league_teams = league_games.groupby("teamname").agg(
        games=("gameid", "nunique"),
        wins=("result", "sum"),
    ).reset_index()
    league_teams["losses"] = league_teams["games"] - league_teams["wins"]
    league_teams["win_rate"] = (league_teams["wins"] / league_teams["games"]).round(3)
    league_teams["elo"] = league_teams["teamname"].map(
        lambda t: round(elo_dict.get(t, 1500), 1)
    )
    league_teams.sort_values("elo", ascending=False, inplace=True)
    league_teams.reset_index(drop=True, inplace=True)
    league_teams.index += 1

    display_cols = league_teams[["teamname", "wins", "losses", "win_rate", "elo"]].copy()
    display_cols.columns = ["Team", "W", "L", "Win%", "ELO"]

    st.dataframe(
        display_cols.style.map(color_win_rate, subset=["Win%"]),
        use_container_width=True,
    )
else:
    st.info("No games found for this league yet.")

st.markdown(f'<div class="footer">⚔️ LoL Esports Hub — Powered by Oracle\'s Elixir | Data as of {get_data_freshness()}</div>',
            unsafe_allow_html=True)

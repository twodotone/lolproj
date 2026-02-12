"""
🏆 Standings — League standings with ELO rankings and global power.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.data_loader import get_team_games, get_teams, get_leagues
from src.elo import compute_all_elo, STARTING_ELO
from src.projection import global_power_rankings

st.set_page_config(page_title="Standings | LoL Hub", page_icon="🏆", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main-title { font-family: 'Orbitron', sans-serif; font-size: 2.2rem; font-weight: 900;
        background: linear-gradient(135deg, #C89B3C 0%, #F0E6D2 50%, #C89B3C 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 2px; }
    .gold-divider { border: none; height: 1px;
        background: linear-gradient(90deg, transparent, #C89B3C, transparent); margin: 20px 0; }
</style>
""", unsafe_allow_html=True)

league = st.session_state.get("selected_league", "LCS")

st.markdown('<h1 class="main-title">🏆 STANDINGS</h1>', unsafe_allow_html=True)
st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Compute ELO
# ---------------------------------------------------------------------------
games_df = get_team_games()
elo_dict, elo_hist = compute_all_elo(games_df)

# ---------------------------------------------------------------------------
# View toggle
# ---------------------------------------------------------------------------
view = st.radio("📋 View", ["League Standings", "Global Power Rankings"], horizontal=True)

if view == "League Standings":
    st.markdown(f"### 🏆 {league} Standings")

    league_teams = get_teams(league)
    league_games = games_df[games_df["league"] == league]

    if league_games.empty:
        st.warning("No data for this league.")
        st.stop()

    # Build standings table
    standings_rows = []
    for team in league_teams:
        team_data = league_games[league_games["teamname"] == team]
        wins = int(team_data["result"].sum())
        games = len(team_data)
        losses = games - wins
        elo = elo_dict.get(team, STARTING_ELO)

        # Per-game averages
        avg_kills = team_data["kills"].mean()
        avg_deaths = team_data["deaths"].mean()
        avg_gl = team_data["gamelength"].mean() / 60
        avg_gd15 = team_data["golddiffat15"].mean()

        standings_rows.append({
            "Team": team,
            "W": wins,
            "L": losses,
            "Win%": round(wins / max(games, 1), 3),
            "ELO": round(elo, 1),
            "K/G": round(avg_kills, 1),
            "D/G": round(avg_deaths, 1),
            "Avg Length": f"{avg_gl:.1f}m",
            "GD@15": round(avg_gd15, 0) if not pd.isna(avg_gd15) else 0,
        })

    standings = pd.DataFrame(standings_rows)
    standings.sort_values("ELO", ascending=False, inplace=True)
    standings.reset_index(drop=True, inplace=True)
    standings.index += 1
    standings.index.name = "#"

    # Color styling
    def style_standings(row):
        styles = []
        for col in row.index:
            if col == "Win%":
                val = row[col]
                if val >= 0.7:
                    styles.append("color: #00C9A7; font-weight: 700;")
                elif val >= 0.5:
                    styles.append("color: #F0E6D2;")
                else:
                    styles.append("color: #FF6B6B;")
            elif col == "GD@15":
                val = row[col]
                if val > 0:
                    styles.append("color: #00C9A7;")
                elif val < 0:
                    styles.append("color: #FF6B6B;")
                else:
                    styles.append("")
            elif col == "ELO":
                val = row[col]
                if val > 1550:
                    styles.append("color: #C89B3C; font-weight: 700;")
                elif val < 1450:
                    styles.append("color: #FF6B6B;")
                else:
                    styles.append("")
            else:
                styles.append("")
        return styles

    st.dataframe(
        standings.style.apply(style_standings, axis=1),
        use_container_width=True,
        height=500,
    )

    # ---------------------------------------------------------------------------
    # ELO history chart for all teams in league
    # ---------------------------------------------------------------------------
    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
    st.markdown(f"### 📈 {league} ELO Trends")

    league_hist = elo_hist[elo_hist["league"] == league] if not elo_hist.empty else pd.DataFrame()

    if not league_hist.empty:
        # Color palette for teams
        colors = [
            "#C89B3C", "#0078D7", "#FF4655", "#00C9A7", "#FF9F1C",
            "#E040FB", "#00BCD4", "#FF6B6B", "#4CAF50", "#9C27B0",
            "#FF5722", "#607D8B", "#795548", "#3F51B5", "#CDDC39",
        ]

        fig = go.Figure()
        for i, team in enumerate(league_teams):
            team_hist = league_hist[league_hist["team"] == team]
            if not team_hist.empty:
                fig.add_trace(go.Scatter(
                    x=team_hist["date"], y=team_hist["elo"],
                    mode="lines+markers",
                    name=team,
                    line=dict(color=colors[i % len(colors)], width=2),
                    marker=dict(size=4),
                ))

        fig.add_hline(y=1500, line_dash="dash", line_color="rgba(160,155,140,0.27)",
                       annotation_text="Baseline")
        fig.update_layout(
            height=500,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="#1E2D3D"),
            yaxis=dict(gridcolor="#1E2D3D", title="ELO Rating"),
            legend=dict(font=dict(color="#F0E6D2", size=11),
                        bgcolor="rgba(0,0,0,0.3)",
                        bordercolor="rgba(200,155,60,0.2)"),
            margin=dict(l=50, r=20, t=20, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough data for ELO trends.")

    # ---------------------------------------------------------------------------
    # Win rate distribution
    # ---------------------------------------------------------------------------
    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
    st.markdown(f"### 📊 {league} Win Rate Distribution")

    wr_data = standings[["Team", "Win%"]].sort_values("Win%", ascending=True)

    fig_wr = go.Figure()
    fig_wr.add_trace(go.Bar(
        x=wr_data["Win%"],
        y=wr_data["Team"],
        orientation="h",
        marker_color=["#00C9A7" if wr >= 0.5 else "#FF6B6B" for wr in wr_data["Win%"]],
        text=[f"{wr:.0%}" for wr in wr_data["Win%"]],
        textposition="outside",
    ))
    fig_wr.add_vline(x=0.5, line_dash="dash", line_color="#C89B3C",
                      annotation_text="50%")
    fig_wr.update_layout(
        height=max(300, len(wr_data) * 35),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#1E2D3D", range=[0, 1.1], title="Win Rate"),
        yaxis=dict(gridcolor="#1E2D3D"),
        margin=dict(l=120, r=60, t=20, b=40),
    )
    st.plotly_chart(fig_wr, use_container_width=True)


else:
    # ---------------------------------------------------------------------------
    # Global Power Rankings
    # ---------------------------------------------------------------------------
    st.markdown("### 🌍 Global Power Rankings")
    st.caption("All teams ranked by composite score (ELO + statistical factors)")

    top_n = st.slider("Show top N teams", 10, 50, 30)
    rankings = global_power_rankings(games_df, elo_dict, top_n=top_n)

    # League filter for global view
    all_leagues = get_leagues()
    league_filter = st.multiselect("Filter by leagues", all_leagues, default=[])

    if league_filter:
        rankings = rankings[rankings["league"].isin(league_filter)]

    def style_global(row):
        styles = []
        for col in row.index:
            if col == "win_rate":
                val = row[col]
                if val >= 0.7:
                    styles.append("color: #00C9A7; font-weight: 700;")
                elif val >= 0.5:
                    styles.append("color: #F0E6D2;")
                else:
                    styles.append("color: #FF6B6B;")
            elif col == "composite":
                val = row[col]
                if val > 0.3:
                    styles.append("color: #C89B3C; font-weight: 700;")
                elif val < -0.3:
                    styles.append("color: #FF6B6B;")
                else:
                    styles.append("")
            else:
                styles.append("")
        return styles

    display = rankings.copy()
    display.columns = ["Team", "League", "ELO", "Power", "Playstyle", "Record", "Win%"]

    st.dataframe(
        display.style.apply(style_global, axis=1),
        use_container_width=True,
        height=600,
    )

    # ELO distribution across leagues
    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
    st.markdown("### 🌐 ELO Distribution by League")

    league_elos = []
    for league_name in all_leagues:
        league_team_list = get_teams(league_name)
        for t in league_team_list:
            league_elos.append({
                "league": league_name,
                "team": t,
                "elo": elo_dict.get(t, STARTING_ELO),
            })

    elo_df = pd.DataFrame(league_elos)

    if not elo_df.empty:
        fig_box = go.Figure()
        for league_name in sorted(all_leagues):
            ldata = elo_df[elo_df["league"] == league_name]
            fig_box.add_trace(go.Box(
                y=ldata["elo"],
                name=league_name,
                boxmean=True,
                marker_color="#C89B3C",
                line_color="#F0E6D2",
            ))
        fig_box.add_hline(y=1500, line_dash="dash", line_color="rgba(160,155,140,0.27)")
        fig_box.update_layout(
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="#1E2D3D"),
            yaxis=dict(gridcolor="#1E2D3D", title="ELO Rating"),
            margin=dict(l=50, r=20, t=20, b=40),
            showlegend=False,
        )
        st.plotly_chart(fig_box, use_container_width=True)

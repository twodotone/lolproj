"""
📊 Teams — Team profiles, rosters, champion pools, and stat dashboards.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from src.data_loader import (get_team_games, get_teams, get_team_stats,
                              get_roster, get_champion_stats, get_player_games)
from src.elo import compute_all_elo
from src.projection import compute_team_profile, get_playstyle_label, FACTOR_COLS

st.set_page_config(page_title="Teams | LoL Hub", page_icon="📊", layout="wide")

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
    .playstyle-badge { display: inline-block; background: linear-gradient(135deg, #C89B3C22, #C89B3C44);
        border: 1px solid #C89B3C; border-radius: 20px; padding: 4px 16px;
        font-size: 0.85rem; color: #F0E6D2; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

league = st.session_state.get("selected_league", "LCS")

st.markdown(f'<h1 class="main-title">📊 TEAM PROFILES</h1>', unsafe_allow_html=True)
st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Team selection
# ---------------------------------------------------------------------------
teams = get_teams(league)
if not teams:
    st.warning("No teams found for this league.")
    st.stop()

col_sel, col_n = st.columns([3, 1])
with col_sel:
    selected_team = st.selectbox(f"🏆 Select Team ({league})", teams)
with col_n:
    last_n = st.selectbox("📊 Sample", [None, 3, 5, 10],
                           format_func=lambda x: "All" if x is None else f"Last {x}",
                           index=0)

st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Team stats overview
# ---------------------------------------------------------------------------
stats = get_team_stats(selected_team, last_n=last_n)
games_df = get_team_games()
elo_dict, elo_hist = compute_all_elo(games_df)
profile = compute_team_profile(selected_team, games_df, last_n=last_n)
playstyle = get_playstyle_label(profile)

# Header
col_h1, col_h2, col_h3 = st.columns([3, 2, 2])
with col_h1:
    st.markdown(f"## {selected_team}")
    st.markdown(f'<span class="playstyle-badge">{playstyle}</span>', unsafe_allow_html=True)
with col_h2:
    elo = elo_dict.get(selected_team, 1500)
    st.metric("ELO Rating", f"{elo:.0f}")
with col_h3:
    st.metric("Record", f'{stats["wins"]}-{stats["losses"]}',
              delta=f'{stats["win_rate"]:.1%} Win Rate')

st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Key metrics row
# ---------------------------------------------------------------------------
st.markdown("### 📈 Core Metrics")
m1, m2, m3, m4, m5, m6 = st.columns(6)

with m1:
    st.metric("⚔️ Avg Kills", f'{stats.get("kills", 0):.1f}')
with m2:
    st.metric("💀 Avg Deaths", f'{stats.get("deaths", 0):.1f}')
with m3:
    kda = (stats.get("kills", 0) + stats.get("assists", 0)) / max(stats.get("deaths", 1), 1)
    st.metric("📊 KDA", f'{kda:.2f}')
with m4:
    st.metric("💰 GPM", f'{stats.get("earned gpm", 0):.0f}')
with m5:
    st.metric("⏱️ Avg Length", f'{stats.get("gamelength", 0) / 60:.1f}m')
with m6:
    st.metric("🗼 Towers/G", f'{stats.get("towers", 0):.1f}')

m7, m8, m9, m10, m11, m12 = st.columns(6)
with m7:
    st.metric("🩸 First Blood%", f'{stats.get("firstblood", 0):.1%}')
with m8:
    st.metric("🐉 First Drake%", f'{stats.get("firstdragon", 0):.1%}')
with m9:
    st.metric("👑 First Baron%", f'{stats.get("firstbaron", 0):.1%}')
with m10:
    st.metric("🏯 First Tower%", f'{stats.get("firsttower", 0):.1%}')
with m11:
    st.metric("🐉 Drakes/G", f'{stats.get("dragons", 0):.1f}')
with m12:
    st.metric("👑 Barons/G", f'{stats.get("barons", 0):.1f}')

st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Factor profile radar
# ---------------------------------------------------------------------------
st.markdown("### 🎯 Team Profile")

factor_names = [f.replace("_", " ").title() for f in FACTOR_COLS.keys()]
vals = [profile.get(f, 0) for f in FACTOR_COLS]

fig = go.Figure()
fig.add_trace(go.Scatterpolar(
    r=vals + [vals[0]],
    theta=factor_names + [factor_names[0]],
    fill="toself",
    fillcolor="rgba(200, 155, 60, 0.2)",
    line=dict(color="#C89B3C", width=3),
    name=selected_team,
))
fig.update_layout(
    polar=dict(
        bgcolor="rgba(0,0,0,0)",
        radialaxis=dict(visible=True, gridcolor="#1E2D3D"),
        angularaxis=dict(gridcolor="#1E2D3D"),
    ),
    height=400,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=60, r=60, t=40, b=40),
    showlegend=False,
)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Early game metrics
# ---------------------------------------------------------------------------
st.markdown("### ⏰ Early Game Differentials")

eg1, eg2, eg3, eg4 = st.columns(4)
with eg1:
    gd10 = stats.get("golddiffat10", 0)
    st.metric("💰 GD@10", f"{gd10:+.0f}",
              delta="Ahead" if gd10 > 0 else "Behind")
with eg2:
    gd15 = stats.get("golddiffat15", 0)
    st.metric("💰 GD@15", f"{gd15:+.0f}",
              delta="Ahead" if gd15 > 0 else "Behind")
with eg3:
    xd10 = stats.get("xpdiffat10", 0)
    st.metric("✨ XPD@10", f"{xd10:+.0f}",
              delta="Ahead" if xd10 > 0 else "Behind")
with eg4:
    cd10 = stats.get("csdiffat10", 0)
    st.metric("🗡️ CSD@10", f"{cd10:+.0f}",
              delta="Ahead" if cd10 > 0 else "Behind")

st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ELO History
# ---------------------------------------------------------------------------
st.markdown("### 📈 ELO History")

team_elo_hist = elo_hist[elo_hist["team"] == selected_team]
if not team_elo_hist.empty:
    fig_elo = go.Figure()
    fig_elo.add_trace(go.Scatter(
        x=team_elo_hist["date"], y=team_elo_hist["elo"],
        mode="lines+markers",
        line=dict(color="#C89B3C", width=3),
        marker=dict(size=6, color="#C89B3C", line=dict(color="#F0E6D2", width=1)),
        fill="tozeroy",
        fillcolor="rgba(200, 155, 60, 0.1)",
        name=selected_team,
    ))
    fig_elo.add_hline(y=1500, line_dash="dash", line_color="#A09B8C",
                       annotation_text="Baseline (1500)")
    fig_elo.update_layout(
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#1E2D3D"),
        yaxis=dict(gridcolor="#1E2D3D", title="ELO"),
        margin=dict(l=50, r=20, t=20, b=40),
        showlegend=False,
    )
    st.plotly_chart(fig_elo, use_container_width=True)
else:
    st.info("Not enough games for ELO history.")

st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Roster
# ---------------------------------------------------------------------------
st.markdown("### 👥 Current Roster")

roster = get_roster(selected_team)
if not roster.empty:
    role_emoji = {"top": "🛡️", "jng": "🌿", "mid": "🔮", "bot": "🏹", "sup": "💫"}
    roster["Role"] = roster["position"].map(lambda p: f'{role_emoji.get(p, "❓")} {p.upper()}')

    display_roster = roster[["Role", "playername", "most_played", "kills", "deaths",
                              "assists", "dpm", "cspm", "golddiffat10"]].copy()
    display_roster.columns = ["Role", "Player", "Signature", "K", "D", "A",
                               "DPM", "CSPM", "GD@10"]

    st.dataframe(display_roster, use_container_width=True, hide_index=True)
else:
    st.info("No roster data available.")

st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Champion pool
# ---------------------------------------------------------------------------
st.markdown("### 🎮 Champion Pool")

champ_stats = get_champion_stats(selected_team)
if not champ_stats.empty:
    top_champs = champ_stats.head(15)

    fig_champs = go.Figure()
    fig_champs.add_trace(go.Bar(
        x=top_champs["champion"],
        y=top_champs["games"],
        marker_color=["#00C9A7" if wr >= 0.5 else "#FF6B6B"
                       for wr in top_champs["win_rate"]],
        text=[f"{wr:.0%}" for wr in top_champs["win_rate"]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Games: %{y}<br>Win Rate: %{text}<extra></extra>",
    ))
    fig_champs.update_layout(
        height=350,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#1E2D3D", title="Champion"),
        yaxis=dict(gridcolor="#1E2D3D", title="Games Played"),
        margin=dict(l=50, r=20, t=20, b=60),
    )
    st.plotly_chart(fig_champs, use_container_width=True)

    with st.expander("📋 Full Champion Stats"):
        st.dataframe(champ_stats, use_container_width=True, hide_index=True)
else:
    st.info("No champion data available.")

# ---------------------------------------------------------------------------
# Recent form
# ---------------------------------------------------------------------------
st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
st.markdown("### 📉 Recent Form")

team_games = get_team_games()
team_recent = team_games[team_games["teamname"] == selected_team].tail(10)

if not team_recent.empty:
    team_recent = team_recent.copy()
    team_recent["game_num"] = range(1, len(team_recent) + 1)
    team_recent["result_label"] = team_recent["result"].map({1: "Win", 0: "Loss"})
    team_recent["color"] = team_recent["result"].map({1: "#00C9A7", 0: "#FF6B6B"})

    # Recent results display
    result_str = "  ".join(
        [f'{"🟢" if r == 1 else "🔴"}' for r in team_recent["result"].values]
    )
    recent_wr = team_recent["result"].mean()
    st.markdown(f"**Last {len(team_recent)} games:** {result_str}  ({recent_wr:.0%} WR)")

    # Gold trend
    fig_form = go.Figure()
    fig_form.add_trace(go.Bar(
        x=team_recent["game_num"],
        y=team_recent["totalgold"],
        marker_color=team_recent["color"].tolist(),
        text=team_recent["result_label"],
        textposition="outside",
    ))
    fig_form.update_layout(
        height=250,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#1E2D3D", title="Game #", dtick=1),
        yaxis=dict(gridcolor="#1E2D3D", title="Total Gold"),
        margin=dict(l=50, r=20, t=20, b=40),
    )
    st.plotly_chart(fig_form, use_container_width=True)
else:
    st.info("Not enough data for recent form.")

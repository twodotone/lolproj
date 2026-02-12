"""
🔮 Matchup Analyzer — Head-to-head projection with factor breakdown.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from src.data_loader import get_team_games, get_all_teams, get_head_to_head
from src.elo import compute_all_elo
from src.projection import project_matchup, FACTOR_COLS

st.set_page_config(page_title="Matchup | LoL Hub", page_icon="🔮", layout="wide")

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
    .win-prob { font-family: 'Orbitron', sans-serif; font-size: 3rem; font-weight: 900; }
    .team-name-large { font-family: 'Orbitron', sans-serif; font-size: 1.4rem; font-weight: 700;
        color: #F0E6D2; letter-spacing: 1px; }
    .playstyle-badge { display: inline-block; background: linear-gradient(135deg, #C89B3C22, #C89B3C44);
        border: 1px solid #C89B3C; border-radius: 20px; padding: 4px 16px; font-size: 0.85rem;
        color: #F0E6D2; font-weight: 600; }
    .advantage { color: #00C9A7; font-weight: 600; }
    .disadvantage { color: #FF6B6B; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🔮 MATCHUP ANALYZER</h1>', unsafe_allow_html=True)
st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Team selection
# ---------------------------------------------------------------------------
all_teams = sorted(get_all_teams())
games_df = get_team_games()

col1, col2, col3 = st.columns([4, 1, 4])

with col1:
    team_a = st.selectbox("🔵 Blue Side", all_teams,
                           index=0)
with col2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<center style='font-size: 2rem; font-weight: 900; color: #C89B3C;'>⚔️</center>",
                unsafe_allow_html=True)
with col3:
    team_b = st.selectbox("🔴 Red Side", all_teams,
                           index=min(1, len(all_teams) - 1))

if team_a == team_b:
    st.warning("Please select two different teams.")
    st.stop()

# Sample size selector
sample_col1, sample_col2 = st.columns([1, 3])
with sample_col1:
    last_n = st.selectbox("📊 Sample Size", [None, 3, 5, 10, 15],
                           format_func=lambda x: "All Games" if x is None else f"Last {x} Games",
                           index=0)

st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Compute projection
# ---------------------------------------------------------------------------
elo_dict, elo_hist = compute_all_elo(games_df)
result = project_matchup(team_a, team_b, games_df, elo_dict, last_n=last_n)

# ---------------------------------------------------------------------------
# Win probability header
# ---------------------------------------------------------------------------
prob_a = result["win_prob_a"]
prob_b = result["win_prob_b"]

col_pa, col_vs, col_pb = st.columns([4, 1, 4])

with col_pa:
    color_a = "#00C9A7" if prob_a > prob_b else "#FF6B6B" if prob_a < prob_b else "#C89B3C"
    st.markdown(f'<p class="team-name-large" style="text-align: center;">{team_a}</p>',
                unsafe_allow_html=True)
    st.markdown(f'<p class="win-prob" style="text-align: center; color: {color_a};">{prob_a:.1%}</p>',
                unsafe_allow_html=True)
    st.markdown(f'<p style="text-align: center;"><span class="playstyle-badge">{result["playstyle_a"]}</span></p>',
                unsafe_allow_html=True)

with col_vs:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<center style='font-size: 1.2rem; color: #A09B8C;'>WIN PROB</center>",
                unsafe_allow_html=True)

with col_pb:
    color_b = "#00C9A7" if prob_b > prob_a else "#FF6B6B" if prob_b < prob_a else "#C89B3C"
    st.markdown(f'<p class="team-name-large" style="text-align: center;">{team_b}</p>',
                unsafe_allow_html=True)
    st.markdown(f'<p class="win-prob" style="text-align: center; color: {color_b};">{prob_b:.1%}</p>',
                unsafe_allow_html=True)
    st.markdown(f'<p style="text-align: center;"><span class="playstyle-badge">{result["playstyle_b"]}</span></p>',
                unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Win probability donut chart
# ---------------------------------------------------------------------------
fig_donut = go.Figure(data=[go.Pie(
    labels=[team_a, team_b],
    values=[prob_a, prob_b],
    hole=0.65,
    marker=dict(colors=["#0078D7", "#FF4655"],
                line=dict(color="#0A1428", width=3)),
    textinfo="label+percent",
    textfont=dict(size=14, family="Inter"),
    hovertemplate="<b>%{label}</b><br>Win Prob: %{percent}<extra></extra>",
)])
fig_donut.update_layout(
    height=300,
    showlegend=False,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=20, r=20, t=20, b=20),
    annotations=[dict(text="WIN<br>PROB", x=0.5, y=0.5, font_size=16,
                       font_color="#A09B8C", font_family="Orbitron",
                       showarrow=False)],
)
st.plotly_chart(fig_donut, use_container_width=True)

st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Factor-by-factor radar chart
# ---------------------------------------------------------------------------
st.markdown("### 📊 Factor Breakdown")

factor_names = [f.replace("_", " ").title() for f in FACTOR_COLS.keys()]
breakdown = result["factor_breakdown"]

vals_a = [breakdown[f]["team_a"] for f in FACTOR_COLS]
vals_b = [breakdown[f]["team_b"] for f in FACTOR_COLS]

fig_radar = go.Figure()
fig_radar.add_trace(go.Scatterpolar(
    r=vals_a + [vals_a[0]],
    theta=factor_names + [factor_names[0]],
    fill="toself",
    fillcolor="rgba(0, 120, 215, 0.2)",
    line=dict(color="#0078D7", width=2),
    name=team_a,
))
fig_radar.add_trace(go.Scatterpolar(
    r=vals_b + [vals_b[0]],
    theta=factor_names + [factor_names[0]],
    fill="toself",
    fillcolor="rgba(255, 70, 85, 0.2)",
    line=dict(color="#FF4655", width=2),
    name=team_b,
))
fig_radar.update_layout(
    polar=dict(
        bgcolor="rgba(0,0,0,0)",
        radialaxis=dict(visible=True, gridcolor="#1E2D3D", linecolor="#1E2D3D"),
        angularaxis=dict(gridcolor="#1E2D3D", linecolor="rgba(200,155,60,0.2)"),
    ),
    height=450,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(font=dict(color="#F0E6D2"), bgcolor="rgba(0,0,0,0)"),
    margin=dict(l=60, r=60, t=40, b=40),
)
st.plotly_chart(fig_radar, use_container_width=True)

# Factor comparison bars
st.markdown("#### Factor Advantages")
for factor in FACTOR_COLS:
    fa = breakdown[factor]["team_a"]
    fb = breakdown[factor]["team_b"]
    diff = fa - fb
    factor_label = factor.replace("_", " ").title()

    col_l, col_bar, col_r = st.columns([2, 6, 2])
    with col_l:
        cls = "advantage" if fa > fb else "disadvantage" if fa < fb else ""
        st.markdown(f'<span class="{cls}">{fa:+.2f}</span>', unsafe_allow_html=True)
    with col_bar:
        # Diverging bar
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(x=[diff], y=[factor_label], orientation="h",
                                  marker_color="#0078D7" if diff > 0 else "#FF4655",
                                  text=f"{team_a if diff > 0 else team_b} +{abs(diff):.2f}",
                                  textposition="outside"))
        fig_bar.update_layout(height=50, margin=dict(l=0, r=0, t=0, b=0),
                              xaxis=dict(visible=False, range=[-2, 2]),
                              yaxis=dict(visible=False),
                              paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)",
                              showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)
    with col_r:
        cls = "advantage" if fb > fa else "disadvantage" if fb < fa else ""
        st.markdown(f'<span class="{cls}">{fb:+.2f}</span>', unsafe_allow_html=True)

st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ELO comparison
# ---------------------------------------------------------------------------
st.markdown("### 📈 ELO Trend")

col_elo1, col_elo2 = st.columns(2)
with col_elo1:
    st.metric(f"🔵 {team_a} ELO", f"{result['elo_a']:.0f}")
with col_elo2:
    st.metric(f"🔴 {team_b} ELO", f"{result['elo_b']:.0f}")

# ELO history chart
hist_a = elo_hist[elo_hist["team"] == team_a]
hist_b = elo_hist[elo_hist["team"] == team_b]

if not hist_a.empty or not hist_b.empty:
    fig_elo = go.Figure()
    if not hist_a.empty:
        fig_elo.add_trace(go.Scatter(x=hist_a["date"], y=hist_a["elo"],
                                      mode="lines+markers", name=team_a,
                                      line=dict(color="#0078D7", width=2),
                                      marker=dict(size=5)))
    if not hist_b.empty:
        fig_elo.add_trace(go.Scatter(x=hist_b["date"], y=hist_b["elo"],
                                      mode="lines+markers", name=team_b,
                                      line=dict(color="#FF4655", width=2),
                                      marker=dict(size=5)))
    fig_elo.add_hline(y=1500, line_dash="dash", line_color="rgba(200,155,60,0.27)",
                       annotation_text="Avg (1500)")
    fig_elo.update_layout(
        height=350,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#1E2D3D"),
        yaxis=dict(gridcolor="#1E2D3D", title="ELO Rating"),
        legend=dict(font=dict(color="#F0E6D2"), bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=50, r=20, t=20, b=40),
    )
    st.plotly_chart(fig_elo, use_container_width=True)

# ---------------------------------------------------------------------------
# Strengths & Weaknesses
# ---------------------------------------------------------------------------
st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
st.markdown("### 💪 Strengths & Weaknesses")

sw1, sw2 = st.columns(2)
with sw1:
    st.markdown(f"**🔵 {team_a}**")
    st.markdown(f'✅ Strengths: {", ".join(result["strengths_a"])}')
    st.markdown(f'⚠️ Weaknesses: {", ".join(result["weaknesses_a"])}')
with sw2:
    st.markdown(f"**🔴 {team_b}**")
    st.markdown(f'✅ Strengths: {", ".join(result["strengths_b"])}')
    st.markdown(f'⚠️ Weaknesses: {", ".join(result["weaknesses_b"])}')

# ---------------------------------------------------------------------------
# Head-to-head history
# ---------------------------------------------------------------------------
st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
st.markdown("### 📜 Head-to-Head History")

h2h = get_head_to_head(team_a, team_b)
if h2h.empty:
    st.info(f"No head-to-head games found between {team_a} and {team_b}.")
else:
    h2h_display = h2h[["gameid", "date", "teamname", "side", "result", "kills", "deaths",
                         "gamelength", "totalgold", "golddiffat15"]].copy()
    h2h_display["date"] = h2h_display["date"].dt.strftime("%Y-%m-%d")
    h2h_display["result"] = h2h_display["result"].map({1: "✅ Win", 0: "❌ Loss"})
    h2h_display["gamelength"] = (h2h_display["gamelength"] / 60).round(1)
    h2h_display.columns = ["Game ID", "Date", "Team", "Side", "Result", "Kills", "Deaths",
                            "Length (min)", "Total Gold", "GD@15"]
    st.dataframe(h2h_display, use_container_width=True, hide_index=True)

    # H2H record
    a_wins = len(h2h[(h2h["teamname"] == team_a) & (h2h["result"] == "✅ Win")]) if "result" in h2h.columns else 0
    # Recalculate from original data
    h2h_raw = get_head_to_head(team_a, team_b)
    a_wins = int(h2h_raw[h2h_raw["teamname"] == team_a]["result"].sum())
    b_wins = int(h2h_raw[h2h_raw["teamname"] == team_b]["result"].sum())
    st.markdown(f"**Record: {team_a} {a_wins} - {b_wins} {team_b}**")

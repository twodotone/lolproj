"""
📅 Calendar — Browse past results AND upcoming matches with win projections.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone
from src.data_loader import get_schedule, get_teams, get_team_games, get_leagues
from src.schedule_fetcher import get_upcoming_matches, get_available_leagues, normalize_team_name
from src.elo import compute_all_elo
from src.projection import project_matchup

st.set_page_config(page_title="Calendar | LoL Hub", page_icon="📅", layout="wide")

# Inject shared CSS
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
    .match-card { background: linear-gradient(145deg, #1E2D3D, #0D1B2A); border: 1px solid rgba(200,155,60,0.2);
        border-radius: 12px; padding: 18px; margin: 8px 0; }
    .win { color: #00C9A7; font-weight: 700; }
    .loss { color: #FF6B6B; font-weight: 700; }
    .upcoming-badge { display: inline-block; background: linear-gradient(135deg, #0078D722, #0078D744);
        border: 1px solid #0078D7; border-radius: 20px; padding: 3px 12px;
        font-size: 0.8rem; color: #0078D7; font-weight: 600; }
    .live-badge { display: inline-block; background: linear-gradient(135deg, #FF465522, #FF465544);
        border: 1px solid #FF4655; border-radius: 20px; padding: 3px 12px;
        font-size: 0.8rem; color: #FF4655; font-weight: 600; animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
</style>
""", unsafe_allow_html=True)

# --- Sidebar: League Selector ---
all_leagues = get_leagues()
default_idx = all_leagues.index("LCS") if "LCS" in all_leagues else 0
league = st.sidebar.selectbox(
    "🌍 Select League", all_leagues, index=default_idx, key="cal_league"
)
st.session_state["selected_league"] = league

st.markdown(f'<h1 class="main-title">📅 {league} SCHEDULE</h1>', unsafe_allow_html=True)
st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tabs: Upcoming / Past Results
# ---------------------------------------------------------------------------
tab_upcoming, tab_results = st.tabs(["🔮 Upcoming Matches", "📜 Past Results"])


# ===================================================================
# TAB 1: UPCOMING MATCHES
# ===================================================================
with tab_upcoming:
    available = get_available_leagues()
    if league not in available:
        st.info(f"Schedule API not available for {league}. Available leagues: {', '.join(available)}")
    else:
        upcoming = get_upcoming_matches(league)

        if upcoming.empty:
            st.info(f"No upcoming matches found for {league}.")
        else:
            st.markdown(f"### 🔮 {len(upcoming)} Upcoming Matches")
            st.caption("Win probabilities from our projection model • Powered by Oracle's Elixir + ELO")

            # Precompute ELO and projection data
            games_df = get_team_games()
            elo_dict, _ = compute_all_elo(games_df)

            # Group by date
            upcoming["date_str"] = upcoming["date"].dt.strftime("%A, %B %d, %Y")
            upcoming["date_only"] = upcoming["date"].dt.date
            dates = sorted(upcoming["date_only"].unique())

            for date in dates:
                day_matches = upcoming[upcoming["date_only"] == date]
                date_label = day_matches.iloc[0]["date_str"]

                # Check if it's today
                today = datetime.now(timezone.utc).date()
                is_today = date == today
                day_badge = " 📍 TODAY" if is_today else ""

                st.markdown(f"#### 📆 {date_label}{day_badge}")

                for _, match in day_matches.iterrows():
                    team_a = match["team_a"]
                    team_b = match["team_b"]
                    block = match["block"]
                    match_time = match["date"].strftime("%I:%M %p %Z") if pd.notna(match["date"]) else ""
                    state = match["state"]
                    bo_count = match.get("strategy_count", 1)
                    bo_label = f"Bo{bo_count}" if bo_count > 1 else ""

                    # State badge
                    if state == "inProgress":
                        badge = '<span class="live-badge">🔴 LIVE</span>'
                    else:
                        badge = f'<span class="upcoming-badge">⏰ {match_time}</span>'

                    # Normalize names for projection
                    norm_a = normalize_team_name(team_a)
                    norm_b = normalize_team_name(team_b)

                    # Main match display
                    col1, col_mid, col2 = st.columns([4, 2, 4])

                    with col1:
                        st.markdown(f"**{team_a}**")
                    with col_mid:
                        st.markdown(f"{badge} {bo_label}", unsafe_allow_html=True)
                        st.markdown(f"<center style='color: #A09B8C; font-size: 0.8rem;'>{block}</center>",
                                    unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"**{team_b}**")

                    # Projection (if both teams are known)
                    if team_a != "TBD" and team_b != "TBD":
                        # Try to find team in our data
                        has_a = norm_a in elo_dict
                        has_b = norm_b in elo_dict

                        if has_a and has_b:
                            result = project_matchup(norm_a, norm_b, games_df, elo_dict)
                            prob_a = result["win_prob_a"]
                            prob_b = result["win_prob_b"]

                            with st.expander(f"🔮 {team_a} ({prob_a:.0%}) vs {team_b} ({prob_b:.0%}) — Projection"):
                                # Win probability bar
                                fig = go.Figure()
                                fig.add_trace(go.Bar(
                                    x=[prob_a * 100], y=["Win Probability"],
                                    orientation="h",
                                    marker_color="#0078D7",
                                    name=team_a,
                                    text=f"{team_a}: {prob_a:.1%}",
                                    textposition="inside",
                                    textfont=dict(color="white", size=13),
                                ))
                                fig.add_trace(go.Bar(
                                    x=[prob_b * 100], y=["Win Probability"],
                                    orientation="h",
                                    marker_color="#FF4655",
                                    name=team_b,
                                    text=f"{team_b}: {prob_b:.1%}",
                                    textposition="inside",
                                    textfont=dict(color="white", size=13),
                                ))
                                fig.update_layout(
                                    barmode="stack", height=55,
                                    margin=dict(l=0, r=0, t=0, b=0),
                                    xaxis=dict(visible=False, range=[0, 100]),
                                    yaxis=dict(visible=False),
                                    showlegend=False,
                                    paper_bgcolor="rgba(0,0,0,0)",
                                    plot_bgcolor="rgba(0,0,0,0)",
                                )
                                st.plotly_chart(fig, use_container_width=True)

                                # Factor breakdown
                                p1, p2, p3, p4 = st.columns(4)
                                breakdown = result["factor_breakdown"]
                                with p1:
                                    eg_a = breakdown["early_game"]["team_a"]
                                    eg_b = breakdown["early_game"]["team_b"]
                                    edge = team_a if eg_a > eg_b else team_b
                                    st.metric("⏰ Early Game", f"{edge} edge",
                                              delta=f"{abs(eg_a - eg_b):.2f}")
                                with p2:
                                    oc_a = breakdown["objective_control"]["team_a"]
                                    oc_b = breakdown["objective_control"]["team_b"]
                                    edge = team_a if oc_a > oc_b else team_b
                                    st.metric("🐉 Objectives", f"{edge} edge",
                                              delta=f"{abs(oc_a - oc_b):.2f}")
                                with p3:
                                    tf_a = breakdown["team_fighting"]["team_a"]
                                    tf_b = breakdown["team_fighting"]["team_b"]
                                    edge = team_a if tf_a > tf_b else team_b
                                    st.metric("⚔️ Team Fight", f"{edge} edge",
                                              delta=f"{abs(tf_a - tf_b):.2f}")
                                with p4:
                                    st.metric("📊 ELO",
                                              f"{result['elo_a']:.0f} vs {result['elo_b']:.0f}",
                                              delta=f"{result['elo_edge']} +{abs(result['elo_a'] - result['elo_b']):.0f}")

                                # Playstyle matchup
                                ps1, ps2 = st.columns(2)
                                with ps1:
                                    st.markdown(f"**{team_a}**: {result['playstyle_a']}")
                                    st.markdown(f"✅ {', '.join(result['strengths_a'])}")
                                    st.markdown(f"⚠️ {', '.join(result['weaknesses_a'])}")
                                with ps2:
                                    st.markdown(f"**{team_b}**: {result['playstyle_b']}")
                                    st.markdown(f"✅ {', '.join(result['strengths_b'])}")
                                    st.markdown(f"⚠️ {', '.join(result['weaknesses_b'])}")
                        else:
                            missing = []
                            if not has_a:
                                missing.append(norm_a)
                            if not has_b:
                                missing.append(norm_b)
                            st.caption(f"⚠️ Team data not found for: {', '.join(missing)} — projection unavailable")
                    else:
                        st.caption("🔒 Teams TBD — projection available once teams are determined")

                    st.markdown("---")

                st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)


# ===================================================================
# TAB 2: PAST RESULTS (from Oracle's Elixir CSV)
# ===================================================================
with tab_results:
    sched = get_schedule(league)

    if sched.empty:
        st.warning("No past results found for this league.")
        st.stop()

    # Filters
    col_f1, col_f2, col_f3 = st.columns([2, 2, 2])

    with col_f1:
        teams = ["All Teams"] + get_teams(league)
        team_filter = st.selectbox("🔍 Filter by Team", teams, key="results_team")

    with col_f2:
        min_date = sched["date"].min().date()
        max_date = sched["date"].max().date()
        date_range = st.date_input("📅 Date Range", value=(min_date, max_date),
                                    min_value=min_date, max_value=max_date,
                                    key="results_dates")

    with col_f3:
        sort_order = st.radio("📋 Sort", ["Newest First", "Oldest First"],
                               horizontal=True, key="results_sort")

    # Apply filters
    filtered = sched.copy()

    if team_filter != "All Teams":
        filtered = filtered[(filtered["blue_team"] == team_filter) |
                             (filtered["red_team"] == team_filter)]

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        filtered = filtered[(filtered["date"].dt.date >= start) &
                             (filtered["date"].dt.date <= end)]

    if sort_order == "Newest First":
        filtered = filtered.sort_values("date", ascending=False)

    st.markdown(f"**Showing {len(filtered)} games**")
    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    if filtered.empty:
        st.info("No matches found for the selected filters.")
    else:
        filtered["date_str"] = filtered["date"].dt.strftime("%A, %B %d, %Y")
        dates = filtered["date"].dt.date.unique()

        for date in dates:
            day_games = filtered[filtered["date"].dt.date == date]
            date_label = day_games.iloc[0]["date_str"]

            st.markdown(f"#### 📆 {date_label}")

            for _, game in day_games.iterrows():
                blue = game["blue_team"]
                red = game["red_team"]
                blue_won = game["blue_result"] == 1

                blue_class = "win" if blue_won else "loss"
                red_class = "loss" if blue_won else "win"

                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 3])

                with col1:
                    icon = "🏆" if blue_won else ""
                    st.markdown(f'<span class="{blue_class}" style="font-size: 1.1rem;">{icon} {blue}</span>',
                                unsafe_allow_html=True)
                with col2:
                    st.markdown(f"**{int(game['blue_kills'])}**")
                with col3:
                    st.markdown(f"⚔️ **vs** ⚔️")
                with col4:
                    st.markdown(f"**{int(game['red_kills'])}**")
                with col5:
                    icon = "🏆" if not blue_won else ""
                    st.markdown(f'<span class="{red_class}" style="font-size: 1.1rem;">{red} {icon}</span>',
                                unsafe_allow_html=True)

                # Expandable details
                with st.expander(f"📊 Match Details — {blue} vs {red}"):
                    d1, d2, d3, d4 = st.columns(4)
                    gl = game["game_length_min"]
                    gd = game["gold_diff"]
                    with d1:
                        st.metric("⏱️ Game Length", f"{gl} min")
                    with d2:
                        gd_display = f"+{int(gd)}" if gd > 0 else str(int(gd))
                        gd_label = f"{'Blue' if gd > 0 else 'Red'} Advantage"
                        st.metric(f"💰 Gold Diff", gd_display, delta=gd_label)
                    with d3:
                        st.metric("🐉 Dragons", f"{int(game['blue_dragons'])} - {int(game['red_dragons'])}")
                    with d4:
                        st.metric("👑 Barons", f"{int(game['blue_barons'])} - {int(game['red_barons'])}")

                    # Gold comparison bar
                    total_gold = game["blue_gold"] + game["red_gold"]
                    blue_pct = game["blue_gold"] / total_gold * 100 if total_gold > 0 else 50

                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=[blue_pct], y=["Gold Share"], orientation="h",
                                          marker_color="#0078D7", name=blue,
                                          text=f"{blue}: {int(game['blue_gold']):,}g",
                                          textposition="inside"))
                    fig.add_trace(go.Bar(x=[100 - blue_pct], y=["Gold Share"], orientation="h",
                                          marker_color="#FF4655", name=red,
                                          text=f"{red}: {int(game['red_gold']):,}g",
                                          textposition="inside"))
                    fig.update_layout(barmode="stack", height=60,
                                      margin=dict(l=0, r=0, t=0, b=0),
                                      xaxis=dict(visible=False),
                                      yaxis=dict(visible=False),
                                      showlegend=False,
                                      paper_bgcolor="rgba(0,0,0,0)",
                                      plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig, use_container_width=True)

                    # Objectives
                    obj1, obj2 = st.columns(2)
                    with obj1:
                        st.markdown(f"**🔵 {blue}**")
                        st.markdown(f"🗼 Towers: {int(game['blue_towers'])} | 🐉 Dragons: {int(game['blue_dragons'])} | 👑 Barons: {int(game['blue_barons'])}")
                    with obj2:
                        st.markdown(f"**🔴 {red}**")
                        st.markdown(f"🗼 Towers: {int(game['red_towers'])} | 🐉 Dragons: {int(game['red_dragons'])} | 👑 Barons: {int(game['red_barons'])}")

            st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    # Games-per-day chart
    st.markdown("### 📈 Games Per Day")
    games_per_day = sched.groupby(sched["date"].dt.date).size().reset_index(name="games")
    games_per_day.columns = ["Date", "Games"]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=games_per_day["Date"], y=games_per_day["Games"],
                          marker_color="#C89B3C", marker_line_color="#F0E6D2",
                          marker_line_width=1))
    fig.update_layout(
        height=250,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#1E2D3D"),
        yaxis=dict(gridcolor="#1E2D3D", title="Games"),
        margin=dict(l=40, r=20, t=20, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

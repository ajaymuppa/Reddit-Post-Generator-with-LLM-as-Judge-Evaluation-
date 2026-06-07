"""
eval_dashboard.py — Eval Dashboard
Reddit Post Generator

Run with: streamlit run eval_dashboard.py
Or navigate to it via the main app sidebar link.

Shows score trends, per-subreddit breakdowns, and top/worst posts.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from eval_store import (
    get_all_generations, get_score_trends,
    get_summary_stats, get_top_posts, list_subreddits
)
from llm_helper import list_subreddits as get_subreddit_list

# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Eval Dashboard",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
    h1, h2, h3 { font-family: 'IBM Plex Mono', monospace; }
    .metric-box {
        background: #1a1a2e;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .metric-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.8rem;
        font-weight: 600;
        color: #e94560;
    }
    .metric-label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.08em; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("# 📊 Eval Dashboard")
st.markdown("*Track generation quality over time and across subreddits*")
st.markdown("---")

# ── Sidebar Filters ───────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Filters")
    subreddits    = ["All"] + get_subreddit_list()
    selected_sub  = st.selectbox("Subreddit", subreddits)
    filter_sub    = None if selected_sub == "All" else selected_sub
    st.page_link("main.py", label="⚡ Back to Generator", icon="⚡")

# ── Load Data ─────────────────────────────────────────────────────────────────

all_gens  = get_all_generations(filter_sub)
trends    = get_score_trends(filter_sub)
stats     = get_summary_stats(filter_sub)
top_posts = get_top_posts(5, filter_sub)

if not all_gens:
    st.info("No generations logged yet. Go generate some posts first!")
    st.stop()

df       = pd.DataFrame(all_gens)
trend_df = pd.DataFrame(trends)

# ── Summary Metrics ───────────────────────────────────────────────────────────

st.markdown("### Summary")
m1, m2, m3, m4, m5 = st.columns(5)

metrics = [
    (m1, "Total Posts",     stats.get("total", 0),         ""),
    (m2, "Avg Overall",     stats.get("avg_overall", 0),   "/10"),
    (m3, "Avg Tone Match",  stats.get("avg_tone", 0),      "/10"),
    (m4, "👍 Thumbs Up",    stats.get("thumbs_up", 0),     ""),
    (m5, "👎 Thumbs Down",  stats.get("thumbs_down", 0),   ""),
]

for col, label, value, suffix in metrics:
    with col:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{value}{suffix}</div>
            <div class="metric-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ── Score Trends Over Time ────────────────────────────────────────────────────

st.markdown("### Score Trends Over Time")

if len(trend_df) >= 2:
    trend_df["timestamp"] = pd.to_datetime(trend_df["timestamp"])
    trend_df = trend_df.sort_values("timestamp")

    dim_cols = {
        "average_score":         "Average",
        "rule_compliance":       "Rule Compliance",
        "tone_match":            "Tone Match",
        "title_clickability":    "Title Clickability",
        "authenticity":          "Authenticity",
        "engagement_potential":  "Engagement Potential",
    }

    selected_dims = st.multiselect(
        "Dimensions to show",
        options=list(dim_cols.keys()),
        default=["average_score", "tone_match", "authenticity"],
        format_func=lambda x: dim_cols[x],
    )

    if selected_dims:
        fig = go.Figure()
        colors = ["#e94560", "#3a7bd5", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"]

        for i, dim in enumerate(selected_dims):
            fig.add_trace(go.Scatter(
                x=trend_df["timestamp"],
                y=trend_df[dim],
                mode="lines+markers",
                name=dim_cols[dim],
                line=dict(color=colors[i % len(colors)], width=2),
                marker=dict(size=6),
            ))

        fig.update_layout(
            plot_bgcolor="#0f0f1a",
            paper_bgcolor="#0f0f1a",
            font=dict(color="#ccc", family="IBM Plex Mono"),
            xaxis=dict(gridcolor="#222", title="Time"),
            yaxis=dict(gridcolor="#222", title="Score", range=[0, 10]),
            legend=dict(bgcolor="#1a1a2e", bordercolor="#333"),
            hovermode="x unified",
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Generate at least 2 posts to see trends.")

st.markdown("---")

# ── Per-Subreddit Radar Chart ─────────────────────────────────────────────────

st.markdown("### Average Scores by Subreddit")

sub_stats = []
for sub in get_subreddit_list():
    s = get_summary_stats(sub)
    if s.get("total", 0) > 0:
        sub_stats.append({
            "subreddit": sub,
            "Rule Compliance":      s.get("avg_rule",   0),
            "Tone Match":           s.get("avg_tone",   0),
            "Title Clickability":   s.get("avg_title",  0),
            "Authenticity":         s.get("avg_auth",   0),
            "Engagement Potential": s.get("avg_engage", 0),
        })

if sub_stats:
    sub_df = pd.DataFrame(sub_stats)
    fig2   = px.bar(
        sub_df.melt(id_vars="subreddit", var_name="Dimension", value_name="Score"),
        x="subreddit", y="Score", color="Dimension",
        barmode="group",
        color_discrete_sequence=["#e94560", "#3a7bd5", "#2ecc71", "#f39c12", "#9b59b6"],
    )
    fig2.update_layout(
        plot_bgcolor="#0f0f1a",
        paper_bgcolor="#0f0f1a",
        font=dict(color="#ccc", family="IBM Plex Mono"),
        xaxis=dict(gridcolor="#222"),
        yaxis=dict(gridcolor="#222", range=[0, 10]),
        legend=dict(bgcolor="#1a1a2e"),
        height=380,
    )
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ── Top Posts ─────────────────────────────────────────────────────────────────

st.markdown("### 🏆 Top 5 Posts by Score")

for i, post in enumerate(top_posts, 1):
    with st.expander(f"#{i} — {post['subreddit']} — Score: {post['average_score']:.1f}/10 — {post['title'][:80]}..."):
        st.markdown(f"**Subreddit:** {post['subreddit']}")
        st.markdown(f"**Topic:** {post['topic']}")
        st.markdown(f"**Generated:** {post['timestamp'][:19]}")
        st.markdown("**Title:**")
        st.code(post["title"], language=None)
        st.markdown("**Body:**")
        st.code(post["body"], language=None)
        c1, c2, c3, c4, c5 = st.columns(5)
        for col, label, key in zip(
            [c1, c2, c3, c4, c5],
            ["Rule", "Tone", "Title", "Auth", "Engage"],
            ["rule_compliance", "tone_match", "title_clickability", "authenticity", "engagement_potential"]
        ):
            col.metric(label, f"{post[key]:.1f}")

st.markdown("---")

# ── Full History Table ────────────────────────────────────────────────────────

st.markdown("### 📋 Full History")

display_cols = [
    "timestamp", "subreddit", "topic",
    "average_score", "rule_compliance", "tone_match",
    "title_clickability", "authenticity", "engagement_potential",
    "overall_score", "user_rating"
]
show_df = df[display_cols].copy()
show_df["timestamp"] = pd.to_datetime(show_df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M")
show_df = show_df.sort_values("timestamp", ascending=False)

st.dataframe(
    show_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "average_score":         st.column_config.NumberColumn("Avg Score", format="%.1f"),
        "rule_compliance":       st.column_config.NumberColumn("Rules", format="%.1f"),
        "tone_match":            st.column_config.NumberColumn("Tone", format="%.1f"),
        "title_clickability":    st.column_config.NumberColumn("Title", format="%.1f"),
        "authenticity":          st.column_config.NumberColumn("Auth", format="%.1f"),
        "engagement_potential":  st.column_config.NumberColumn("Engage", format="%.1f"),
        "overall_score":         st.column_config.NumberColumn("Overall", format="%.1f"),
        "user_rating":           st.column_config.NumberColumn("Feedback"),
    }
)

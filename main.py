"""
main.py — Reddit Post Generator + Eval UI
Streamlit application

Run with: streamlit run main.py
"""

import streamlit as st
from llm_helper import generate_post, load_profile, list_subreddits
from evaluator import evaluate_post
from eval_store import log_generation, update_feedback

# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Reddit Post Generator",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }
    h1, h2, h3 {
        font-family: 'IBM Plex Mono', monospace;
    }
    .score-card {
        background: #1a1a2e;
        border: 1px solid #e94560;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        color: white;
    }
    .score-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 2rem;
        font-weight: 600;
        color: #e94560;
    }
    .score-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #aaa;
        margin-top: 4px;
    }
    .post-box {
        background: #0f0f1a;
        border-left: 3px solid #e94560;
        border-radius: 4px;
        padding: 20px;
        color: #e0e0e0;
        font-family: 'IBM Plex Sans', sans-serif;
        line-height: 1.7;
    }
    .post-title {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.1rem;
        font-weight: 600;
        color: #e94560;
        margin-bottom: 12px;
    }
    .improvement-box {
        background: #0d2137;
        border: 1px solid #3a7bd5;
        border-radius: 6px;
        padding: 14px;
        color: #90cdf4;
        font-size: 0.9rem;
    }
    .stButton > button {
        background-color: #e94560;
        color: white;
        border: none;
        border-radius: 4px;
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 600;
        letter-spacing: 0.05em;
        padding: 10px 24px;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #c73652;
    }
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────────────────

if "generated_post" not in st.session_state:
    st.session_state.generated_post = None
if "eval_result" not in st.session_state:
    st.session_state.eval_result = None
if "row_id" not in st.session_state:
    st.session_state.row_id = None
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = False

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("# 🤖 Reddit Post Generator")
    st.markdown("*Powered by GPT-4o + LLM-as-Judge evaluation*")
    st.markdown("---")

    available = list_subreddits()
    subreddit = st.selectbox("Target Subreddit", available)

    topic = st.text_area(
        "Topic / What to post about",
        placeholder="e.g. I just paid off my student loans using the avalanche method",
        height=100,
    )

    post_type = st.selectbox(
        "Post Type",
        ["Discussion", "Story / Experience", "Question", "Advice Request", "Resource / Tips"],
    )

    extra_context = st.text_input(
        "Extra context (optional)",
        placeholder="e.g. I'm 26, earning $65k, in the US",
    )

    st.markdown("---")
    generate_btn = st.button("⚡ Generate & Evaluate")
    st.markdown("---")
    st.page_link("eval_dashboard.py", label="📊 View Eval Dashboard", icon="📊")

# ── Main Panel ────────────────────────────────────────────────────────────────

st.markdown("## Generate Post")

if generate_btn:
    if not topic.strip():
        st.warning("Please enter a topic before generating.")
    else:
        st.session_state.feedback_given = False

        with st.spinner(f"Generating post for {subreddit}..."):
            profile = load_profile(subreddit)
            post    = generate_post(topic, subreddit, post_type.lower(), extra_context)
            st.session_state.generated_post = post

        with st.spinner("Evaluating with LLM judge..."):
            result = evaluate_post(
                post["title"], post["body"], subreddit, profile
            )
            st.session_state.eval_result = result

        # Log to SQLite
        row_id = log_generation(
            subreddit, topic, post_type,
            post["title"], post["body"], result
        )
        st.session_state.row_id = row_id


# ── Display Generated Post ────────────────────────────────────────────────────

if st.session_state.generated_post and st.session_state.eval_result:
    post   = st.session_state.generated_post
    result = st.session_state.eval_result

    st.markdown("### 📝 Generated Post")
    st.markdown(f"""
    <div class="post-box">
        <div class="post-title">{post['title']}</div>
        {post['body'].replace(chr(10), '<br>')}
    </div>
    """, unsafe_allow_html=True)

    # Copy buttons
    col1, col2 = st.columns(2)
    with col1:
        st.code(post["title"], language=None)
    with col2:
        st.code(post["body"], language=None)

    st.markdown("---")

    # ── Score Cards ───────────────────────────────────────────────────────────

    st.markdown("### 📊 Evaluation Scores")

    dims = [
        ("rule_compliance",      "Rule\nCompliance"),
        ("tone_match",           "Tone\nMatch"),
        ("title_clickability",   "Title\nClickability"),
        ("authenticity",         "Authenticity"),
        ("engagement_potential", "Engagement\nPotential"),
    ]

    cols = st.columns(5)
    for col, (dim_key, label) in zip(cols, dims):
        dim   = getattr(result, dim_key)
        score = dim.score
        color = "#2ecc71" if score >= 7 else "#f39c12" if score >= 5 else "#e74c3c"
        with col:
            st.markdown(f"""
            <div class="score-card">
                <div class="score-value" style="color:{color}">{score:.1f}</div>
                <div class="score-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    # Overall score banner
    avg = result.average_score()
    overall = result.overall_score.score
    st.markdown(f"""
    <div style="background:#1a1a2e; border:2px solid #e94560; border-radius:8px;
                padding:16px; text-align:center; margin-top:16px;">
        <span style="font-family:'IBM Plex Mono',monospace; font-size:1.4rem; color:#e94560; font-weight:600;">
            Overall: {overall:.1f} / 10
        </span>
        &nbsp;&nbsp;
        <span style="color:#aaa; font-size:0.9rem;">
            (avg of 5 dimensions: {avg:.1f})
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Detailed Reasoning ────────────────────────────────────────────────────

    st.markdown("### 🔍 Detailed Feedback")
    with st.expander("See reasoning for each dimension", expanded=False):
        for dim_key, label in dims:
            dim = getattr(result, dim_key)
            score = dim.score
            color = "🟢" if score >= 7 else "🟡" if score >= 5 else "🔴"
            st.markdown(f"**{color} {label.replace(chr(10), ' ')} ({score:.1f}/10)**")
            st.markdown(f"> {dim.reasoning}")
            st.markdown("")

        st.markdown(f"**Overall ({result.overall_score.score:.1f}/10)**")
        st.markdown(f"> {result.overall_score.reasoning}")

    # Improvement suggestion
    st.markdown("### 💡 Suggested Improvement")
    st.markdown(f"""
    <div class="improvement-box">
        {result.improvement_suggestion}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── User Feedback ─────────────────────────────────────────────────────────

    st.markdown("### 👍 Rate this post")
    if not st.session_state.feedback_given:
        fb_col1, fb_col2, _ = st.columns([1, 1, 3])
        with fb_col1:
            if st.button("👍 Good post"):
                update_feedback(st.session_state.row_id, 1)
                st.session_state.feedback_given = True
                st.success("Thanks for the feedback!")
        with fb_col2:
            if st.button("👎 Needs work"):
                update_feedback(st.session_state.row_id, -1)
                st.session_state.feedback_given = True
                st.info("Feedback logged — helps improve future generations.")
    else:
        st.success("✅ Feedback logged.")

else:
    st.markdown("""
    <div style="text-align:center; padding:60px 20px; color:#555;">
        <div style="font-size:3rem;">🤖</div>
        <div style="font-family:'IBM Plex Mono',monospace; margin-top:12px;">
            Choose a subreddit, enter a topic, and hit Generate.
        </div>
    </div>
    """, unsafe_allow_html=True)

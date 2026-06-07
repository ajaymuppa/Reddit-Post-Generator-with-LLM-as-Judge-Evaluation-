# 🤖 Reddit Post Generator + LLM-as-Judge

A subreddit-aware Reddit post generator powered by GPT-4o, with an automated **LLM-as-Judge** evaluation system that scores every post across five dimensions — plus a feedback loop that learns from your ratings to improve future posts.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-app-FF4B4B)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991)
![LangChain](https://img.shields.io/badge/LangChain-FAISS-1C3C3C)

---

## What it does

Pick a subreddit and a topic, and the app generates a post written to fit that community's specific culture — its tone, rules, banned phrases, and the shape of posts that actually do well there. Every generated post is then scored by GPT-4o acting as a veteran Reddit moderator, with a transparent breakdown and a concrete suggestion for improvement. Your 👍/👎 ratings are logged and fed back in, so the generator gets sharper for each community over time.

## Features

- **Subreddit-aware generation** — each subreddit has a cultural profile (tone, audience, rules, banned phrases, and high-performing example posts).
- **Dynamic few-shot retrieval** — FAISS embeds the example posts and pulls the most relevant ones for your topic at generation time.
- **LLM-as-Judge evaluation** — GPT-4o (temperature 0) scores every post on Rule Compliance, Tone Match, Title Clickability, Authenticity, and Engagement Potential, plus an overall score and a one-line improvement.
- **Feedback-conditioned generation** — 👍/👎 ratings are logged *and read back*: future posts for a subreddit are steered toward your highest-rated posts and away from your thumbs-down ones.
- **SQLite logging** — every generation and score is persisted for analysis.
- **Eval dashboard** — a separate Streamlit + Plotly dashboard showing score trends over time and per-subreddit breakdowns.

## Demo

<!-- Add a screenshot: create a docs/ folder, drop an image in it, then uncomment the line below -->
<!-- ![Reddit Post Generator](docs/screenshot.png) -->

_Add a screenshot of the generator and score card here._

## Tech stack

Python · Streamlit · OpenAI GPT-4o · LangChain + FAISS (few-shot retrieval) · Pydantic (structured output) · SQLite · Plotly

## Supported subreddits

- r/MachineLearning
- r/personalfinance
- r/explainlikeimfive
- r/entrepreneur
- r/productivity

## How it works

```
User input (topic + subreddit)
        │
        ▼
Subreddit profile loader
        │
        ▼
Few-shot retriever (FAISS)  +  Past feedback (👍/👎 from SQLite)
        │
        ▼
GPT-4o post generator
        │
        ▼
LLM-as-Judge evaluator (GPT-4o, temp = 0)
        │
        ▼
Score card + reasoning + improvement  (Streamlit)
        │
        ▼
SQLite log  →  Eval dashboard
```

## Getting started

### 1. Clone and install

```bash
git clone https://github.com/<your-username>/reddit-post-generator.git
cd reddit-post-generator

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add your OpenAI API key

```bash
cp .env.example .env            # Windows: copy .env.example .env
```

Open `.env` and paste your key after `OPENAI_API_KEY=`.

> **Note:** This uses the OpenAI API (GPT-4o + embeddings), which is pay-as-you-go and separate from a ChatGPT subscription. OpenAI billing is prepaid, so your account needs a payment method **and** a positive credit balance — otherwise the API returns `429 insufficient_quota`. A few dollars is plenty.

### 3. Run the generator

```bash
streamlit run main.py
```

### 4. Run the eval dashboard (optional, separate terminal)

```bash
streamlit run eval_dashboard.py
```

## The feedback loop

Thumbs up/down isn't just logged — it shapes the next generation:

1. You rate a generated post 👍 or 👎 (stored in `eval_results.db`).
2. On the next generation for that subreddit, the app pulls your top thumbs-up posts (by eval score) and your thumbs-down posts (with the judge's improvement note).
3. Those are injected into the prompt as "emulate these / avoid these" examples, alongside the FAISS-retrieved profile examples.

Cold start is a no-op: with no feedback yet, generation behaves normally. Once feedback exists, the sidebar shows a 👍/👎 tally per subreddit.

## Project structure

```
reddit-post-generator/
├── main.py                  # Generator UI (Streamlit)
├── eval_dashboard.py        # Eval dashboard (Streamlit + Plotly)
├── llm_helper.py            # GPT-4o generation + FAISS few-shot + feedback steering
├── evaluator.py             # LLM-as-Judge scoring (Pydantic-validated)
├── eval_store.py            # SQLite logging + feedback reads
├── requirements.txt
├── .env.example             # Template for your API key (copy to .env)
├── .gitignore
├── subreddit_profiles/      # One JSON profile per subreddit
│   ├── MachineLearning.json
│   ├── personalfinance.json
│   ├── explainlikeimfive.json
│   ├── entrepreneur.json
│   └── productivity.json
└── eval_results.db          # Auto-created on first run (git-ignored)
```

## Adding a new subreddit

Drop a JSON file into `subreddit_profiles/` following this schema:

```json
{
  "subreddit": "r/YourSubreddit",
  "tone": "...",
  "audience": "...",
  "rules": ["rule 1", "rule 2"],
  "banned_phrases": ["phrase 1", "phrase 2"],
  "title_format": "...",
  "body_format": "...",
  "upvote_patterns": "...",
  "example_posts": [
    { "title": "...", "body": "...", "upvotes": 1000 }
  ]
}
```

It's picked up automatically — no code changes needed.

## What you can measure

Because every generation and rating is logged, you can track average score per subreddit, score changes across prompt iterations, the 👍/👎 ratio, and JSON parse success rate — useful signals for tuning prompts or summarizing the project.

## License

No license is included yet. To open-source it, add a `LICENSE` file (MIT is a common choice).

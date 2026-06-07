"""
llm_helper.py — Post Generation + Few-Shot Retrieval
Reddit Post Generator

Uses GPT-4o for generation with dynamic few-shot examples
retrieved via FAISS embeddings from subreddit profiles.
"""

import json
import os
from pathlib import Path

from openai import OpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

client = OpenAI()
PROFILES_DIR = Path(__file__).parent / "subreddit_profiles"
EMBED_MODEL   = "text-embedding-3-small"

# ── Load Subreddit Profiles ───────────────────────────────────────────────────

def load_profile(subreddit: str) -> dict:
    """Load subreddit profile JSON by name."""
    name = subreddit.replace("r/", "")
    path = PROFILES_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"No profile found for {subreddit}")
    with open(path) as f:
        return json.load(f)


def list_subreddits() -> list[str]:
    """Return all available subreddit names."""
    return [f"r/{p.stem}" for p in PROFILES_DIR.glob("*.json")]


# ── Dynamic Few-Shot Retrieval ────────────────────────────────────────────────

def build_few_shot_retriever(profile: dict):
    """
    Build a FAISS retriever over the subreddit's example posts.
    At query time, returns the most relevant example for the topic.
    """
    examples = profile.get("example_posts", [])
    if not examples:
        return None

    docs = [
        Document(
            page_content=f"Title: {ex['title']}\nBody: {ex['body']}",
            metadata={"upvotes": ex.get("upvotes", 0)}
        )
        for ex in examples
    ]
    embeddings  = OpenAIEmbeddings(model=EMBED_MODEL)
    vectorstore = FAISS.from_documents(docs, embeddings)
    return vectorstore


def get_relevant_examples(topic: str, profile: dict, k: int = 2) -> str:
    """Retrieve the most relevant example posts for the given topic."""
    retriever = build_few_shot_retriever(profile)
    if not retriever:
        return "No examples available."

    results = retriever.similarity_search(topic, k=k)
    formatted = []
    for i, doc in enumerate(results, 1):
        formatted.append(f"Example {i}:\n{doc.page_content}")
    return "\n\n".join(formatted)


# ── Generation Prompt ─────────────────────────────────────────────────────────

GENERATION_SYSTEM = """You are an expert Reddit user who has spent years 
participating authentically in various subreddit communities. You deeply 
understand each community's culture, tone, and unwritten rules.

Your task is to generate a Reddit post that would genuinely belong in the 
target subreddit — not something that looks AI-generated or out of place.

Always return your response as valid JSON with exactly these keys:
{{
  "title": "<post title>",
  "body": "<post body>"
}}

Return ONLY the JSON. No preamble, no markdown fences."""


def generate_post(
    topic: str,
    subreddit: str,
    post_type: str = "discussion",
    extra_context: str = "",
) -> dict:
    """
    Generate a Reddit post for the given topic and subreddit.

    Returns dict with keys: title, body
    """
    profile  = load_profile(subreddit)
    examples = get_relevant_examples(topic, profile)

    user_prompt = f"""Generate a Reddit post for {subreddit} about: {topic}

SUBREDDIT PROFILE:
- Tone: {profile['tone']}
- Audience: {profile['audience']}
- Title format: {profile['title_format']}
- Body format: {profile['body_format']}

RULES TO FOLLOW:
{chr(10).join(f'- {r}' for r in profile['rules'])}

PHRASES TO AVOID:
{', '.join(profile['banned_phrases'])}

POST TYPE: {post_type}
{f'EXTRA CONTEXT: {extra_context}' if extra_context else ''}

RELEVANT EXAMPLE POSTS FROM THIS SUBREDDIT:
{examples}

Now generate an original post in the same spirit. Be specific, authentic, 
and match the community's voice exactly."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": GENERATION_SYSTEM},
            {"role": "user",   "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )

    raw = response.choices[0].message.content
    return json.loads(raw)

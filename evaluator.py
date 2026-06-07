"""
evaluator.py — LLM-as-Judge Evaluation Layer
Reddit Post Generator

Scores every generated post across 5 dimensions using GPT-4o as judge.
Uses Pydantic for structured output validation.
"""

import json
from openai import OpenAI
from pydantic import BaseModel, field_validator

client = OpenAI()

# ── Pydantic Models ───────────────────────────────────────────────────────────

class DimensionScore(BaseModel):
    score: float
    reasoning: str

    @field_validator("score")
    @classmethod
    def clamp_score(cls, v):
        return max(0.0, min(10.0, float(v)))


class EvalResult(BaseModel):
    rule_compliance:      DimensionScore
    tone_match:           DimensionScore
    title_clickability:   DimensionScore
    authenticity:         DimensionScore
    engagement_potential: DimensionScore
    overall_score:        DimensionScore
    improvement_suggestion: str

    def average_score(self) -> float:
        dims = [
            self.rule_compliance.score,
            self.tone_match.score,
            self.title_clickability.score,
            self.authenticity.score,
            self.engagement_potential.score,
        ]
        return round(sum(dims) / len(dims), 2)

    def to_dict(self) -> dict:
        return {
            "rule_compliance":      {"score": self.rule_compliance.score,      "reasoning": self.rule_compliance.reasoning},
            "tone_match":           {"score": self.tone_match.score,           "reasoning": self.tone_match.reasoning},
            "title_clickability":   {"score": self.title_clickability.score,   "reasoning": self.title_clickability.reasoning},
            "authenticity":         {"score": self.authenticity.score,         "reasoning": self.authenticity.reasoning},
            "engagement_potential": {"score": self.engagement_potential.score, "reasoning": self.engagement_potential.reasoning},
            "overall_score":        {"score": self.overall_score.score,        "reasoning": self.overall_score.reasoning},
            "improvement_suggestion": self.improvement_suggestion,
            "average_score": self.average_score(),
        }


# ── Judge Prompt ──────────────────────────────────────────────────────────────

JUDGE_SYSTEM = """You are a veteran Reddit moderator and power user with 10+ 
years of experience across dozens of subreddits. You understand what makes 
posts succeed or fail in specific communities — not just generic writing quality,
but cultural fit, community norms, and authentic voice.

Always return a valid JSON object with EXACTLY this structure and nothing else:
{{
  "rule_compliance":      {{"score": <0-10>, "reasoning": "<1-2 sentences>"}},
  "tone_match":           {{"score": <0-10>, "reasoning": "<1-2 sentences>"}},
  "title_clickability":   {{"score": <0-10>, "reasoning": "<1-2 sentences>"}},
  "authenticity":         {{"score": <0-10>, "reasoning": "<1-2 sentences>"}},
  "engagement_potential": {{"score": <0-10>, "reasoning": "<1-2 sentences>"}},
  "overall_score":        {{"score": <0-10>, "reasoning": "<2-3 sentences>"}},
  "improvement_suggestion": "<one specific, actionable improvement>"
}}"""

JUDGE_USER = """Evaluate this Reddit post for {subreddit}:

TITLE: {title}
BODY: {body}

SUBREDDIT CONTEXT:
- Expected tone: {tone}
- Rules: {rules}
- Banned phrases: {banned_phrases}

SCORING GUIDE:
- rule_compliance (0-10): Does the post follow all subreddit rules? 
  Does it use any banned phrases or violate content policies?
- tone_match (0-10): Does the post sound like it genuinely belongs 
  in {subreddit}? Does it match the community's voice and culture?
- title_clickability (0-10): Will the title attract clicks without 
  being clickbait? Is it specific and compelling for this community?
- authenticity (0-10): Does this read like a real human post or does 
  it feel AI-generated, generic, or inauthentic?
- engagement_potential (0-10): Will this generate meaningful comments 
  and discussion? Does it invite responses?
- overall_score (0-10): Holistic quality — would this post do well 
  in {subreddit}? Would a moderator approve it?

Be strict and honest. A score of 7+ should mean genuinely good."""


def evaluate_post(
    title: str,
    body: str,
    subreddit: str,
    profile: dict,
) -> EvalResult:
    """
    Evaluate a Reddit post using GPT-4o as judge.
    Returns a validated EvalResult with scores + reasoning.
    """
    prompt = JUDGE_USER.format(
        subreddit=subreddit,
        title=title,
        body=body,
        tone=profile.get("tone", ""),
        rules="\n".join(f"- {r}" for r in profile.get("rules", [])),
        banned_phrases=", ".join(profile.get("banned_phrases", [])),
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user",   "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,  # deterministic scoring
    )

    raw  = response.choices[0].message.content
    data = json.loads(raw)
    return EvalResult(**data)

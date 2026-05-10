"""
Scorer Agent — grades each rubric criterion with full XAI transparency.
Accepts instructor correction examples (RL few-shot) to calibrate scoring
to the instructor's grading style over time.
"""

import json
import anthropic


def score(
    client: anthropic.Anthropic,
    analysis: str,
    submission_text: str,
    context: str,
    rubric: dict,
    rl_examples: str = "",          # formatted few-shot block from rl_corrections
) -> dict:
    criteria_json = json.dumps(rubric["criteria"], indent=2)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=5000,
        system=f"""You are a fair, rigorous, and transparent academic grader with XAI principles.
Score submissions against rubric criteria with complete transparency about your reasoning.

XAI principles to follow:
- Cite specific evidence (direct quotes or concrete references) for every score
- Assign a confidence score (0.0–1.0) reflecting how clear-cut the evidence is
- Provide counterfactual reasoning: what would the student need to do to earn the next level up?
- Note any uncertainty or ambiguity that influenced your decision
{rl_examples}
{context}""",
        messages=[
            {
                "role": "user",
                "content": f"""Score this submission against every rubric criterion with full XAI transparency.
{f"Apply the instructor calibration examples above when scoring." if rl_examples else ""}

SUBMISSION ANALYSIS:
{analysis}

ORIGINAL SUBMISSION (for direct quoting):
---
{submission_text}
---

RUBRIC CRITERIA:
{criteria_json}

Return ONLY valid JSON — no other text:
{{
  "scores": [
    {{
      "criterion_id": "<id>",
      "criterion_name": "<name>",
      "level_awarded": "<excellent|competent|needs_improvement|inadequate>",
      "points_awarded": <exact rubric value for that level>,
      "max_points": <number>,
      "confidence": <0.0–1.0>,
      "evidence": "<direct quote or specific reference from submission>",
      "rationale": "<why this level and not higher or lower>",
      "counterfactual": "<what would earn the next level up>",
      "uncertainty_notes": "<any ambiguity, or null if clear-cut>"
    }}
  ],
  "total_points": <sum>,
  "total_possible": {rubric['total_points']},
  "overall_confidence": <mean of all confidence scores>
}}""",
            }
        ],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())

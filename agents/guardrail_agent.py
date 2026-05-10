"""
Guardrail Agent — validates a submission meets minimum requirements before
full grading. Flags edge cases for human review.
"""

import json
import anthropic

MINIMUM_ALGORITHMS = 8
MINIMUM_WORDS = 150


def validate(client: anthropic.Anthropic, submission_text: str, context: str) -> dict:
    """Returns a guardrail report. If passes_guardrails is False, grading halts."""

    word_count = len(submission_text.split())

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=f"""You are a submission pre-screening validator for an academic grading system.
Assess whether a student submission meets the minimum requirements to be graded.

{context}""",
        messages=[
            {
                "role": "user",
                "content": f"""Validate this submission. Respond ONLY with valid JSON.

Submission ({word_count} words):
---
{submission_text}
---

Check each of the following:
1. RELEVANCE: Does the submission address machine learning algorithms? (not a different subject)
2. ALGORITHM_COUNT: Count how many distinct ML algorithms are mentioned or described. Minimum required: {MINIMUM_ALGORITHMS}
3. HAS_CLASSIFICATION: Does it classify algorithms by type (supervised/unsupervised) or domain?
4. HAS_VISUAL_DESCRIPTION: Does it describe or reference a visual framework or infographic?
5. HAS_REFLECTION: Is there a personal learning reflection or discussion of the experience?
6. INAPPROPRIATE_CONTENT: Any academic dishonesty indicators or inappropriate content?

Return JSON exactly:
{{
  "is_relevant": true|false,
  "algorithm_count": number,
  "has_classification": true|false,
  "has_visual_description": true|false,
  "has_reflection": true|false,
  "inappropriate_content": true|false,
  "passes_guardrails": true|false,
  "flag_for_human_review": true|false,
  "flag_reason": "string or null",
  "warnings": ["list of concerns, empty if none"]
}}

IMPORTANT: passes_guardrails is ALWAYS true — grading continues regardless of issues found.
Use warnings to surface concerns. flag_for_human_review if: algorithm_count < {MINIMUM_ALGORITHMS},
relevance is questionable, or possible integrity concern. Never set passes_guardrails to false.""",
            }
        ],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    result = json.loads(raw.strip())
    result["word_count"] = word_count
    return result

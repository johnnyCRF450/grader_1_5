"""
RAI Agent — Responsible AI review of the scoring output.
Checks for internal consistency, evidence quality, and potential grading bias.
Recommends score adjustments where fairness issues are detected.
"""

import json
import anthropic


def review(
    client: anthropic.Anthropic,
    scores: dict,
    submission_text: str,
    context: str,
) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=f"""You are a Responsible AI (RAI) auditor reviewing automated academic scoring for fairness,
consistency, and transparency. Your job is to catch grading errors before a student sees their grade.

Bias types to check for:
  • Style bias: penalizing informal writing style rather than content quality
  • Halo effect: one strong section inflating scores across unrelated criteria
  • Recency bias: over-weighting the last section read
  • Length bias: equating longer responses with higher quality regardless of content
  • Vocabulary bias: penalizing clear simple writing vs. unnecessarily complex jargon
  • Internal inconsistency: scores that contradict each other

{context}""",
        messages=[
            {
                "role": "user",
                "content": f"""Perform an RAI audit on these automated scores. Be concise — keep each text field under 100 words.

SCORES (summarized):
{json.dumps([{"criterion_id": s["criterion_id"], "level": s["level_awarded"], "points": s["points_awarded"], "confidence": s.get("confidence"), "evidence": s.get("evidence","")[:120]} for s in scores.get("scores",[])], indent=2)}

SUBMISSION EXCERPT (first 600 chars):
---
{submission_text[:600]}
---

Return ONLY valid JSON:
{{
  "consistency_check": "pass|warn|fail",
  "consistency_notes": "<explain any contradictions between criteria scores>",
  "bias_flags": [
    {{"bias_type": "<type>", "criterion_affected": "<id>", "description": "<what was flagged>"}}
  ],
  "evidence_quality": "strong|adequate|weak",
  "evidence_notes": "<assessment of whether scores are grounded in specific evidence>",
  "fairness_concerns": ["<list any fairness issues>"],
  "recommended_adjustments": [
    {{
      "criterion_id": "<id>",
      "current_level": "<level>",
      "current_points": <number>,
      "suggested_level": "<level>",
      "suggested_points": <number>,
      "reason": "<why the adjustment is warranted>"
    }}
  ],
  "rai_approved": true|false,
  "rai_summary": "<1-2 sentence overall RAI assessment>",
  "human_review_recommended": true|false,
  "human_review_reason": "<reason or null>"
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


def apply_adjustments(scores: dict, rai_report: dict) -> dict:
    """Apply RAI-recommended score adjustments and note them in the score record."""
    if not rai_report.get("recommended_adjustments"):
        return scores

    adjustments = {a["criterion_id"]: a for a in rai_report["recommended_adjustments"]}
    adjusted_scores = []
    for s in scores["scores"]:
        if s["criterion_id"] in adjustments:
            adj = adjustments[s["criterion_id"]]
            s = s.copy()
            s["original_level"] = s["level_awarded"]
            s["original_points"] = s["points_awarded"]
            s["level_awarded"] = adj["suggested_level"]
            s["points_awarded"] = adj["suggested_points"]
            s["rai_adjusted"] = True
            s["rai_adjustment_reason"] = adj["reason"]
        else:
            s = s.copy()
            s["rai_adjusted"] = False
        adjusted_scores.append(s)

    total = sum(s["points_awarded"] for s in adjusted_scores)
    return {**scores, "scores": adjusted_scores, "total_points": total}

"""
Feedback Agent — generates a motivational, personalized grade report.
Incorporates XAI transparency (explains score reasoning) and RAI notes.
"""

import anthropic


def generate(
    client: anthropic.Anthropic,
    submission_text: str,
    analysis: str,
    scores: dict,
    rai_report: dict,
    context: str,
) -> str:
    pct = round(scores["total_points"] / scores["total_possible"] * 100, 1)
    letter = _letter(pct)

    score_lines = "\n".join(
        f"  {s['criterion_name']}: {s['points_awarded']}/{s['max_points']} "
        f"({s['level_awarded']}, confidence={s.get('confidence', '?')})"
        + (f" [RAI-adjusted from {s.get('original_level','?')}]" if s.get("rai_adjusted") else "")
        for s in scores["scores"]
    )

    rai_note = ""
    if rai_report.get("recommended_adjustments"):
        rai_note = (
            f"\n\nRAI AUDIT NOTE: {len(rai_report['recommended_adjustments'])} score(s) were adjusted "
            f"after a fairness review. {rai_report.get('rai_summary', '')}"
        )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=f"""You are an encouraging, transparent academic instructor grading portfolio work.
Your feedback should:
  - Be warm, specific, and genuinely motivating
  - Reference specific elements from the student's work (not generic praise)
  - Explain the scoring in plain language (XAI transparency)
  - Give concrete, actionable suggestions for improvement
  - Acknowledge if any scores were adjusted for fairness (RAI transparency)
  - Be professional and appropriate for adult learners in a graduate/professional program
  - Use plain, approachable language — avoid academic jargon in the feedback itself

{context}""",
        messages=[
            {
                "role": "user",
                "content": f"""Write a grade report and motivational response.

SCORE BREAKDOWN:
{score_lines}
Total: {scores['total_points']}/{scores['total_possible']} ({pct}% — {letter})
{rai_note}

SUBMISSION ANALYSIS:
{analysis}

Structure your response as follows:
1. Opening (1-2 sentences acknowledging their portfolio work positively)
2. STRENGTHS (2-3 specific things done well, with references to their actual work)
3. AREAS FOR GROWTH (2-3 specific, actionable improvements with "how-to" guidance)
4. SCORE EXPLANATION (brief plain-language explanation of the key scoring decisions — XAI transparency)
5. FINAL GRADE: {scores['total_points']}/{scores['total_possible']} ({pct}% — {letter})
6. Closing motivational sentence tied to their career/portfolio goals

Keep the full response under 500 words. Write in second person ("you", "your work").
If any scores were RAI-adjusted, mention this briefly and positively.""",
            }
        ],
    )
    return response.content[0].text


def _letter(pct: float) -> str:
    if pct >= 93: return "A"
    if pct >= 90: return "A-"
    if pct >= 87: return "B+"
    if pct >= 83: return "B"
    if pct >= 80: return "B-"
    if pct >= 77: return "C+"
    if pct >= 73: return "C"
    if pct >= 70: return "C-"
    if pct >= 67: return "D+"
    if pct >= 60: return "D"
    return "F"

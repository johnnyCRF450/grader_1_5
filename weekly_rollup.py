"""
Weekly rollup generator — aggregates grades for a given ISO week and produces
a structured report with per-criterion statistics, common issues, and an
LLM-synthesized summary of class-wide patterns.
"""

from collections import Counter, defaultdict
from datetime import datetime

import anthropic

from grades_store import load_week, available_weeks
from rl_corrections import get_agreement_stats


def generate(week_str: str | None = None) -> str:
    if week_str is None:
        week_str = datetime.now().strftime("%Y-W%W")

    records = load_week(week_str)
    if not records:
        return f"No grades found for week {week_str}."

    client = anthropic.Anthropic()
    total_possible = records[0].get("total_possible", 75)

    # ── Summary stats ────────────────────────────────────────────────────────
    scores     = [r["total_points"] for r in records]
    avg_score  = sum(scores) / len(scores)
    avg_pct    = avg_score / total_possible * 100
    grade_dist = Counter(r.get("letter_grade", "?") for r in records)

    # ── Per-criterion aggregation ────────────────────────────────────────────
    criterion_data: dict[str, list] = defaultdict(list)
    all_counterfactuals: list[str]  = []

    for record in records:
        for cs in record.get("criteria_scores", []):
            criterion_data[cs["criterion_id"]].append(cs)
            if cs.get("counterfactual"):
                all_counterfactuals.append(
                    f"[{cs['criterion_name']}]: {cs['counterfactual']}"
                )

    # ── Common warnings ──────────────────────────────────────────────────────
    all_warnings: list[str] = []
    for record in records:
        all_warnings.extend(record.get("guardrail_warnings", []))
    warning_counts = Counter(all_warnings)

    # ── Flagged students ─────────────────────────────────────────────────────
    flagged = [r for r in records if r.get("flag_for_review")]

    # ── RL stats ─────────────────────────────────────────────────────────────
    rl = get_agreement_stats()

    # ── Build report ─────────────────────────────────────────────────────────
    lines = [
        f"WEEKLY GRADE ROLLUP — {week_str}",
        "=" * 52,
        f"Students graded : {len(records)}",
        f"Score range     : {min(scores)}–{max(scores)} / {total_possible}",
        f"Class average   : {avg_score:.1f} / {total_possible} ({avg_pct:.1f}%)",
        f"Grade distribution: {_fmt_dist(grade_dist)}",
        "",
        "PER-CRITERION BREAKDOWN",
        "─" * 52,
    ]

    for cid, entries in criterion_data.items():
        avg_pts    = sum(e["points"] for e in entries) / len(entries)
        max_pts    = entries[0]["max_points"]
        pct        = avg_pts / max_pts * 100
        level_dist = Counter(e["level"] for e in entries)
        top_level  = level_dist.most_common(1)[0][0]
        name       = entries[0]["criterion_name"]
        adj_count  = sum(1 for e in entries if e.get("rai_adjusted"))

        lines.append(
            f"\n{name}\n"
            f"  Avg: {avg_pts:.1f}/{max_pts} ({pct:.0f}%)  |  "
            f"Most common level: {top_level}\n"
            f"  Distribution: {_fmt_dist(level_dist)}"
            + (f"\n  ⚖ RAI-adjusted in {adj_count} submission(s)" if adj_count else "")
        )

    # ── Common issues ────────────────────────────────────────────────────────
    if warning_counts:
        lines += ["", "COMMON CLASS-WIDE ISSUES", "─" * 52]
        for warning, count in warning_counts.most_common(8):
            pct_students = count / len(records) * 100
            lines.append(f"  {count}/{len(records)} students ({pct_students:.0f}%) — {warning}")

    # ── Flagged students ─────────────────────────────────────────────────────
    if flagged:
        lines += ["", "STUDENTS FLAGGED FOR HUMAN REVIEW", "─" * 52]
        for r in flagged:
            lines.append(f"  • {r['student']}: {r.get('flag_reason','see guardrail report')}")

    # ── RL calibration metrics ───────────────────────────────────────────────
    if "agreement_rate_pct" in rl:
        lines += ["", "RL CALIBRATION METRICS", "─" * 52,
            f"  Total criteria graded : {rl['total_criteria_graded']}",
            f"  Instructor corrections: {rl['total_corrections']}",
            f"  AI agreement rate     : {rl['agreement_rate_pct']}%",
            f"  Correction rate       : {rl['correction_rate_pct']}%",
        ]
        if rl.get("most_corrected_criterion"):
            lines.append(f"  Most corrected criterion: {rl['most_corrected_criterion']}")
        if rl.get("by_criterion"):
            lines.append("  Per-criterion correction pattern:")
            for cid, info in rl["by_criterion"].items():
                lines.append(f"    {cid}: {info['corrections']} corrections — {info['direction']}")

    stats_text = "\n".join(lines)

    # ── LLM synthesis ────────────────────────────────────────────────────────
    if len(records) >= 2:
        synthesis = _llm_synthesis(client, records, stats_text, all_counterfactuals)
        stats_text += f"\n\nINSTRUCTOR SYNTHESIS & RECOMMENDATIONS\n{'─'*52}\n{synthesis}"

    return stats_text


def _llm_synthesis(
    client: anthropic.Anthropic,
    records: list[dict],
    stats_text: str,
    counterfactuals: list[str],
) -> str:
    sample_cf = "\n".join(counterfactuals[:25])
    rai_summaries = [r.get("rai_summary", "") for r in records if r.get("rai_summary")]
    sample_rai = "\n".join(rai_summaries[:8])

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=700,
        messages=[{
            "role": "user",
            "content": f"""You are an instructional analyst reviewing a week of student grades.
Based on the grade statistics, common score improvement suggestions, and RAI audit notes,
provide a concise instructor-facing synthesis.

GRADE STATISTICS:
{stats_text[:1200]}

COMMON IMPROVEMENT SUGGESTIONS (from XAI counterfactuals):
{sample_cf}

RAI AUDIT NOTES:
{sample_rai}

Write a structured synthesis (under 350 words) with these sections:
1. TOP 3 STRUGGLES — most common patterns where students fell short
2. INSTRUCTIONAL INTERVENTIONS — specific actions the instructor can take next class
3. STRENGTHS TO REINFORCE — what the class is doing well that should be acknowledged
4. RL NOTE — if there were instructor corrections this week, what do they suggest about AI calibration?

Be specific and actionable. Avoid generic advice.""",
        }],
    )
    return response.content[0].text


def _fmt_dist(counter: Counter) -> str:
    order = ["excellent", "competent", "needs_improvement", "inadequate",
             "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F"]
    ordered = [(k, counter[k]) for k in order if k in counter]
    rest    = [(k, v) for k, v in counter.items() if k not in order]
    return "  ".join(f"{k}:{v}" for k, v in ordered + rest)


if __name__ == "__main__":
    print(generate())

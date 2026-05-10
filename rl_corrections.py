"""
Reinforcement Learning from instructor corrections (in-context RLHF).

When an instructor overrides a criterion score, the correction is stored
with context. On future grading runs, recent corrections are injected into
the scorer's prompt as few-shot examples, teaching it the instructor's
grading style and calibration preferences.

The RL reward signal is implicit:
  - Correction = negative signal (AI was wrong)
  - No correction = positive signal (AI was right)
Agreement rate tracks model calibration over time.
"""

import json
from datetime import datetime
from pathlib import Path

CORRECTIONS_PATH = Path(__file__).parent / "corrections_store.json"
MAX_EXAMPLES_PER_CRITERION = 4   # few-shot examples injected per criterion


# ── Storage ──────────────────────────────────────────────────────────────────

def save_correction(
    student_label: str,
    criterion_id: str,
    criterion_name: str,
    original_level: str,
    original_points: int,
    corrected_level: str,
    corrected_points: int,
    instructor_reason: str,
    submission_excerpt: str = "",
) -> dict:
    corrections = _load()
    record = {
        "id":               len(corrections),
        "timestamp":        datetime.now().isoformat(),
        "student_label":    student_label,
        "criterion_id":     criterion_id,
        "criterion_name":   criterion_name,
        "original_level":   original_level,
        "original_points":  original_points,
        "corrected_level":  corrected_level,
        "corrected_points": corrected_points,
        "instructor_reason": instructor_reason,
        "submission_excerpt": submission_excerpt[:250],
        "direction": "up" if corrected_points > original_points else "down",
    }
    corrections.append(record)
    CORRECTIONS_PATH.write_text(json.dumps(corrections, indent=2))
    return record


def get_examples_for_criterion(criterion_id: str) -> list[dict]:
    """Return recent corrections for a criterion as few-shot examples."""
    relevant = [c for c in _load() if c["criterion_id"] == criterion_id]
    return relevant[-MAX_EXAMPLES_PER_CRITERION:]


def get_all_examples() -> list[dict]:
    """Return all corrections — used to build the full few-shot block."""
    return _load()


def format_few_shot_block(corrections: list[dict]) -> str:
    """Format corrections into a prompt-ready few-shot example block."""
    if not corrections:
        return ""
    lines = [
        "\n--- INSTRUCTOR CALIBRATION EXAMPLES ---",
        "These are past cases where the instructor corrected AI scores.",
        "Learn from these to align your scoring with instructor expectations:\n",
    ]
    for c in corrections:
        lines.append(
            f"Criterion: {c['criterion_name']}\n"
            f"  Submission excerpt: \"{c['submission_excerpt']}\"\n"
            f"  AI scored: {c['original_level']} ({c['original_points']} pts)\n"
            f"  Instructor corrected to: {c['corrected_level']} ({c['corrected_points']} pts)\n"
            f"  Instructor reasoning: {c['instructor_reason']}\n"
        )
    lines.append("--- END CALIBRATION EXAMPLES ---\n")
    return "\n".join(lines)


# ── Agreement rate (RL reward metric) ────────────────────────────────────────

def get_agreement_stats() -> dict:
    """
    Computes the RL reward signal.
    Agreement rate = fraction of AI criterion scores the instructor left unchanged.
    """
    from grades_store import load_all
    all_records = load_all()
    total_criteria = sum(len(r.get("criteria_scores", [])) for r in all_records)
    corrections = _load()
    n_corrections = len(corrections)

    if total_criteria == 0:
        return {"status": "no data yet"}

    agreement_rate = (total_criteria - n_corrections) / total_criteria

    # Per-criterion breakdown
    from collections import Counter
    by_criterion = Counter(c["criterion_id"] for c in corrections)
    criterion_counts = {k: {"corrections": v, "direction": _net_direction(k, corrections)}
                        for k, v in by_criterion.items()}

    return {
        "total_criteria_graded":   total_criteria,
        "total_corrections":       n_corrections,
        "agreement_rate_pct":      round(agreement_rate * 100, 1),
        "correction_rate_pct":     round((1 - agreement_rate) * 100, 1),
        "by_criterion":            criterion_counts,
        "most_corrected_criterion": by_criterion.most_common(1)[0][0] if by_criterion else None,
    }


def _net_direction(criterion_id: str, corrections: list[dict]) -> str:
    relevant = [c for c in corrections if c["criterion_id"] == criterion_id]
    ups   = sum(1 for c in relevant if c["direction"] == "up")
    downs = sum(1 for c in relevant if c["direction"] == "down")
    if ups > downs:   return f"AI scores too low ({ups} bumped up)"
    if downs > ups:   return f"AI scores too high ({downs} bumped down)"
    return "mixed"


def _load() -> list[dict]:
    if not CORRECTIONS_PATH.exists():
        return []
    try:
        return json.loads(CORRECTIONS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return []

"""
Grades store — persists full grade records as JSON Lines for rollup analysis.
Also writes the human-readable CSV for quick spreadsheet access.
"""

import csv
import json
from datetime import datetime
from pathlib import Path

STORE_PATH = Path(__file__).parent / "grades_store.jsonl"
CSV_PATH   = Path(__file__).parent / "grades_log.csv"

_CSV_HEADER = [
    "timestamp", "week", "student", "format", "images_analyzed",
    "total_points", "total_possible", "percentage", "letter_grade",
    "overall_confidence", "rai_approved", "guardrail_warnings", "feedback",
]


def _ensure_csv():
    if not CSV_PATH.exists():
        with open(CSV_PATH, "w", newline="") as f:
            csv.writer(f).writerow(_CSV_HEADER)


def save(report) -> dict:
    """Persist a GradeReport to both JSONL store and CSV. Returns the stored record."""
    now = datetime.now()
    week = now.strftime("%Y-W%W")

    record = {
        "timestamp": now.isoformat(),
        "week": week,
        **report.to_dict(),
        "criteria_scores": [
            {
                "criterion_id":   s["criterion_id"],
                "criterion_name": s["criterion_name"],
                "level":          s["level_awarded"],
                "points":         s["points_awarded"],
                "max_points":     s["max_points"],
                "confidence":     s.get("confidence"),
                "evidence":       s.get("evidence", ""),
                "counterfactual": s.get("counterfactual", ""),
                "rai_adjusted":   s.get("rai_adjusted", False),
            }
            for s in report.scores.get("scores", [])
        ],
        "guardrail_warnings": report.guardrail_report.get("warnings", []),
        "flag_for_review":    report.guardrail_report.get("flag_for_human_review", False),
        "analysis_excerpt":   report.analysis[:600] if report.analysis else "",
        "rai_summary":        report.rai_report.get("rai_summary", ""),
    }

    # JSONL store
    with open(STORE_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")

    # CSV
    _ensure_csv()
    with open(CSV_PATH, "a", newline="") as f:
        csv.writer(f).writerow([
            record["timestamp"], week,
            record["student"], record.get("document_format", "?"),
            record.get("images_analyzed", 0),
            record["total_points"], record["total_possible"],
            record["percentage"], record["letter_grade"],
            record.get("overall_confidence", ""),
            record.get("rai_approved", ""),
            "; ".join(record["guardrail_warnings"]),
            record["feedback"][:300].replace("\n", " "),
        ])

    return record


def load_week(week_str: str | None = None) -> list[dict]:
    """Return all records for the given ISO week (default = current week)."""
    if week_str is None:
        week_str = datetime.now().strftime("%Y-W%W")
    return [r for r in _iter_store() if r.get("week") == week_str]


def load_all() -> list[dict]:
    return list(_iter_store())


def available_weeks() -> list[str]:
    weeks = sorted({r.get("week", "") for r in _iter_store() if r.get("week")}, reverse=True)
    return weeks or [datetime.now().strftime("%Y-W%W")]


def _iter_store():
    if not STORE_PATH.exists():
        return
    with open(STORE_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

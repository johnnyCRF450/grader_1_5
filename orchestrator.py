"""
Orchestrator — coordinates the 7-agent grading pipeline for Assignment 1.5.

Pipeline order:
  Privacy Agent → Guardrail Agent → Context Agent → Analyzer Agent
  → Scorer Agent → RAI Agent → Feedback Agent
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from agents.context_agent import build_context, get_rubric
from agents.privacy_agent import scrub
from agents.guardrail_agent import validate
from agents.analyzer_agent import analyze, load_image
from agents.scorer_agent import score
from agents.rai_agent import review, apply_adjustments
from agents.feedback_agent import generate, _letter

RUBRIC_PATH = Path(__file__).parent / "rubric.json"


@dataclass
class GradeReport:
    student_label: str
    privacy_report: dict
    guardrail_report: dict
    analysis: str
    scores: dict
    rai_report: dict
    feedback: str
    halted: bool = False
    halt_reason: str = ""

    @property
    def total_points(self) -> int:
        return self.scores.get("total_points", 0)

    @property
    def total_possible(self) -> int:
        return self.scores.get("total_possible", 75)

    @property
    def percentage(self) -> float:
        return round(self.total_points / self.total_possible * 100, 1) if self.total_possible else 0.0

    @property
    def letter_grade(self) -> str:
        return _letter(self.percentage)

    def summary(self) -> str:
        if self.halted:
            return f"GRADING HALTED for {self.student_label}: {self.halt_reason}"

        lines = [
            f"Student: {self.student_label}",
            f"Grade: {self.total_points}/{self.total_possible} ({self.percentage}% — {self.letter_grade})",
            f"Overall confidence: {self.scores.get('overall_confidence', '?')}",
            f"RAI approved: {self.rai_report.get('rai_approved', '?')}",
            "",
            "Score Breakdown:",
        ]
        for s in self.scores.get("scores", []):
            adj = " [RAI-adjusted]" if s.get("rai_adjusted") else ""
            lines.append(
                f"  {s['criterion_name']}: {s['points_awarded']}/{s['max_points']} "
                f"({s['level_awarded']}, conf={s.get('confidence','?')}){adj}"
            )
        lines += [
            "",
            f"Privacy: {self.privacy_report.get('privacy_report', 'N/A')}",
            f"Guardrails: {'PASSED' if self.guardrail_report.get('passes_guardrails') else 'FAILED'}",
            "",
            "--- FEEDBACK ---",
            self.feedback,
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "student": self.student_label,
            "total_points": self.total_points,
            "total_possible": self.total_possible,
            "percentage": self.percentage,
            "letter_grade": self.letter_grade,
            "overall_confidence": self.scores.get("overall_confidence"),
            "rai_approved": self.rai_report.get("rai_approved"),
            "score_breakdown": self.scores.get("scores", []),
            "privacy_report": self.privacy_report.get("privacy_report"),
            "guardrail_warnings": self.guardrail_report.get("warnings", []),
            "feedback": self.feedback,
            "halted": self.halted,
            "halt_reason": self.halt_reason,
        }


def grade(
    submission_text: str,
    student_label: str = "Student",
    image_path: str | None = None,
) -> GradeReport:
    client = anthropic.Anthropic()
    rubric = get_rubric(RUBRIC_PATH)

    print(f"[1/7] Privacy scrub...")
    privacy = scrub(client, submission_text)
    clean_text = privacy["scrubbed_text"]

    print(f"[2/7] Building context...")
    context = build_context(RUBRIC_PATH)

    print(f"[3/7] Guardrail validation...")
    guardrails = validate(client, clean_text, context)

    if not guardrails.get("passes_guardrails", True):
        reason = (
            f"Submission did not pass guardrails. "
            f"Reason: {guardrails.get('flag_reason') or ', '.join(guardrails.get('warnings', ['unknown']))}"
        )
        print(f"  ⚠ HALTED — {reason}")
        return GradeReport(
            student_label=student_label,
            privacy_report=privacy,
            guardrail_report=guardrails,
            analysis="",
            scores={"total_points": 0, "total_possible": rubric["total_points"], "scores": []},
            rai_report={},
            feedback="",
            halted=True,
            halt_reason=reason,
        )

    print(f"[4/7] Analyzing submission...")
    image_b64 = load_image(image_path) if image_path else None
    analysis = analyze(client, clean_text, context, image_b64)

    print(f"[5/7] Scoring with XAI...")
    scores = score(client, analysis, clean_text, context, rubric)

    print(f"[6/7] RAI review...")
    rai = review(client, scores, clean_text, context)
    scores = apply_adjustments(scores, rai)

    print(f"[7/7] Generating feedback...")
    feedback = generate(client, clean_text, analysis, scores, rai, context)

    print(f"    Done — {scores['total_points']}/{scores['total_possible']}")
    return GradeReport(
        student_label=student_label,
        privacy_report=privacy,
        guardrail_report=guardrails,
        analysis=analysis,
        scores=scores,
        rai_report=rai,
        feedback=feedback,
    )

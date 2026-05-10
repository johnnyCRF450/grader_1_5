"""
Orchestrator — coordinates the 7-agent grading pipeline for Assignment 1.5.

Pipeline order:
  Document Loader → Privacy Agent → Guardrail Agent → Context Agent
  → Analyzer Agent → Scorer Agent → RAI Agent → Feedback Agent

Guardrails are advisory only — grading always runs to completion.
"""

from dataclasses import dataclass
from pathlib import Path

import anthropic

from document_loader import load as load_document
from agents.context_agent import build_context, get_rubric
from agents.privacy_agent import scrub
from agents.guardrail_agent import validate
from agents.analyzer_agent import analyze
from agents.scorer_agent import score
from agents.rai_agent import review, apply_adjustments
from agents.feedback_agent import generate, _letter
from grades_store import save as save_grade
from rl_corrections import get_all_examples, format_few_shot_block

RUBRIC_PATH = Path(__file__).parent / "rubric.json"


@dataclass
class GradeReport:
    student_label: str
    document_info: dict
    privacy_report: dict
    guardrail_report: dict
    analysis: str
    scores: dict
    rai_report: dict
    feedback: str

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
        guard = self.guardrail_report
        warnings = guard.get("warnings", [])
        flag = guard.get("flag_for_human_review", False)

        lines = [
            f"Student: {self.student_label}",
            f"Document: {self.document_info.get('format','?').upper()} | "
            f"{self.document_info.get('page_count','?')} pages | "
            f"{self.document_info.get('image_count', 0)} image(s) extracted",
            f"Grade: {self.total_points}/{self.total_possible} ({self.percentage}% — {self.letter_grade})",
            f"Overall confidence: {self.scores.get('overall_confidence', '?')}",
            f"RAI approved: {self.rai_report.get('rai_approved', '?')}",
        ]
        if warnings:
            lines.append(f"⚠ Guardrail warnings: {'; '.join(warnings)}")
        if flag:
            lines.append(f"🚩 Flagged for human review: {guard.get('flag_reason', '')}")
        lines += ["", "Score Breakdown:"]
        for s in self.scores.get("scores", []):
            adj = " [RAI-adjusted]" if s.get("rai_adjusted") else ""
            lines.append(
                f"  {s['criterion_name']}: {s['points_awarded']}/{s['max_points']} "
                f"({s['level_awarded']}, conf={s.get('confidence','?')}){adj}"
            )
        lines += [
            "",
            f"Privacy: {self.privacy_report.get('privacy_report', 'N/A')}",
            "",
            "--- FEEDBACK ---",
            self.feedback,
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "student": self.student_label,
            "document_format": self.document_info.get("format"),
            "images_analyzed": self.document_info.get("image_count", 0),
            "total_points": self.total_points,
            "total_possible": self.total_possible,
            "percentage": self.percentage,
            "letter_grade": self.letter_grade,
            "overall_confidence": self.scores.get("overall_confidence"),
            "rai_approved": self.rai_report.get("rai_approved"),
            "score_breakdown": self.scores.get("scores", []),
            "guardrail_warnings": self.guardrail_report.get("warnings", []),
            "flag_for_review": self.guardrail_report.get("flag_for_human_review", False),
            "feedback": self.feedback,
        }


def grade(
    document_path: str | None = None,
    submission_text: str = "",
    student_label: str = "Student",
) -> GradeReport:
    """
    Grade a submission from a document file (PDF/DOCX/image) and/or pasted text.
    If document_path is provided, text and images are extracted from the file.
    submission_text can supplement or replace document content.
    Grading always runs to completion — guardrails are advisory only.
    """
    client = anthropic.Anthropic()
    rubric = get_rubric(RUBRIC_PATH)

    # ── Document loading ────────────────────────────────────────────────────
    doc_info = {"text": "", "images": [], "image_count": 0, "page_count": None, "format": "text"}
    if document_path:
        print(f"[0/7] Loading document: {Path(document_path).name}...")
        doc_info = load_document(document_path)
        print(f"       Extracted {len(doc_info['text'].split())} words, "
              f"{doc_info['image_count']} image(s) from {doc_info['format'].upper()}")

    # Merge document text with any additional pasted text
    combined_text = "\n\n".join(
        t for t in [doc_info["text"], submission_text] if t.strip()
    )
    images = doc_info.get("images", [])

    # ── Privacy scrub ───────────────────────────────────────────────────────
    print(f"[1/7] Privacy scrub...")
    privacy = scrub(client, combined_text)
    clean_text = privacy["scrubbed_text"]

    # ── Context ─────────────────────────────────────────────────────────────
    print(f"[2/7] Building context...")
    context = build_context(RUBRIC_PATH)

    # ── Guardrails (advisory — never halts) ─────────────────────────────────
    print(f"[3/7] Guardrail check (advisory)...")
    guardrails = validate(client, clean_text, context)
    warnings = guardrails.get("warnings", [])
    if warnings:
        print(f"       ⚠ Warnings (grading continues): {'; '.join(warnings)}")
    if guardrails.get("flag_for_human_review"):
        print(f"       🚩 Flagged for human review: {guardrails.get('flag_reason')}")

    # ── Analysis — multimodal (text + all embedded images) ──────────────────
    print(f"[4/7] Analyzing submission ({len(images)} image(s))...")
    analysis = analyze(client, clean_text, context, images)

    # ── XAI Scoring (with RL calibration examples) ──────────────────────────
    print(f"[5/7] Scoring with XAI...")
    rl_examples = format_few_shot_block(get_all_examples())
    if rl_examples:
        print(f"       RL: {len(get_all_examples())} instructor correction(s) injected")
    scores = score(client, analysis, clean_text, context, rubric, rl_examples)

    # ── RAI Audit ───────────────────────────────────────────────────────────
    print(f"[6/7] RAI fairness audit...")
    rai = review(client, scores, clean_text, context)
    scores = apply_adjustments(scores, rai)

    # ── Feedback ────────────────────────────────────────────────────────────
    print(f"[7/7] Generating feedback...")
    feedback = generate(client, clean_text, analysis, scores, rai, context)

    print(f"    ✓ Complete — {scores['total_points']}/{scores['total_possible']} ({_letter(scores['total_points']/scores['total_possible']*100)})")
    report = GradeReport(
        student_label=student_label,
        document_info=doc_info,
        privacy_report=privacy,
        guardrail_report=guardrails,
        analysis=analysis,
        scores=scores,
        rai_report=rai,
        feedback=feedback,
    )
    save_grade(report)

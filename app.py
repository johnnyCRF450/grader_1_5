"""
Gradio web UI — multi-tab interface for Assignment 1.5 grader.
Tabs: Submit | Privacy & Guardrails | XAI Scores | RAI Audit | Feedback | History
"""

import csv
import json
from datetime import datetime
from pathlib import Path

import gradio as gr

from orchestrator import grade

LOG_PATH = Path(__file__).parent / "grades_log.csv"


def _ensure_log():
    if not LOG_PATH.exists():
        with open(LOG_PATH, "w", newline="") as f:
            csv.writer(f).writerow([
                "timestamp", "student", "total_points", "total_possible",
                "percentage", "letter_grade", "overall_confidence",
                "rai_approved", "pii_found", "guardrail_warnings", "feedback"
            ])


def run_grader(submission_text, student_name, image_path):
    if not submission_text.strip():
        empty = "Please paste a submission first."
        return empty, empty, empty, empty, empty

    label = student_name.strip() or "Student"
    img = image_path if image_path else None

    try:
        report = grade(submission_text, student_label=label, image_path=img)
    except Exception as e:
        err = f"Error: {e}"
        return err, err, err, err, err

    # ── Privacy & Guardrail tab ─────────────────────────────────────────────
    priv = report.privacy_report
    guard = report.guardrail_report
    privacy_text = (
        f"Privacy Scrub Report\n{'─'*40}\n"
        f"{priv.get('privacy_report', 'N/A')}\n\n"
        f"PII found: {priv.get('pii_found', False)}\n"
        f"Regex detections: {len(priv.get('regex_detections', []))}\n"
        f"LLM detections: {', '.join(priv.get('llm_detections', [])) or 'none'}\n\n"
        f"Guardrail Results\n{'─'*40}\n"
        f"Status: {'✅ PASSED' if guard.get('passes_guardrails') else '❌ FAILED — grading halted'}\n"
        f"Word count: {guard.get('word_count', '?')}\n"
        f"Algorithms found: {guard.get('algorithm_count', '?')} (min 8 required)\n"
        f"Has classification: {guard.get('has_classification', '?')}\n"
        f"Has reflection: {guard.get('has_reflection', '?')}\n"
        f"Flag for human review: {guard.get('flag_for_human_review', False)}\n"
        f"Flag reason: {guard.get('flag_reason') or 'none'}\n"
        f"Warnings: {', '.join(guard.get('warnings', [])) or 'none'}"
    )

    if report.halted:
        halted_msg = f"GRADING HALTED\n\n{report.halt_reason}"
        return privacy_text, halted_msg, halted_msg, halted_msg, halted_msg

    # ── XAI Scores tab ──────────────────────────────────────────────────────
    xai_lines = [
        f"XAI Score Breakdown\n{'─'*40}",
        f"Total: {report.total_points}/{report.total_possible} ({report.percentage}% — {report.letter_grade})",
        f"Overall confidence: {report.scores.get('overall_confidence', '?'):.2f}",
        "",
    ]
    for s in report.scores.get("scores", []):
        adj = f"\n  ⚖ RAI-adjusted from {s.get('original_level','?')} ({s.get('original_points','?')} pts): {s.get('rai_adjustment_reason','')}" if s.get("rai_adjusted") else ""
        xai_lines.append(
            f"{s['criterion_name']}: {s['points_awarded']}/{s['max_points']} — {s['level_awarded'].upper()} (confidence: {s.get('confidence', '?')})\n"
            f"  Evidence: {s.get('evidence', 'N/A')}\n"
            f"  Rationale: {s.get('rationale', 'N/A')}\n"
            f"  To score higher: {s.get('counterfactual', 'N/A')}"
            + (f"\n  Uncertainty: {s['uncertainty_notes']}" if s.get("uncertainty_notes") else "")
            + adj
            + "\n"
        )
    xai_text = "\n".join(xai_lines)

    # ── RAI Audit tab ───────────────────────────────────────────────────────
    rai = report.rai_report
    rai_lines = [
        f"RAI Audit Report\n{'─'*40}",
        f"RAI Approved: {'✅ Yes' if rai.get('rai_approved') else '⚠ No'}",
        f"Consistency: {rai.get('consistency_check', '?').upper()}",
        f"Evidence quality: {rai.get('evidence_quality', '?').upper()}",
        f"Human review recommended: {rai.get('human_review_recommended', False)}",
        f"Human review reason: {rai.get('human_review_reason') or 'N/A'}",
        "",
        f"Summary: {rai.get('rai_summary', 'N/A')}",
        "",
        f"Consistency notes: {rai.get('consistency_notes', 'N/A')}",
        "",
        "Bias flags:",
    ]
    for flag in rai.get("bias_flags", []) or []:
        rai_lines.append(f"  • [{flag.get('bias_type','?')}] {flag.get('criterion_affected','?')}: {flag.get('description','?')}")
    if not (rai.get("bias_flags") or []):
        rai_lines.append("  None detected")
    rai_lines += ["", "Fairness concerns:"]
    for concern in rai.get("fairness_concerns", []) or []:
        rai_lines.append(f"  • {concern}")
    if not (rai.get("fairness_concerns") or []):
        rai_lines.append("  None detected")
    rai_lines += ["", "Score adjustments:"]
    for adj in rai.get("recommended_adjustments", []) or []:
        rai_lines.append(f"  • {adj.get('criterion_id')}: {adj.get('current_level')} → {adj.get('suggested_level')} ({adj.get('reason')})")
    if not (rai.get("recommended_adjustments") or []):
        rai_lines.append("  None recommended")
    rai_text = "\n".join(rai_lines)

    # ── Log ─────────────────────────────────────────────────────────────────
    _ensure_log()
    with open(LOG_PATH, "a", newline="") as f:
        csv.writer(f).writerow([
            datetime.now().isoformat(), label,
            report.total_points, report.total_possible,
            report.percentage, report.letter_grade,
            report.scores.get("overall_confidence", ""),
            rai.get("rai_approved", ""),
            priv.get("pii_found", False),
            "; ".join(guard.get("warnings", [])),
            report.feedback.replace("\n", " "),
        ])

    return privacy_text, xai_text, rai_text, report.feedback


def load_history():
    if not LOG_PATH.exists():
        return "No grades logged yet."
    rows = LOG_PATH.read_text()
    return rows


with gr.Blocks(title="Assignment 1.5 Grader — ML Visual Framework") as demo:
    gr.Markdown("## Assignment 1.5 — ML Algorithm Visual Framework Grader")
    gr.Markdown(
        "Paste student submission text and optionally upload their infographic. "
        "The system runs privacy scrubbing, guardrail validation, XAI scoring, "
        "and an RAI fairness audit before generating feedback."
    )

    with gr.Row():
        student_name = gr.Textbox(label="Student Name / ID", placeholder="e.g. Jane Smith")

    with gr.Row():
        submission = gr.Textbox(
            label="Student Submission (paste full text — reflection, descriptions, classification rationale)",
            lines=15,
            placeholder="Paste the student's written submission here...",
        )
        image_input = gr.Image(
            label="Infographic / Visual Framework (optional — upload image for vision analysis)",
            type="filepath",
        )

    grade_btn = gr.Button("Grade Submission", variant="primary", size="lg")

    with gr.Tabs():
        with gr.Tab("Privacy & Guardrails"):
            privacy_out = gr.Textbox(label="Privacy & Guardrail Report", lines=18, interactive=False)
        with gr.Tab("XAI Score Breakdown"):
            xai_out = gr.Textbox(label="Scores with Evidence, Confidence & Counterfactuals", lines=28, interactive=False)
        with gr.Tab("RAI Audit"):
            rai_out = gr.Textbox(label="Responsible AI Fairness Audit", lines=20, interactive=False)
        with gr.Tab("Feedback"):
            feedback_out = gr.Textbox(label="Motivational Grade Report", lines=20, interactive=False)
        with gr.Tab("Grade History"):
            history_btn = gr.Button("Refresh History")
            history_out = gr.Textbox(label="grades_log.csv", lines=15, interactive=False)
            history_btn.click(fn=load_history, outputs=history_out)

    grade_btn.click(
        fn=run_grader,
        inputs=[submission, student_name, image_input],
        outputs=[privacy_out, xai_out, rai_out, feedback_out],
    )

    gr.Markdown("*Grades auto-logged to `grades_log.csv` (gitignored). PII scrubbed before any API call.*")


if __name__ == "__main__":
    demo.launch()

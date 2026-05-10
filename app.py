"""
Gradio web UI — single document upload (PDF/DOCX/image) with multimodal grading.
Tabs: Submit | Privacy & Guardrails | XAI Scores | RAI Audit | Feedback | History
"""

import csv
from datetime import datetime
from pathlib import Path

import gradio as gr

from orchestrator import grade

LOG_PATH = Path(__file__).parent / "grades_log.csv"


def _ensure_log():
    if not LOG_PATH.exists():
        with open(LOG_PATH, "w", newline="") as f:
            csv.writer(f).writerow([
                "timestamp", "student", "format", "images_analyzed",
                "total_points", "total_possible", "percentage", "letter_grade",
                "overall_confidence", "rai_approved", "guardrail_warnings", "feedback"
            ])


def run_grader(document_file, student_name, extra_text):
    if document_file is None and not extra_text.strip():
        msg = "Upload a document or paste submission text (or both)."
        return msg, msg, msg, msg

    label = student_name.strip() or "Student"

    try:
        report = grade(
            document_path=document_file,
            submission_text=extra_text,
            student_label=label,
        )
    except Exception as e:
        err = f"Error during grading: {e}"
        return err, err, err, err

    doc = report.document_info
    guard = report.guardrail_report
    priv = report.privacy_report
    rai = report.rai_report

    # ── Privacy & Guardrail tab ─────────────────────────────────────────────
    privacy_text = (
        f"Document Info\n{'─'*40}\n"
        f"Format: {doc.get('format','?').upper()}\n"
        f"Pages: {doc.get('page_count','N/A')}\n"
        f"Images extracted: {doc.get('image_count', 0)} (all sent for visual analysis)\n\n"
        f"Privacy Scrub\n{'─'*40}\n"
        f"{priv.get('privacy_report', 'N/A')}\n"
        f"PII found: {priv.get('pii_found', False)}\n"
        f"Regex detections: {len(priv.get('regex_detections', []))}\n"
        f"LLM detections: {', '.join(priv.get('llm_detections', [])) or 'none'}\n\n"
        f"Guardrail Check (advisory — grading always completes)\n{'─'*40}\n"
        f"Algorithms found: {guard.get('algorithm_count', '?')} (min 8 required)\n"
        f"Has classification: {guard.get('has_classification', '?')}\n"
        f"Has reflection: {guard.get('has_reflection', '?')}\n"
        f"Word count: {guard.get('word_count', '?')}\n"
        f"Flagged for human review: {guard.get('flag_for_human_review', False)}\n"
        f"Flag reason: {guard.get('flag_reason') or 'none'}\n"
        f"Warnings: {', '.join(guard.get('warnings', [])) or 'none'}"
    )

    # ── XAI Scores tab ──────────────────────────────────────────────────────
    xai_lines = [
        f"XAI Score Breakdown\n{'─'*40}",
        f"Total: {report.total_points}/{report.total_possible} "
        f"({report.percentage}% — {report.letter_grade})",
        f"Overall confidence: {report.scores.get('overall_confidence', '?')}",
        "",
    ]
    for s in report.scores.get("scores", []):
        adj = (
            f"\n  ⚖ RAI-adjusted: {s.get('original_level','?')} → {s['level_awarded']} "
            f"| Reason: {s.get('rai_adjustment_reason','')}"
            if s.get("rai_adjusted") else ""
        )
        uncertainty = f"\n  Uncertainty: {s['uncertainty_notes']}" if s.get("uncertainty_notes") else ""
        xai_lines.append(
            f"{s['criterion_name']}: {s['points_awarded']}/{s['max_points']} "
            f"— {s['level_awarded'].upper()} (confidence: {s.get('confidence', '?')})\n"
            f"  Evidence: {s.get('evidence', 'N/A')}\n"
            f"  Rationale: {s.get('rationale', 'N/A')}\n"
            f"  To score higher: {s.get('counterfactual', 'N/A')}"
            + uncertainty + adj + "\n"
        )
    xai_text = "\n".join(xai_lines)

    # ── RAI Audit tab ───────────────────────────────────────────────────────
    rai_lines = [
        f"RAI Audit Report\n{'─'*40}",
        f"RAI Approved: {'✅ Yes' if rai.get('rai_approved') else '⚠ No'}",
        f"Consistency: {rai.get('consistency_check', '?').upper()}",
        f"Evidence quality: {rai.get('evidence_quality', '?').upper()}",
        f"Human review recommended: {rai.get('human_review_recommended', False)}",
        f"Human review reason: {rai.get('human_review_reason') or 'N/A'}",
        "",
        f"Summary: {rai.get('rai_summary', 'N/A')}",
        f"Consistency notes: {rai.get('consistency_notes', 'N/A')}",
        "",
        "Bias flags:",
    ]
    for flag in rai.get("bias_flags") or []:
        rai_lines.append(f"  • [{flag.get('bias_type','?')}] {flag.get('criterion_affected','?')}: {flag.get('description','?')}")
    if not (rai.get("bias_flags") or []):
        rai_lines.append("  None detected")
    rai_lines += ["", "Score adjustments made:"]
    for adj in rai.get("recommended_adjustments") or []:
        rai_lines.append(f"  • {adj.get('criterion_id')}: {adj.get('current_level')} → {adj.get('suggested_level')} ({adj.get('reason')})")
    if not (rai.get("recommended_adjustments") or []):
        rai_lines.append("  None")
    rai_text = "\n".join(rai_lines)

    # ── Log ─────────────────────────────────────────────────────────────────
    _ensure_log()
    with open(LOG_PATH, "a", newline="") as f:
        csv.writer(f).writerow([
            datetime.now().isoformat(), label,
            doc.get("format", "?"), doc.get("image_count", 0),
            report.total_points, report.total_possible,
            report.percentage, report.letter_grade,
            report.scores.get("overall_confidence", ""),
            rai.get("rai_approved", ""),
            "; ".join(guard.get("warnings", [])),
            report.feedback.replace("\n", " "),
        ])

    return privacy_text, xai_text, rai_text, report.feedback


def load_history():
    return LOG_PATH.read_text() if LOG_PATH.exists() else "No grades logged yet."


with gr.Blocks(title="Assignment 1.5 Grader") as demo:
    gr.Markdown("## Assignment 1.5 — ML Visual Framework Grader")
    gr.Markdown(
        "Upload a **PDF, DOCX, or image file** containing the student's submission. "
        "Text and all embedded images are automatically extracted and analyzed together. "
        "Optionally paste additional text below. Grading always runs to completion."
    )

    with gr.Row():
        student_name = gr.Textbox(
            label="Student Name / ID",
            placeholder="e.g. Jane Smith",
            scale=1,
        )

    with gr.Row():
        document_file = gr.File(
            label="Upload Submission (PDF, DOCX, PNG, JPG)",
            file_types=[".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg"],
            scale=2,
        )
        extra_text = gr.Textbox(
            label="Additional Text (optional — supplements document content)",
            lines=8,
            placeholder="Paste any text not captured in the document...",
            scale=2,
        )

    grade_btn = gr.Button("Grade Submission", variant="primary", size="lg")

    with gr.Tabs():
        with gr.Tab("📋 Privacy & Guardrails"):
            privacy_out = gr.Textbox(lines=20, interactive=False, show_label=False)
        with gr.Tab("⚖️ XAI Score Breakdown"):
            xai_out = gr.Textbox(lines=30, interactive=False, show_label=False)
        with gr.Tab("🧭 RAI Audit"):
            rai_out = gr.Textbox(lines=22, interactive=False, show_label=False)
        with gr.Tab("💬 Feedback"):
            feedback_out = gr.Textbox(lines=24, interactive=False, show_label=False)
        with gr.Tab("📊 Grade History"):
            history_btn = gr.Button("Refresh")
            history_out = gr.Textbox(lines=12, interactive=False, show_label=False)
            history_btn.click(fn=load_history, outputs=history_out)

    grade_btn.click(
        fn=run_grader,
        inputs=[document_file, student_name, extra_text],
        outputs=[privacy_out, xai_out, rai_out, feedback_out],
    )

    gr.Markdown(
        "*Grades auto-logged to `grades_log.csv` (gitignored). "
        "PII is scrubbed before any content reaches the API. "
        "Guardrails flag issues but never stop grading.*"
    )


if __name__ == "__main__":
    demo.launch()

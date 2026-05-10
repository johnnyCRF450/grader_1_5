"""
Gradio web UI — single document upload with multimodal grading.
Tabs: Submit | Privacy & Guardrails | XAI Scores | RAI Audit | Feedback
      | Corrections (RL) | Weekly Report
"""

from datetime import datetime
from pathlib import Path

import gradio as gr

from orchestrator import grade
from rl_corrections import save_correction, get_agreement_stats, _load as load_corrections
from weekly_rollup import generate as generate_rollup
from grades_store import available_weeks

# ── Grading ──────────────────────────────────────────────────────────────────

def run_grader(document_file, student_name, extra_text):
    if document_file is None and not extra_text.strip():
        msg = "Upload a document or paste submission text (or both)."
        return msg, msg, msg, msg, [], "{}"

    label = student_name.strip() or "Student"

    try:
        report = grade(document_path=document_file, submission_text=extra_text, student_label=label)
    except Exception as e:
        err = f"Error during grading: {e}"
        return err, err, err, err, [], "{}"

    doc   = report.document_info
    guard = report.guardrail_report
    priv  = report.privacy_report
    rai   = report.rai_report

    # ── Privacy & Guardrail tab ─────────────────────────────────────────────
    privacy_text = (
        f"Document Info\n{'─'*40}\n"
        f"Format : {doc.get('format','?').upper()}\n"
        f"Pages  : {doc.get('page_count','N/A')}\n"
        f"Images : {doc.get('image_count', 0)} extracted and analyzed\n\n"
        f"Privacy Scrub\n{'─'*40}\n"
        f"{priv.get('privacy_report', 'N/A')}\n"
        f"PII found      : {priv.get('pii_found', False)}\n"
        f"Regex hits     : {len(priv.get('regex_detections', []))}\n"
        f"LLM detections : {', '.join(priv.get('llm_detections', [])) or 'none'}\n\n"
        f"Guardrail Check (advisory — grading always completes)\n{'─'*40}\n"
        f"Algorithms found       : {guard.get('algorithm_count', '?')} (min 8)\n"
        f"Has classification     : {guard.get('has_classification', '?')}\n"
        f"Has reflection         : {guard.get('has_reflection', '?')}\n"
        f"Word count             : {guard.get('word_count', '?')}\n"
        f"Flag for human review  : {guard.get('flag_for_human_review', False)}\n"
        f"Flag reason            : {guard.get('flag_reason') or 'none'}\n"
        f"Warnings               : {', '.join(guard.get('warnings', [])) or 'none'}"
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
            f"\n  ⚖ RAI-adjusted: {s.get('original_level','?')} → {s['level_awarded']}"
            f" | {s.get('rai_adjustment_reason','')}"
            if s.get("rai_adjusted") else ""
        )
        uncertainty = f"\n  Uncertainty: {s['uncertainty_notes']}" if s.get("uncertainty_notes") else ""
        xai_lines.append(
            f"{s['criterion_name']}: {s['points_awarded']}/{s['max_points']} "
            f"— {s['level_awarded'].upper()} (conf: {s.get('confidence','?')})\n"
            f"  Evidence : {s.get('evidence','N/A')}\n"
            f"  Rationale: {s.get('rationale','N/A')}\n"
            f"  To improve: {s.get('counterfactual','N/A')}"
            + uncertainty + adj + "\n"
        )
    xai_text = "\n".join(xai_lines)

    # ── RAI Audit tab ───────────────────────────────────────────────────────
    rai_lines = [
        f"RAI Audit Report\n{'─'*40}",
        f"RAI Approved : {'✅ Yes' if rai.get('rai_approved') else '⚠ No'}",
        f"Consistency  : {rai.get('consistency_check','?').upper()}",
        f"Evidence     : {rai.get('evidence_quality','?').upper()}",
        f"Human review : {rai.get('human_review_recommended', False)}",
        f"Reason       : {rai.get('human_review_reason') or 'N/A'}",
        "",
        f"Summary: {rai.get('rai_summary','N/A')}",
        f"Consistency notes: {rai.get('consistency_notes','N/A')}",
        "",
        "Bias flags:",
    ]
    for flag in rai.get("bias_flags") or []:
        rai_lines.append(f"  • [{flag.get('bias_type','?')}] {flag.get('criterion_affected','?')}: {flag.get('description','?')}")
    if not (rai.get("bias_flags") or []):
        rai_lines.append("  None detected")
    rai_lines += ["", "Score adjustments:"]
    for adj in rai.get("recommended_adjustments") or []:
        rai_lines.append(f"  • {adj.get('criterion_id')}: {adj.get('current_level')} → {adj.get('suggested_level')} ({adj.get('reason')})")
    if not (rai.get("recommended_adjustments") or []):
        rai_lines.append("  None")
    rai_text = "\n".join(rai_lines)

    # ── Build corrections table data ─────────────────────────────────────────
    scores_list = report.scores.get("scores", [])
    corrections_data = [
        [
            s["criterion_name"],
            s["level_awarded"],
            s["points_awarded"],
            s["max_points"],
            "",       # corrected_level (instructor fills in)
            "",       # reason (instructor fills in)
        ]
        for s in scores_list
    ]

    # Pack current report metadata into JSON for the correction submit handler
    import json
    report_meta = json.dumps({
        "student_label": report.student_label,
        "scores": [
            {
                "criterion_id":   s["criterion_id"],
                "criterion_name": s["criterion_name"],
                "level_awarded":  s["level_awarded"],
                "points_awarded": s["points_awarded"],
            }
            for s in scores_list
        ],
    })

    return privacy_text, xai_text, rai_text, report.feedback, corrections_data, report_meta


# ── RL Corrections ───────────────────────────────────────────────────────────

LEVEL_TO_POINTS = {
    # Maps (criterion_id, level) → points — loaded from rubric at startup
}

def _build_level_map():
    import json
    rubric = json.loads((Path(__file__).parent / "rubric.json").read_text())
    for c in rubric["criteria"]:
        for level, data in c["levels"].items():
            LEVEL_TO_POINTS[(c["id"], level)] = data["points"]

_build_level_map()

VALID_LEVELS = ["excellent", "competent", "needs_improvement", "inadequate", ""]


def submit_corrections(corrections_table, report_meta_json):
    import json
    if not report_meta_json or report_meta_json == "{}":
        return "Grade a submission first before submitting corrections."

    meta   = json.loads(report_meta_json)
    label  = meta["student_label"]
    scores = {s["criterion_id"]: s for s in meta["scores"]}
    saved  = []

    for row in corrections_table:
        cname, orig_level, orig_pts, max_pts, new_level, reason = row
        new_level = (new_level or "").strip().lower().replace(" ", "_")
        if not new_level or new_level == orig_level:
            continue   # no change — skip

        # Find criterion_id from name
        cid = next(
            (k for k, v in scores.items() if v["criterion_name"] == cname), None
        )
        if cid is None:
            continue

        new_pts = LEVEL_TO_POINTS.get((cid, new_level), orig_pts)
        save_correction(
            student_label    = label,
            criterion_id     = cid,
            criterion_name   = cname,
            original_level   = orig_level,
            original_points  = int(orig_pts),
            corrected_level  = new_level,
            corrected_points = new_pts,
            instructor_reason = reason or "(no reason given)",
            submission_excerpt = "",
        )
        saved.append(f"  {cname}: {orig_level} → {new_level} ({reason or 'no reason'})")

    if not saved:
        return "No changes detected. To save a correction, enter a new level in the 'Your Level' column."

    stats = get_agreement_stats()
    return (
        f"✅ {len(saved)} correction(s) saved. These will inform future grading.\n\n"
        + "\n".join(saved)
        + f"\n\nRL Agreement rate (all time): {stats.get('agreement_rate_pct','?')}%"
    )


def show_rl_stats():
    stats = get_agreement_stats()
    if "status" in stats:
        return "No grading data yet. Grade some submissions first."
    lines = [
        "RL CALIBRATION DASHBOARD",
        "─" * 40,
        f"Total criteria graded : {stats['total_criteria_graded']}",
        f"Instructor corrections: {stats['total_corrections']}",
        f"AI agreement rate     : {stats['agreement_rate_pct']}%",
        f"Correction rate       : {stats['correction_rate_pct']}%",
        "",
        "Per-criterion correction patterns:",
    ]
    for cid, info in (stats.get("by_criterion") or {}).items():
        lines.append(f"  {cid}: {info['corrections']} corrections — {info['direction']}")
    if not stats.get("by_criterion"):
        lines.append("  No corrections yet.")
    return "\n".join(lines)


# ── Weekly rollup ─────────────────────────────────────────────────────────────

def run_rollup(week_str):
    try:
        return generate_rollup(week_str.strip() or None)
    except Exception as e:
        return f"Error generating rollup: {e}"


# ── Gradio layout ─────────────────────────────────────────────────────────────

with gr.Blocks(title="Assignment 1.5 Grader") as demo:
    report_meta_state = gr.State("{}")

    gr.Markdown("## Assignment 1.5 — ML Visual Framework Grader")
    gr.Markdown(
        "Upload a **PDF, DOCX, or image** containing the student's submission. "
        "Text and all embedded images are extracted and analyzed together. "
        "Grading always runs to completion — guardrails are advisory only."
    )

    with gr.Row():
        student_name = gr.Textbox(label="Student Name / ID", placeholder="e.g. Jane Smith", scale=1)

    with gr.Row():
        document_file = gr.File(
            label="Upload Submission (PDF, DOCX, PNG, JPG)",
            file_types=[".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg"],
            scale=2,
        )
        extra_text = gr.Textbox(
            label="Additional Text (optional)",
            lines=6,
            placeholder="Paste any text not captured in the document...",
            scale=2,
        )

    grade_btn = gr.Button("Grade Submission", variant="primary", size="lg")

    with gr.Tabs():
        with gr.Tab("📋 Privacy & Guardrails"):
            privacy_out = gr.Textbox(lines=22, interactive=False, show_label=False)

        with gr.Tab("⚖️ XAI Score Breakdown"):
            xai_out = gr.Textbox(lines=32, interactive=False, show_label=False)

        with gr.Tab("🧭 RAI Audit"):
            rai_out = gr.Textbox(lines=24, interactive=False, show_label=False)

        with gr.Tab("💬 Feedback"):
            feedback_out = gr.Textbox(lines=26, interactive=False, show_label=False)

        with gr.Tab("🎓 Corrections (RL)"):
            gr.Markdown(
                "Review the AI scores below. If a score is wrong, enter the correct level "
                "in **Your Level** and add a brief reason. Click **Save Corrections** — "
                "these are injected as few-shot examples into all future grading runs."
            )
            corrections_table = gr.Dataframe(
                headers=["Criterion", "AI Level", "AI Points", "Max", "Your Level", "Reason"],
                datatype=["str", "str", "number", "number", "str", "str"],
                col_count=(6, "fixed"),
                interactive=True,
                wrap=True,
            )
            save_corrections_btn = gr.Button("Save Corrections", variant="secondary")
            corrections_result   = gr.Textbox(label="Result", lines=8, interactive=False)
            gr.Markdown("---")
            rl_stats_btn = gr.Button("Show RL Calibration Stats")
            rl_stats_out = gr.Textbox(label="RL Dashboard", lines=14, interactive=False)

            save_corrections_btn.click(
                fn=submit_corrections,
                inputs=[corrections_table, report_meta_state],
                outputs=corrections_result,
            )
            rl_stats_btn.click(fn=show_rl_stats, outputs=rl_stats_out)

        with gr.Tab("📊 Weekly Report"):
            gr.Markdown(
                "Generate a class-wide rollup for any graded week. "
                "Includes per-criterion averages, common issues, flagged students, "
                "RL calibration metrics, and an AI synthesis of patterns."
            )
            week_choices = available_weeks()
            week_dropdown = gr.Dropdown(
                choices=week_choices,
                value=week_choices[0] if week_choices else None,
                label="Select Week (ISO format YYYY-WWW)",
                allow_custom_value=True,
            )
            rollup_btn    = gr.Button("Generate Rollup", variant="primary")
            rollup_out    = gr.Textbox(label="Weekly Report", lines=40, interactive=False)

            rollup_btn.click(fn=run_rollup, inputs=week_dropdown, outputs=rollup_out)

    grade_btn.click(
        fn=run_grader,
        inputs=[document_file, student_name, extra_text],
        outputs=[privacy_out, xai_out, rai_out, feedback_out, corrections_table, report_meta_state],
    )

    gr.Markdown(
        "*PII scrubbed before API calls. Grades stored in `grades_store.jsonl` + `grades_log.csv`. "
        "Instructor corrections stored in `corrections_store.json` (all gitignored).*"
    )


if __name__ == "__main__":
    demo.launch()

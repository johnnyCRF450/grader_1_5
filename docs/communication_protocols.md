# Communication Protocols — Assignment 1.5 Grader

## Protocol Overview

All inter-agent communication is **synchronous and centrally orchestrated**.
The Orchestrator is the sole message router — no agent contacts another directly.

```
Raw Submission
     │
     ▼
① Orchestrator ──────────────────────────────► Privacy Agent
              ◄── {scrubbed_text, pii_found,    ──────────────
                   regex_detections,             Protocol: Direct Python call
                   llm_detections,              Model: claude-haiku-4-5
                   privacy_report}              Technique: 2-pass (regex → LLM)
     │
     ▼
② Orchestrator ──────────────────────────────► Context Agent
              ◄── context_string (plain text)   ──────────────
                                                Protocol: Direct Python call
                                                Model: None (pure file I/O)
                                                Output: ~3000 char context string
     │
     ▼
③ Orchestrator ──────────────────────────────► Guardrail Agent
              ◄── {passes_guardrails: bool,      ──────────────
                   algorithm_count: int,         Protocol: Anthropic Messages API
                   has_classification: bool,     Model: claude-haiku-4-5
                   has_reflection: bool,         max_tokens: 600
                   flag_for_human_review: bool,  Response: JSON
                   warnings: [str]}
     │
     ├── IF passes_guardrails = false → HALT, return GradeReport(halted=True)
     │
     ▼
④ Orchestrator ──────────────────────────────► Analyzer Agent
              ◄── structured_analysis (text)     ──────────────
                                                Protocol: Anthropic Messages API
                                                Model: claude-sonnet-4-6
                                                max_tokens: 1500
                                                Optional: image_b64 (vision)
                                                Multimodal: text + image content blocks
     │
     ▼
⑤ Orchestrator ──────────────────────────────► Scorer Agent
              ◄── {scores: [...], total_points,  ──────────────
                   total_possible,               Protocol: Anthropic Messages API
                   overall_confidence}           Model: claude-sonnet-4-6
                                                max_tokens: 3000
                                                Response: JSON (parsed with json.loads)
                                                XAI fields per criterion:
                                                  confidence, evidence,
                                                  rationale, counterfactual,
                                                  uncertainty_notes
     │
     ▼
⑥ Orchestrator ──────────────────────────────► RAI Agent
              ◄── {rai_approved: bool,           ──────────────
                   consistency_check: str,       Protocol: Anthropic Messages API
                   bias_flags: [...],            Model: claude-sonnet-4-6
                   recommended_adjustments: [...],max_tokens: 1500
                   human_review_recommended}     Response: JSON
                                                Orchestrator applies adjustments
                                                to scores before next step
     │
     ▼
⑦ Orchestrator ──────────────────────────────► Feedback Agent
              ◄── feedback_text (markdown)       ──────────────
                                                Protocol: Anthropic Messages API
                                                Model: claude-sonnet-4-6
                                                max_tokens: 1200
                                                Response: Plain text (markdown)
     │
     ▼
  GradeReport (dataclass)
     ├── privacy_report: dict
     ├── guardrail_report: dict
     ├── analysis: str
     ├── scores: dict (with XAI + RAI fields)
     ├── rai_report: dict
     └── feedback: str
```

## Data Schemas

### Shared Context String (built by Context Agent)
```
=== ASSIGNMENT CONTEXT ===
  Assignment instructions
  Grading scope notes

=== GRADING RUBRIC ===
  9 criteria × 4 levels (excellent/competent/needs_improvement/inadequate)
  Point values and level descriptions

=== ML ALGORITHM KNOWLEDGE BASE ===
  18 reference algorithms with correct classifications
  Domain descriptions
  Minimum algorithm count requirement
```

### Guardrail Report (JSON)
```json
{
  "is_relevant": true,
  "algorithm_count": 10,
  "has_classification": true,
  "has_visual_description": true,
  "has_reflection": true,
  "inappropriate_content": false,
  "passes_guardrails": true,
  "flag_for_human_review": false,
  "flag_reason": null,
  "warnings": [],
  "word_count": 450
}
```

### Score Object (JSON — per criterion)
```json
{
  "criterion_id": "classification_accuracy",
  "criterion_name": "Classification Accuracy",
  "level_awarded": "competent",
  "points_awarded": 9,
  "max_points": 10,
  "confidence": 0.85,
  "evidence": "Student correctly identifies Random Forest as supervised...",
  "rationale": "Accurate classifications across 9 of 10 algorithms...",
  "counterfactual": "To reach Excellent, student would need to demonstrate...",
  "uncertainty_notes": null,
  "rai_adjusted": false
}
```

### RAI Report (JSON)
```json
{
  "consistency_check": "pass",
  "consistency_notes": "Scores are internally consistent across criteria.",
  "bias_flags": [],
  "evidence_quality": "strong",
  "fairness_concerns": [],
  "recommended_adjustments": [],
  "rai_approved": true,
  "rai_summary": "No bias detected. Scores are well-evidenced.",
  "human_review_recommended": false,
  "human_review_reason": null
}
```

## Model Selection Rationale

| Task | Model | Reason |
|------|-------|--------|
| Privacy scrubbing | Haiku | High-throughput, mechanical text transformation. Speed > nuance. |
| Guardrail validation | Haiku | Structured JSON classification with clear binary criteria. |
| Submission analysis | Sonnet | Requires nuanced extraction + optional vision (image reading). |
| XAI scoring | Sonnet | Complex multi-criteria judgment requiring reasoning depth. |
| RAI audit | Sonnet | Requires meta-reasoning about the scoring agent's own output. |
| Feedback generation | Sonnet | High-quality prose generation requiring empathy and specificity. |

## Privacy Protocol

```
Raw Text
  │
  ├── Regex Pass (synchronous, no API)
  │     Patterns: email, phone, SSN, student_id, zip, LinkedIn URL
  │     Speed: <1ms
  │
  └── LLM Pass (Haiku)
        Detects: names, institutions, locations, handles, portfolio URLs
        Never logs the original text — only the scrubbed version continues
        Scrubbed text is what ALL subsequent agents see
```

No raw submission text is ever logged. `grades_log.csv` stores only anonymized results.

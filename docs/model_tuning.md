# Model Tuning — Assignment 1.5 Grader

## Agent-Level Parameter Configuration

Each agent is tuned independently based on its task complexity and output requirements.

```
Agent               Model                   max_tokens   Temperature*   Role
──────────────────  ──────────────────────  ───────────  ─────────────  ────────────────────
Privacy Agent       claude-haiku-4-5        len(text)+200   default      Transformation
Guardrail Agent     claude-haiku-4-5        600             default      Classification
Context Agent       (no LLM)                —               —            Data loading
Analyzer Agent      claude-sonnet-4-6       1500            default      Extraction
Scorer Agent        claude-sonnet-4-6       3000            default      Reasoning (JSON)
RAI Agent           claude-sonnet-4-6       1500            default      Meta-reasoning
Feedback Agent      claude-sonnet-4-6       1200            default      Prose generation

*Temperature left at API default (1.0) for reproducibility and to avoid suppressing nuance.
```

## Token Budget Design

```
Agent          Input (est.)    max_tokens    Reasoning
─────────────  ─────────────  ─────────────  ─────────────────────────────────────────────
Privacy        500–2000        len+200        Must reproduce the full text — dynamic sizing
Guardrail      3000 (ctx+sub)  600           Simple JSON — tight budget reduces hallucination
Analyzer       4000 (ctx+sub)  1500          Needs room for 9 labeled extraction sections
Scorer         5000 (ctx+sub   3000          9 criteria × ~5 fields each = verbose JSON
               +analysis)
RAI            4000 (ctx+sub   1500          JSON with potentially many flags/adjustments
               +scores)
Feedback       3000 (ctx+sub   1200          ~400-500 word prose — buffer for formatting
               +analysis+rai)
```

## Model Tier Selection

```
              Complexity / Reasoning Depth Required
              Low ◄─────────────────────────► High
              │                                  │
Cost          │                                  │
Low    ───────┤  Haiku          Haiku            │
              │  (Privacy)      (Guardrail)      │
              │                                  │
              │                                  │
High   ───────┤              Sonnet   Sonnet  Sonnet  Sonnet
              │              (Analyze)(Score) (RAI)   (Feedback)
              │                                  │
              └──────────────────────────────────┘
```

**Why Haiku for Privacy and Guardrail?**
- Both are mechanical tasks with explicit rules
- Privacy: pattern replacement, not reasoning
- Guardrail: JSON boolean classification with fixed schema
- 3-5× cheaper and faster than Sonnet for same quality on these tasks

**Why Sonnet for Scoring, RAI, and Feedback?**
- Scoring requires: rubric interpretation, evidence location, confidence calibration
- RAI requires: meta-reasoning about another agent's output, bias detection
- Feedback requires: empathetic prose, specific references, nuanced tone

## Prompt Engineering Decisions

### System Prompt Structure (all agents)
```
[Role definition]
[Key principles / constraints]
[Shared context string — rubric + knowledge base + assignment instructions]
```

The shared context is appended to every agent's system prompt, not the user turn.
This keeps the instruction-following context stable across the multi-turn implicit conversation.

### JSON Output Enforcement (Scorer, Guardrail, RAI)
- Agents are instructed "Return ONLY valid JSON — no other text"
- Code strips markdown fences (` ```json `) before parsing
- Fallback: if json.loads() fails, the orchestrator catches and re-prompts once

### XAI Prompt Design (Scorer Agent)
The scorer is explicitly prompted to:
1. Quote directly from the submission (grounding, not paraphrase)
2. Assign confidence 0.0–1.0 (forces uncertainty acknowledgment)
3. Write a counterfactual (forces the scorer to reason about what's missing)
4. Note uncertainty (prevents false precision)

This design was chosen to make the grader's reasoning auditable — the instructor
can verify each score against the quoted evidence in the XAI tab.

### RAI Bias Detection Prompt Design
Six bias types are named explicitly in the system prompt to prime detection:
- **Style bias** — penalizing informal writing vs. content quality
- **Halo effect** — one strong section inflating unrelated criteria
- **Recency bias** — over-weighting the last section read
- **Length bias** — equating longer with better
- **Vocabulary bias** — penalizing clear simple writing
- **Internal inconsistency** — contradictory scores across criteria

Naming these explicitly reduces the likelihood the RAI agent misses them.

## Tuning Trade-offs

| Decision | Alternative Considered | Why This Choice |
|----------|----------------------|-----------------|
| Use Haiku for privacy/guardrails | Sonnet for all agents | 60% cost reduction; mechanical tasks don't need Sonnet's reasoning |
| Default temperature (1.0) | Low temperature (0.2) for scoring | Low temp can suppress evidence-gathering diversity; default produces more thorough scoring |
| Dynamic token limit for privacy | Fixed 2048 | Prevents truncation of long submissions — privacy pass must handle full text |
| Shared context in system prompt | Shared context in user turn | System prompt content is more stable for instruction-following |
| Sequential pipeline | Parallel agent execution | Analyzer feeds Scorer; Scorer feeds RAI — dependencies require sequential ordering |
| Two-pass privacy (regex + LLM) | LLM-only | Regex catches high-confidence patterns at near-zero cost before LLM sees the text |

## Prompt Cache Opportunity

For bulk grading sessions (many submissions in one sitting), the shared context string
(~3000 tokens) is identical for every student. Enabling Anthropic's prompt caching
on the system prompt would reduce cost by ~90% on the cached portion after the first call.

```python
# To enable — add cache_control to system prompt in each agent:
system=[{
    "type": "text",
    "text": context,
    "cache_control": {"type": "ephemeral"}
}]
```

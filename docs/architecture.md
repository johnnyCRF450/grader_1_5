# Multi-Agent Architecture — Assignment 1.5 Grader

## System Overview

```mermaid
flowchart TD
    U([👤 Instructor\npastes submission\n+ optional infographic]) -->|raw text + image| O

    subgraph PIPELINE ["⚙️  7-Agent Grading Pipeline"]
        direction TB

        P["🔒 Privacy Agent\nagents/privacy_agent.py\n──────────────────────\nPass 1: Regex PII patterns\nPass 2: LLM contextual scrub\nModel: claude-haiku-4-5\nOutputs: scrubbed_text + audit log"]

        G["🛡️ Guardrail Agent\nagents/guardrail_agent.py\n──────────────────────\nValidates min requirements\n• ≥8 algorithms present\n• Submission is relevant\n• Content not inappropriate\nModel: claude-haiku-4-5\nOutputs: pass/fail + warnings"]

        CTX["📚 Context Agent\nagents/context_agent.py\n──────────────────────\nLoads rubric.json\nLoads algorithm knowledge base\nBuilds shared context string\nNo LLM call — pure Python"]

        ANA["🔍 Analyzer Agent\nagents/analyzer_agent.py\n──────────────────────\nExtracts algorithms listed\nMaps domains + classifications\nAnalyzes infographic (vision)\nModel: claude-sonnet-4-6\nOutputs: structured analysis text"]

        SCR["⚖️ Scorer Agent\nagents/scorer_agent.py\n──────────────────────\nScores all 9 rubric criteria\nXAI: confidence 0.0–1.0\nXAI: direct evidence quotes\nXAI: counterfactual reasoning\nModel: claude-sonnet-4-6\nOutputs: scores JSON"]

        RAI["🧭 RAI Agent\nagents/rai_agent.py\n──────────────────────\nBias detection (6 types)\nConsistency cross-check\nEvidence quality review\nScore adjustment recommendations\nModel: claude-sonnet-4-6\nOutputs: rai_report + adjustments"]

        FBK["💬 Feedback Agent\nagents/feedback_agent.py\n──────────────────────\nMotivational grade report\nReferences specific student work\nExplains scores in plain English\nAcknowledges RAI adjustments\nModel: claude-sonnet-4-6\nOutputs: feedback text"]

        O["🎯 Orchestrator\norchestrator.py\n──────────────────────\nCoordinates all 7 agents\nEnforces pipeline order\nApplies RAI adjustments\nBuilds GradeReport dataclass"]

        O -->|"① raw text"| P
        P -->|"scrubbed text + privacy audit"| O
        O -->|"② rubric_path"| CTX
        CTX -->|"context string"| O
        O -->|"③ scrubbed text + context"| G
        G -->|"guardrail report"| O
        O -->|"④ scrubbed text + context + image_b64"| ANA
        ANA -->|"structured analysis"| O
        O -->|"⑤ analysis + scrubbed text + context + rubric"| SCR
        SCR -->|"scores JSON with XAI fields"| O
        O -->|"⑥ scores + scrubbed text + context"| RAI
        RAI -->|"rai_report + adjustments"| O
        O -->|"⑦ adjusted scores + analysis + rai_report + context"| FBK
        FBK -->|"feedback text"| O
    end

    O -->|GradeReport| UI
    O -->|append row| LOG[("📄 grades_log.csv\nPII-free record")]

    subgraph UI ["🌐 Gradio Web UI  localhost:7860"]
        T1["Privacy & Guardrails tab"]
        T2["XAI Score Breakdown tab"]
        T3["RAI Audit tab"]
        T4["Feedback tab"]
        T5["Grade History tab"]
    end

    subgraph API ["☁️  Anthropic API"]
        H["claude-haiku-4-5\n(Privacy + Guardrail agents)\nFast, low-cost mechanical tasks"]
        S["claude-sonnet-4-6\n(Analyzer, Scorer, RAI, Feedback)\nComplex reasoning tasks"]
    end

    P <-->|"Messages API"| H
    G <-->|"Messages API"| H
    ANA <-->|"Messages API\n+ Vision (image)"| S
    SCR <-->|"Messages API"| S
    RAI <-->|"Messages API"| S
    FBK <-->|"Messages API"| S
```

## Agent Roles

| Agent | Model | Purpose | Guardrail Role |
|-------|-------|---------|----------------|
| Privacy | Haiku | Scrub PII before any data leaves the system | First line — protects student identity |
| Guardrail | Haiku | Validate minimum submission requirements | Second line — prevents garbage-in |
| Context | None (Python) | Build shared ground truth for all agents | Ensures consistent rubric + KB reference |
| Analyzer | Sonnet | Extract structured elements from submission | Separates understanding from judgment |
| Scorer | Sonnet | Score 9 criteria with XAI transparency | Core grading with confidence tracking |
| RAI | Sonnet | Audit for bias, consistency, fairness | Post-hoc fairness check before student sees grade |
| Feedback | Sonnet | Generate motivational, transparent report | Ensures communication is constructive |

## Halt Conditions

The pipeline halts after Guardrail validation if:
- Submission is not relevant to ML algorithms
- Fewer than 8 algorithms are present
- Submission is under 150 words
- Inappropriate content detected

A halted submission is logged with the halt reason and flagged for human review.
```
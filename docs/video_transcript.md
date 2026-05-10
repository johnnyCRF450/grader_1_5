# Video Transcript — Assignment 1.5 Multi-Agent Grader Walkthrough

*Format: YouTube-style explainer transcript. Timecodes approximate a 6-minute walkthrough video.*

---

**[00:00 — Intro]**

Hey everyone. Today I'm walking you through an automated multi-agent grading system built specifically for Assignment 1.5 — the ML Algorithm Visual Framework portfolio artifact. This system grades student submissions using seven specialized AI agents, each with a distinct role, and includes privacy protection, XAI transparency, and a Responsible AI fairness audit built right into the pipeline.

Let's dig in.

---

**[00:20 — The Problem]**

So the challenge with grading this assignment is that it has nine separate rubric criteria, covering everything from visual clarity and design to classification accuracy and personal reflection. Grading 30 students consistently across nine dimensions is time-consuming, and human graders — even experienced ones — can drift in their standards between the first and last submission they read.

That's where this system comes in.

---

**[00:45 — System Overview]**

The grader runs seven agents in sequence. Think of it like an assembly line, where each station does one specific job and passes its output to the next.

Here's the order:

One — Privacy Agent. Before the student's words touch any AI model, we scrub personally identifiable information. Names, emails, student IDs — all redacted. Two passes: a fast regex scan first, then a language model that catches the subtle stuff like "my professor at [university name]."

Two — Context Agent. This one doesn't call an AI at all. It just loads the rubric JSON and our ML algorithm knowledge base — a reference table of 18 algorithms with their correct classifications — and builds a shared context string that every downstream agent receives.

Three — Guardrail Agent. Before we do any real grading, we check: does this submission actually meet minimum requirements? Did the student include at least eight algorithms? Is the submission relevant to machine learning? Is it long enough to have meaningful content? If any check fails, grading halts and the instructor gets a clear explanation why.

Four — Analyzer Agent. This one reads the scrubbed submission carefully and extracts structured information: which algorithms were mentioned, how the student classified them, what examples were provided, what their visual framework looks like, what the reflection says. If the instructor uploads an image of the infographic, this agent actually *looks* at it using Claude's vision capability.

Five — Scorer Agent. This is the core grading step. For each of the nine rubric criteria, the scorer assigns a level — excellent, competent, needs improvement, or inadequate — and produces three XAI fields: a confidence score from zero to one, a direct quote from the submission as evidence, and a counterfactual — what the student would need to do to score one level higher.

Six — RAI Agent. The Responsible AI auditor. It reviews the scorer's output for six types of bias: style bias, halo effects, recency bias, length bias, vocabulary bias, and internal inconsistency. If it finds a problem, it recommends specific score adjustments, which the orchestrator applies before the student ever sees their grade.

Seven — Feedback Agent. Finally, the feedback agent writes a warm, specific, motivating grade report. It references the student's actual work — not generic praise — explains the scoring in plain English, and acknowledges any RAI adjustments transparently.

---

**[02:30 — The XAI Design]**

Let me spend a moment on the XAI — Explainable AI — design, because this is one of the most important features for an academic context.

Every score comes with three fields that make the grader's reasoning auditable. Evidence: a direct quote from the submission supporting the score. Rationale: why *this* level and not one above or below. And counterfactual: what specifically would earn a higher score.

This means the instructor can open the XAI tab, look at any criterion, and immediately verify whether the score makes sense. You don't have to trust the system blindly — you can audit it.

Confidence scores are also important. A confidence of 0.9 means the evidence is clear-cut. A 0.6 means there was ambiguity — maybe the student's reflection was borderline between competent and needs improvement. Low-confidence scores are the first ones an instructor should check manually.

---

**[03:15 — The RAI Fairness Audit]**

Now the RAI agent. This is something I'm particularly proud of.

The scoring agent is good, but AI systems can reproduce biases. A student who writes in a more casual, conversational style might get penalized compared to one who uses technical jargon — even if the *content* is equally strong. That's style bias, and it's unfair.

So after scoring, the RAI agent reads the scores and the submission together and asks: are these scores internally consistent? Is every score grounded in content evidence, not writing style? Are there any halo effects — where a beautiful infographic might have inflated the reflection score even though they're separate criteria?

If the RAI agent spots a problem, it recommends a specific adjustment: "change classification_accuracy from needs_improvement to competent — the student correctly classified 9 of 10 algorithms but the scorer may have over-weighted the one error." The orchestrator applies the adjustment, and the feedback agent mentions it transparently in the student-facing report.

---

**[04:10 — Privacy by Design]**

Quick note on privacy. FERPA and institutional data policies mean student information should not be sent to external AI services in raw form.

The privacy agent runs *before* any data touches the Anthropic API. The regex pass catches structured PII — emails, phone numbers, student IDs — in under a millisecond. Then the Haiku model (cheaper and faster than Sonnet) handles contextual PII like names and location references.

The scrubbed text is what all downstream agents see. The `grades_log.csv` file, which stores results over time, only records anonymized data. The raw submission is never stored.

---

**[04:50 — The Gradio UI]**

For the instructor workflow, I built a five-tab Gradio interface running locally at localhost:7860.

Tab one: paste the submission, optionally upload the infographic image, click Grade.
Tab two: see the privacy scrub report and guardrail validation results.
Tab three: the full XAI score breakdown — all nine criteria with evidence, confidence, and counterfactuals.
Tab four: the RAI audit report — bias flags, consistency check, any adjustments made.
Tab five: the motivational feedback report ready to copy into Brightspace.

There's also a Grade History tab showing a running CSV of all graded submissions.

---

**[05:30 — Model Selection]**

Two models are used: Haiku for the mechanical tasks — privacy scrubbing and guardrail validation — and Sonnet for the complex reasoning tasks — analysis, scoring, RAI, and feedback.

This isn't just a cost decision. Haiku is actually better suited to the mechanical tasks because those prompts are rule-based and explicit. Using Sonnet on a simple "classify as true/false" task doesn't improve accuracy, it just costs more.

---

**[05:50 — Wrap-up]**

So to recap: seven agents, two model tiers, privacy-first design, XAI transparency on every score, and a Responsible AI fairness audit before anything reaches the student.

The system doesn't replace the instructor — it handles the consistent, time-consuming mechanical work of applying a rubric, so the instructor's energy goes toward the judgment calls that actually require human context.

Thanks for watching. The full source code, architecture diagrams, and this transcript are all in the GitHub repo linked below.

---

*Background reading referenced in Assignment 1.5:*
- *"Unraveling the Differences Between AI, ML, DL, and GenAI"*
- *"What are the differences between AI, ML, DL, and Gen AI?"*

*Note to instructor: if you have the YouTube URLs for the above videos, add them to `assignment_context.py` under a `BACKGROUND_VIDEOS` dict and extend the Context Agent to include transcript summaries for additional grading context.*

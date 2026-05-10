"""
Context Agent — assembles the shared context string injected into every
LLM agent's system prompt. Single source of truth for rubric + knowledge base.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from assignment_context import get_knowledge_base_string

ASSIGNMENT_INSTRUCTIONS = """
ASSIGNMENT 1.5 — ML Algorithm Visual Framework (Portfolio Artifact)
Indiana Wesleyan University

TASK:
Students create a visual infographic/framework illustrating 8–10 machine learning
algorithms, classifying each by:
  • Algorithm type (Supervised or Unsupervised)
  • Application domains (Tabular Data, Computer Vision, NLP, Generative AI)
  • Real-world examples and use cases
  • Brief explanation of how the algorithm works
Additionally, students write a reflection on their learning experience.

KEY DOMAINS EMPHASIZED:
  Tabular Data | Computer Vision | NLP | Generative AI (especially)

GRADING SCOPE:
  • Visual framework: assessed on clarity, appeal, accuracy, relationships, comprehensiveness
  • Written reflection: assessed on insight, writing quality, explanation of classification process
  • Infographic may be submitted as image, PDF, or described in text
  • Portfolio artifact requirements are part of the assignment but do NOT affect rubric score directly
"""


def build_context(rubric_path: Path) -> str:
    rubric = json.loads(rubric_path.read_text())
    criteria_text = []
    for c in rubric["criteria"]:
        levels = " | ".join(
            f"{lvl} ({data['points']}pts)"
            for lvl, data in c["levels"].items()
        )
        criteria_text.append(f"  [{c['name']} — max {c['max_points']} pts]: {levels}")

    return f"""
=== ASSIGNMENT CONTEXT ===
{ASSIGNMENT_INSTRUCTIONS}

=== GRADING RUBRIC ===
Assignment: {rubric['assignment']}
Total points: {rubric['total_points']}
Overall thresholds: Excellent≥{rubric['thresholds']['excellent']}, Competent≥{rubric['thresholds']['competent']}, Needs Improvement≥{rubric['thresholds']['needs_improvement']}
Note: {rubric['grading_note']}

Criteria:
{chr(10).join(criteria_text)}

=== {get_knowledge_base_string()}
"""


def get_rubric(rubric_path: Path) -> dict:
    return json.loads(rubric_path.read_text())

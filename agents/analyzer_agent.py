"""
Analyzer Agent — extracts structured elements from a student submission.
Supports text submissions and optional base64-encoded infographic images.
"""

import base64
import anthropic


def analyze(
    client: anthropic.Anthropic,
    submission_text: str,
    context: str,
    image_b64: str | None = None,
) -> str:
    """Extract key elements. If image_b64 provided, analyzes the infographic visually."""

    content = []

    if image_b64:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": image_b64,
            },
        })
        content.append({
            "type": "text",
            "text": f"""Analyze both this infographic image AND the written submission text below.

Written submission:
---
{submission_text}
---

Extract and label each section:

1. ALGORITHMS_IDENTIFIED: List every ML algorithm named or described. Count them.
2. LEARNING_TYPE_CLASSIFICATIONS: How did the student classify each algorithm (supervised/unsupervised)?
3. DOMAIN_MAPPINGS: What domains (Tabular, CV, NLP, GenAI) did the student assign to each algorithm?
4. EXAMPLES_PROVIDED: What real-world examples or use cases were included?
5. VISUAL_DESCRIPTION: Describe the layout, structure, and design of the infographic (from the image if provided).
6. REFLECTION_CONTENT: Summarize the student's personal reflection and what they say they learned.
7. CLASSIFICATION_RATIONALE: Did the student explain WHY they classified algorithms as they did?
8. MISSING_ELEMENTS: What required elements are absent or underdeveloped?
9. ACCURACY_ISSUES: Note any factual errors in algorithm classification or description.""",
        })
    else:
        content.append({
            "type": "text",
            "text": f"""Analyze this student submission for Assignment 1.5 (ML Algorithm Visual Framework).

Submission:
---
{submission_text}
---

Extract and label each section:

1. ALGORITHMS_IDENTIFIED: List every ML algorithm named or described. Count them.
2. LEARNING_TYPE_CLASSIFICATIONS: How did the student classify each algorithm (supervised/unsupervised)?
3. DOMAIN_MAPPINGS: What domains (Tabular, CV, NLP, GenAI) did the student assign to each algorithm?
4. EXAMPLES_PROVIDED: What real-world examples or use cases were included?
5. VISUAL_DESCRIPTION: Describe the visual framework as the student describes it (or note if not described).
6. REFLECTION_CONTENT: Summarize the student's personal reflection and what they say they learned.
7. CLASSIFICATION_RATIONALE: Did the student explain WHY they classified algorithms as they did?
8. MISSING_ELEMENTS: What required elements are absent or underdeveloped?
9. ACCURACY_ISSUES: Note any factual errors in algorithm classification or description.""",
        })

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=f"""You are an academic submission analyzer. Extract information objectively.
Do not score — only identify what is present, what is absent, and flag factual errors.

{context}""",
        messages=[{"role": "user", "content": content}],
    )
    return response.content[0].text


def load_image(image_path: str) -> str | None:
    """Load an image file and return base64-encoded string."""
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        return None

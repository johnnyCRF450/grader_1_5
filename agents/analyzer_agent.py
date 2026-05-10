"""
Analyzer Agent — extracts structured elements from a student submission.
Accepts extracted text plus a list of base64 images (from PDF/DOCX/image files).
Sends all images in one multimodal request for holistic analysis.
"""

import anthropic

MAX_IMAGES_PER_REQUEST = 10


def analyze(
    client: anthropic.Anthropic,
    submission_text: str,
    context: str,
    images: list[str] | None = None,
) -> str:
    """
    Extract key elements from the submission.
    images: list of base64-encoded PNG strings extracted from the document.
    """
    images = images or []
    has_images = len(images) > 0

    content = []

    # Prepend all images so Claude sees the visuals before the text prompt
    for i, img_b64 in enumerate(images[:MAX_IMAGES_PER_REQUEST]):
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": img_b64},
        })

    image_instruction = ""
    if has_images:
        image_instruction = f"""
You have been provided {len(images)} image(s) extracted directly from the student's submitted document.
For each image:
  • Read ALL text visible in the image (OCR — treat it as content, not decoration)
  • Describe the visual layout, structure, color coding, and design choices
  • Identify every algorithm, label, arrow, grouping, or diagram element
  • Note any legends, axes, or category headers
  • Assess the visual quality and professionalism of the design
  • Identify any diagrams showing relationships or hierarchies between algorithms
"""

    content.append({
        "type": "text",
        "text": f"""Analyze this student's Assignment 1.5 submission completely.
{image_instruction}
Extracted document text:
---
{submission_text if submission_text.strip() else "[No text extracted — evaluate from images only]"}
---

Extract and label ALL of the following sections. Do not skip any section even if content is sparse:

1. ALGORITHMS_IDENTIFIED
   List every ML algorithm named or visible (in text OR images). Count them.
   Format: "Algorithm Name — source (text/image/both)"

2. LEARNING_TYPE_CLASSIFICATIONS
   How did the student classify each algorithm (supervised/unsupervised/other)?
   Note if this classification is correct or incorrect per the reference knowledge base.

3. DOMAIN_MAPPINGS
   What domains (Tabular, CV, NLP, GenAI) did the student assign to each algorithm?
   Identify any missing or incorrect domain assignments.

4. EXAMPLES_PROVIDED
   List all real-world examples or use cases the student included, per algorithm.

5. VISUAL_DESCRIPTION
   Describe the infographic layout in detail: structure type (quadrant/flowchart/table/concept map),
   color scheme, typography, visual hierarchy, use of icons/arrows/groupings.
   Comment on how clearly the visual communicates relationships between algorithms.

6. TEXT_IN_IMAGES
   List all text extracted from the images (labels, headings, descriptions, legends).

7. REFLECTION_CONTENT
   Summarize the student's personal reflection: what they learned, challenges faced,
   connections to course concepts, career applications.

8. CLASSIFICATION_RATIONALE
   Did the student explain WHY they classified algorithms as they did?
   Quote or describe any reasoning provided.

9. MISSING_ELEMENTS
   List required assignment elements that are absent or underdeveloped.

10. ACCURACY_ISSUES
    Note any factual errors in algorithm classification, description, or domain assignment.
    Be specific: "Student classified X as supervised — it is unsupervised." """,
    })

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2500,
        system=f"""You are an academic submission analyzer with multimodal capabilities.
You can read text, analyze visual designs, and extract content from embedded images.
Extract information objectively and completely. Do not skip sections.
Do not score — only identify what is present, what is absent, and what is inaccurate.

{context}""",
        messages=[{"role": "user", "content": content}],
    )
    return response.content[0].text

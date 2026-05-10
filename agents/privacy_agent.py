"""
Privacy Agent — scrubs PII from student submissions before any LLM processing.
Two-pass approach: fast regex patterns first, then LLM for contextual PII.
"""

import re
import json
import anthropic

_PII_PATTERNS = {
    "email":      r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "phone":      r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "ssn":        r"\b\d{3}-\d{2}-\d{4}\b",
    "student_id": r"\b(?:student\s*id|ID|#)\s*:?\s*\d{5,10}\b",
    "zip_code":   r"\b\d{5}(?:-\d{4})?\b",
    "url_with_name": r"https?://(?:www\.)?linkedin\.com/in/[^\s]+",
}


def scrub_regex(text: str) -> tuple[str, list[dict]]:
    """Pass 1 — fast pattern-based scrubbing. Returns scrubbed text and audit log."""
    scrubbed = text
    audit = []
    for pii_type, pattern in _PII_PATTERNS.items():
        for match in re.finditer(pattern, scrubbed, re.IGNORECASE):
            audit.append({"type": pii_type, "redacted": "[REDACTED]", "position": match.start()})
        scrubbed = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", scrubbed, flags=re.IGNORECASE)
    return scrubbed, audit


def scrub_llm(client: anthropic.Anthropic, text: str) -> tuple[str, list[str]]:
    """Pass 2 — LLM-based scrubbing for contextual/subtle PII.
    Uses Haiku (cheaper/faster) since this is a mechanical task."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=len(text) + 200,
        system="""You are a student privacy protection system for an academic grading tool.
Your ONLY job: replace personally identifiable information with placeholders.

Replace these with the indicated placeholder (preserve all other content exactly):
  Full student names          → [NAME_REDACTED]
  Student email addresses     → [EMAIL_REDACTED]
  University/school names     → [INSTITUTION_REDACTED]
  City, state, country refs   → [LOCATION_REDACTED]
  Social media handles/URLs   → [HANDLE_REDACTED]
  Student ID numbers          → [ID_REDACTED]
  Portfolio URLs with names   → [PORTFOLIO_URL_REDACTED]
  References to specific classmates → [CLASSMATE_REDACTED]

Keep all academic content (algorithm names, technical terms, assignment content) intact.
Return ONLY the scrubbed text — no explanation, no commentary.""",
        messages=[{"role": "user", "content": text}],
    )
    scrubbed = response.content[0].text

    # Detect what was changed
    redacted_types = list({
        m.group(0)
        for m in re.finditer(r"\[([A-Z_]+_REDACTED)\]", scrubbed)
    })
    return scrubbed, redacted_types


def scrub(client: anthropic.Anthropic, raw_text: str) -> dict:
    """Full two-pass PII scrub. Returns privacy report."""
    pass1_text, regex_audit = scrub_regex(raw_text)
    pass2_text, llm_redacted = scrub_llm(client, pass1_text)

    return {
        "scrubbed_text": pass2_text,
        "pii_found": len(regex_audit) > 0 or len(llm_redacted) > 0,
        "regex_detections": regex_audit,
        "llm_detections": llm_redacted,
        "privacy_report": (
            f"Privacy scrub complete. "
            f"Regex pass: {len(regex_audit)} pattern(s) redacted. "
            f"LLM pass: {len(llm_redacted)} contextual type(s) redacted: {', '.join(llm_redacted) or 'none'}."
        ),
    }

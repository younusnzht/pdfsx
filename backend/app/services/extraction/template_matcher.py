"""
MVP-stage institution detection: simple, explainable keyword matching
against statement header text. This is what ships first — the ML
classifier in services/ml/template_classifier.py only becomes worth using
once there's enough labeled training data (see ml_training_samples) to
outperform this. Keep both; fall back to this when the ML model returns
low confidence or isn't trained yet.
"""
from dataclasses import dataclass

# Keyed to the institutions validated during skill development.
# Extend this as new institutions/layouts are confirmed.
INSTITUTION_KEYWORDS: dict[str, list[str]] = {
    "RBC": ["royal bank", "rbc"],
    "TD": ["td canada trust", "td bank", "cash back visa"],
    "Scotiabank": ["scotiabank", "scotia"],
    "BMO": ["bank of montreal", "bmo"],
    "CIBC": ["cibc"],
    "National Bank": ["national bank of canada", "banque nationale"],
    "Desjardins": ["desjardins", "caisse"],
    "Tangerine": ["tangerine"],
    "Simplii": ["simplii financial"],
    "EQ Bank": ["eq bank", "equitable bank"],
    "Wealthsimple": ["wealthsimple"],
    "American Express": ["american express", "amex"],
    "Rogers Bank": ["rogers bank"],
    "Triangle Mastercard": ["triangle", "canadian tire"],
}


@dataclass
class TemplateMatch:
    institution: str | None
    confidence: float  # 1.0 if a keyword hit, 0.0 if none matched


def match_institution(header_text: str) -> TemplateMatch:
    lowered = header_text.lower()
    for institution, keywords in INSTITUTION_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return TemplateMatch(institution=institution, confidence=1.0)
    return TemplateMatch(institution=None, confidence=0.0)

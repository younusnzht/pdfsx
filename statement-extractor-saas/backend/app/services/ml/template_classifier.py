"""
Classical ML (TF-IDF + linear classifier — NOT a generative/LLM model)
that identifies which known institution/layout a statement matches, so the
deterministic template rules in institution_templates can be applied.

Training data comes from ml_training_samples (task_type="template"),
built up from confirmed extractions and reviewer corrections. Retrain
periodically via a scheduled job (see workers/tasks.py), not on every
request.

Falls back to "unknown" when confidence is below threshold, which routes
the statement to the generic CRF field-tagger instead of a specific
institution's rules — see field_extractor.py.
"""
from dataclasses import dataclass

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

MODEL_PATH = "app/services/ml/artifacts/template_classifier.joblib"
CONFIDENCE_THRESHOLD = 0.75


@dataclass
class TemplateMatch:
    institution: str | None
    confidence: float


def build_pipeline() -> Pipeline:
    """Defines the model architecture. Call train_and_save() to fit it on
    real labeled statement headers before this is usable in production."""
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=5000)),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )


def train_and_save(header_texts: list[str], labels: list[str]) -> None:
    pipeline = build_pipeline()
    pipeline.fit(header_texts, labels)
    joblib.dump(pipeline, MODEL_PATH)


def classify(header_text: str) -> TemplateMatch:
    try:
        pipeline: Pipeline = joblib.load(MODEL_PATH)
    except FileNotFoundError:
        # No trained model yet — MVP should rely on the deterministic
        # keyword/logo-text matcher in template_matcher.py instead.
        return TemplateMatch(institution=None, confidence=0.0)

    probabilities = pipeline.predict_proba([header_text])[0]
    best_idx = probabilities.argmax()
    confidence = float(probabilities[best_idx])
    institution = pipeline.classes_[best_idx] if confidence >= CONFIDENCE_THRESHOLD else None
    return TemplateMatch(institution=institution, confidence=confidence)

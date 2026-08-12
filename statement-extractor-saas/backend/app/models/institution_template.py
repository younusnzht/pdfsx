from sqlalchemy import JSON, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class InstitutionTemplate(UUIDPKMixin, TimestampMixin, Base):
    """
    Global (not tenant-scoped) registry of known statement layouts —
    codifies the deterministic parsing rules from the extraction skill
    (column names, date formats, debit/credit terminology per institution).
    Versioned because institutions periodically change their statement
    layout, which silently breaks a template — bump version_number and keep
    the old one for statements already parsed under it.
    """

    __tablename__ = "institution_templates"

    institution_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "bank_account" | "credit_card"
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Structural rules as data, not code — column header aliases, date regex
    # patterns, debit/credit disambiguation keywords, section-header logic.
    layout_rules: Mapped[dict] = mapped_column(JSON, nullable=False)

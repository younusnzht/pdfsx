import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.ml_training_sample import MLTrainingSample
from app.models.statement import Statement
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import TransactionCorrection, TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _get_owned_statement(db: Session, statement_id: uuid.UUID, tenant_id: uuid.UUID) -> Statement:
    statement = db.query(Statement).filter(Statement.id == statement_id, Statement.tenant_id == tenant_id).first()
    if statement is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Statement not found")
    return statement


@router.get("/by-statement/{statement_id}", response_model=list[TransactionOut])
async def list_transactions(
    statement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_statement(db, statement_id, current_user.tenant_id)

    return (
        db.query(Transaction)
        .filter(Transaction.statement_id == statement_id, Transaction.tenant_id == current_user.tenant_id)
        .order_by(Transaction.row_order)
        .all()
    )


@router.patch("/{transaction_id}", response_model=TransactionOut)
async def correct_transaction(
    transaction_id: uuid.UUID,
    correction: TransactionCorrection,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.tenant_id == current_user.tenant_id)
        .first()
    )
    if transaction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")

    before = {
        "raw_date": transaction.raw_date,
        "raw_description": transaction.raw_description,
        "raw_debit": transaction.raw_debit,
        "raw_credit": transaction.raw_credit,
    }

    update_data = correction.model_dump(exclude_unset=True)
    changed = False
    for field, value in update_data.items():
        if getattr(transaction, field) != value:
            setattr(transaction, field, value)
            changed = True

    transaction.reviewed = True
    transaction.reviewed_by_id = current_user.id
    if changed:
        transaction.was_corrected = True
        transaction.is_uncertain = False

        db.add(
            MLTrainingSample(
                source_transaction_id=transaction.id,
                task_type="field_correction",
                input_features=before,
                corrected_label=update_data,
            )
        )

    db.commit()
    db.refresh(transaction)
    return transaction

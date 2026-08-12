"""
Review-UI endpoints: list a statement's extracted rows and accept
corrections. Every correction should also insert an MLTrainingSample —
this is the feedback loop that improves the classical models over time
without calling any external AI API.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.transaction import TransactionCorrection

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/by-statement/{statement_id}")
async def list_transactions(statement_id: str, db: Session = Depends(get_db)):
    # TODO: query Transaction rows for this statement, tenant-scoped
    return {"statement_id": statement_id, "transactions": []}


@router.patch("/{transaction_id}")
async def correct_transaction(transaction_id: str, correction: TransactionCorrection, db: Session = Depends(get_db)):
    # TODO: apply correction, set was_corrected=True, reviewed=True,
    # write an MLTrainingSample row capturing the before/after.
    return {"transaction_id": transaction_id, "status": "not_yet_implemented"}

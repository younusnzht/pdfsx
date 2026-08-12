"""
Upload + list + status endpoints for statements. Auth dependency and
tenant-scoping dependency are stubbed with TODOs — wire these to the real
get_current_user dependency once app/api/deps.py is implemented.
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter(prefix="/statements", tags=["statements"])
settings = get_settings()


@router.post("/upload")
async def upload_statement(file: UploadFile, db: Session = Depends(get_db)):
    """
    Accepts a PDF, saves it to local disk under a tenant-scoped path,
    creates a Statement row, and enqueues the Celery extraction task.
    Skeleton only — file validation (size/type), tenant resolution from
    the auth token, and the actual Statement row creation are TODO.
    """
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    statement_id = str(uuid.uuid4())
    destination = upload_dir / f"{statement_id}.pdf"

    contents = await file.read()
    destination.write_bytes(contents)

    # TODO: create Statement row, enqueue extract_statement_task.delay(...)

    return {"statement_id": statement_id, "filename": file.filename, "status": "uploaded"}


@router.get("/{statement_id}")
async def get_statement(statement_id: str, db: Session = Depends(get_db)):
    # TODO: fetch Statement + its Transactions, scoped to the requesting tenant
    return {"statement_id": statement_id, "status": "not_yet_implemented"}

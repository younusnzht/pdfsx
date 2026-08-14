import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.statement import Statement
from app.models.user import User
from app.schemas.statement import StatementOut
from app.workers.tasks import extract_statement_task

router = APIRouter(prefix="/statements", tags=["statements"])
settings = get_settings()


@router.post("/upload", response_model=StatementOut)
async def upload_statement(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only PDF uploads are supported right now")

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB limit",
        )

    tenant_dir = Path(settings.UPLOAD_DIR) / str(current_user.tenant_id)
    tenant_dir.mkdir(parents=True, exist_ok=True)

    statement_id = uuid.uuid4()
    destination = tenant_dir / f"{statement_id}.pdf"
    destination.write_bytes(contents)

    statement = Statement(
        id=statement_id,
        tenant_id=current_user.tenant_id,
        uploaded_by_id=current_user.id,
        original_filename=file.filename or "statement.pdf",
        storage_path=str(destination),
    )
    db.add(statement)
    db.commit()
    db.refresh(statement)

    extract_statement_task.delay(str(statement.id), str(destination))

    return statement


@router.get("/{statement_id}", response_model=StatementOut)
async def get_statement(
    statement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = (
        db.query(Statement)
        .filter(Statement.id == statement_id, Statement.tenant_id == current_user.tenant_id)
        .first()
    )
    if statement is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Statement not found")
    return statement

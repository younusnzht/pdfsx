from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.core.slugify import slugify
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _unique_slug(db: Session, base_name: str) -> str:
    base_slug = slugify(base_name)
    slug = base_slug
    suffix = 2
    while db.query(Tenant).filter(Tenant.slug == slug).first() is not None:
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


@router.post("/signup", response_model=TokenResponse)
async def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    tenant = Tenant(name=payload.tenant_name, slug=_unique_slug(db, payload.tenant_name))
    db.add(tenant)
    db.flush()

    user = User(
        tenant_id=tenant.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.owner,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(subject=str(user.id), tenant_id=str(tenant.id)),
        refresh_token=create_refresh_token(subject=str(user.id), tenant_id=str(tenant.id)),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    invalid_credentials = HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise invalid_credentials
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated")
    return TokenResponse(
        access_token=create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id)),
        refresh_token=create_refresh_token(subject=str(user.id), tenant_id=str(user.tenant_id)),
    )

"""
Signup creates a new Tenant + its first User (role=owner). Login issues
JWT access + refresh tokens. Password hashing and JWT logic live in
app.core.security — never re-implement either inline in a route.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.db.session import get_db
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
async def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    # TODO: create Tenant row, create User row (role=owner) with
    # hash_password(payload.password), then issue tokens below.
    hashed = hash_password(payload.password)  # noqa: F841 — used once User creation is wired up
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Signup not yet wired to the database")


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    # TODO: fetch User by email, verify_password(payload.password, user.hashed_password)
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Login not yet wired to the database")

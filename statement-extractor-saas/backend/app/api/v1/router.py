from fastapi import APIRouter

from app.api.v1.routers import auth, statements, transactions

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(statements.router)
api_router.include_router(transactions.router)

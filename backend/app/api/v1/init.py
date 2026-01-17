"""
MATRXe API v1 Router
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, users, digital_twins, chat, tasks,
    voice, face, billing, admin, health
)

api_router = APIRouter()

# Include all routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(digital_twins.router, prefix="/digital-twins", tags=["Digital Twins"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Scheduled Tasks"])
api_router.include_router(voice.router, prefix="/voice", tags=["Voice Processing"])
api_router.include_router(face.router, prefix="/face", tags=["Face Processing"])
api_router.include_router(billing.router, prefix="/billing", tags=["Billing & Credits"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(health.router, prefix="/health", tags=["Health"])

__all__ = ["api_router"]
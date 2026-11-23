"""
Agregador de rutas API v1 para SOFIA Platform.
"""
from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.entitlements import router as entitlements_router
from app.api.v1.billing import router as billing_router
from app.api.v1.metrics import router as metrics_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(tenants_router)
api_v1_router.include_router(entitlements_router)
api_v1_router.include_router(billing_router)
api_v1_router.include_router(metrics_router)

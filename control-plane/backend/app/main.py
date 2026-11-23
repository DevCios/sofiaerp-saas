"""
Punto de Entrada Principal de la Aplicación SOFIA Platform API.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.api.v1.router import api_v1_router
from app.api.admin_ui import admin_ui_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación: inicialización de recursos y tablas."""
    # Inicialización segura de tablas del Control Plane si no existen
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed inicial seguro de Superadministrador SOFIA
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        from app.models.user import User
        from app.core.security import get_password_hash
        admin_email = os.getenv("SOFIA_SUPERADMIN_EMAIL", "admin@sofiaerp.com")
        admin_pass = os.getenv("SOFIA_SUPERADMIN_PASSWORD", "SofiaAdmin2026!")
        stmt = select(User).where(User.email == admin_email)
        res = await session.execute(stmt)
        if not res.scalar_one_or_none():
            superadmin = User(
                email=admin_email,
                password_hash=get_password_hash(admin_pass),
                full_name="Super Administrador SOFIA",
                is_active=True,
                is_superadmin=True,
            )
            session.add(superadmin)
            await session.commit()

    yield
    # Cierre ordenado de conexiones
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Plataforma SaaS Central para Gestión Multiproducto, Multi-tenant y Licenciamiento de SOFIA ERP.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Configuración de CORS estricto
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Middleware global para inyección de cabeceras de seguridad."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


# Inclusión de Routers de API y Panel Gráfico de Administración
app.include_router(api_v1_router, prefix="/api")
app.include_router(admin_ui_router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "platform": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "documentation": "/api/docs",
    }

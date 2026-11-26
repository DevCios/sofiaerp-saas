"""
Punto de Entrada Principal de la Aplicación SOFIA Platform API.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
import app.models  # Asegura registro de todos los modelos ORM en Base.metadata
from app.api.v1.router import api_v1_router
from app.api.admin_ui import admin_ui_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación: inicialización de recursos y tablas."""
    # Inicialización segura de tablas del Control Plane si no existen
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migración segura e idempotente de columnas de suscripción en tenants
        migration_statements = [
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS plan_code VARCHAR(50) DEFAULT 'SOFIA-ERP-PRO'",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS billing_cycle VARCHAR(20) DEFAULT 'MONTHLY'",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMPTZ",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS payment_status VARCHAR(30) DEFAULT 'PAID'",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS last_payment_date TIMESTAMPTZ",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS last_payment_reference VARCHAR(100)",
        ]
        for stmt in migration_statements:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass

    # Seed inicial seguro de Superadministrador SOFIA
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        from app.models.user import User
        from app.core.security import get_password_hash
        admin_email = os.getenv("SOFIA_SUPERADMIN_EMAIL", "admin@sofiaerp.com")
        admin_pass = os.getenv("SOFIA_SUPERADMIN_PASSWORD", "SofiaAdmin2026!")
        stmt = select(User).where(User.email == admin_email)
        res = await session.execute(stmt)
        existing_admin = res.scalar_one_or_none()
        if not existing_admin:
            superadmin = User(
                email=admin_email,
                password_hash=get_password_hash(admin_pass),
                full_name="Super Administrador SOFIA",
                is_active=True,
                is_superadmin=True,
                mfa_enabled=False,
            )
            session.add(superadmin)
            await session.commit()
        else:
            existing_admin.password_hash = get_password_hash(admin_pass)
            existing_admin.is_active = True
            existing_admin.is_superadmin = True
            existing_admin.mfa_enabled = False
            await session.commit()

        # Seed idempotente de Producto y Planes Comerciales SOFIA ERP
        from app.models.product import Product, ProductPlan
        prod_stmt = select(Product).where(Product.code == "SOFIA-ERP")
        product = (await session.execute(prod_stmt)).scalar_one_or_none()
        if not product:
            product = Product(
                code="SOFIA-ERP",
                name="SOFIA ERP Cloud",
                description="ERP Multi-Tenant con Facturación Electrónica SUNAT y GRE.",
                is_active=True,
            )
            session.add(product)
            await session.flush()

        default_plans = [
            ("SOFIA-PLAN-EMP", "Plan Emprendedor", "BASIC", 2, 2, 10, 9.90),
            ("SOFIA-PLAN-PRO", "Plan Pyme Pro", "PROFESSIONAL", 5, 5, 25, 14.90),
            ("SOFIA-PLAN-CORP", "Plan Corporativo", "ENTERPRISE", 15, 15, 100, 19.90),
        ]
        for code, name, tier, max_u, max_s, storage_gb, price in default_plans:
            p_res = await session.execute(select(ProductPlan).where(ProductPlan.code == code))
            if not p_res.scalar_one_or_none():
                session.add(ProductPlan(
                    product_id=product.id,
                    code=code,
                    name=name,
                    tier=tier,
                    max_users=max_u,
                    max_concurrent_sessions=max_s,
                    storage_gb_limit=storage_gb,
                    base_price=price,
                ))
        await session.commit()

    yield
    # Cierre ordenado de conexiones
    await engine.dispose()


_is_prod = settings.ENVIRONMENT.lower() == "production"

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Plataforma SaaS Central para Gestión Multiproducto, Multi-tenant y Licenciamiento de SOFIA ERP.",
    docs_url=None if _is_prod else "/api/docs",
    redoc_url=None if _is_prod else "/api/redoc",
    openapi_url=None if _is_prod else "/api/openapi.json",
    lifespan=lifespan,
)

# Configuración de CORS estricto (nunca combinar '*' con allow_credentials=True)
_cors_origins = settings.allowed_hosts_list
_allow_creds = "*" not in _cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_creds,
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

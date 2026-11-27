# -*- coding: utf-8 -*-
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.admin_ui import router as admin_ui_router
from app.api.billing import router as billing_router
from app.api.docs_portal import router as docs_portal_router
from app.api.mcp_server import router as mcp_router
from app.api.oauth_mcp import router as oauth_mcp_router
from app.api.public_portal import router as public_portal_router
from app.api.v1.routes import router as v1_router
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, Base, async_engine
import app.models  # noqa: F401 - registra todos los modelos en Base.metadata
from app.models import ApiRequestLog

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migraciones idempotentes sin downtime para bases existentes
        await conn.execute(text("ALTER TABLE issuers ADD COLUMN IF NOT EXISTS is_nrus BOOLEAN NOT NULL DEFAULT FALSE"))
        await conn.execute(text("ALTER TABLE issuers ADD COLUMN IF NOT EXISTS plan_name VARCHAR(40) NOT NULL DEFAULT 'STARTER'"))
        await conn.execute(text("ALTER TABLE issuers ADD COLUMN IF NOT EXISTS monthly_quota INTEGER NOT NULL DEFAULT 500"))
        await conn.execute(text("ALTER TABLE issuers ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(36)"))
        await conn.execute(text("ALTER TABLE api_clients ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(36)"))
        await conn.execute(text("ALTER TABLE api_request_logs ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(36)"))
    yield
    await async_engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.PUBLIC_BASE_URL, "https://sofiaerp.com", "https://admin.sofiaerp.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-API-Key", "X-Internal-Service-Key", "Mcp-Session-Id", "MCP-Protocol-Version"],
)


@app.middleware("http")
async def audit_rest_api_middleware(request: Request, call_next):
    path = request.url.path
    should_log = path.startswith("/api/v1/documents") or path.startswith("/api/v1/ai/")
    if not should_log:
        return await call_next(request)
    t0 = time.monotonic()
    response = await call_next(request)
    try:
        ruc = request.query_params.get("issuer_ruc") or request.query_params.get("ruc")
        async with AsyncSessionLocal() as session:
            session.add(
                ApiRequestLog(
                    source="REST",
                    method=request.method,
                    action=path[:160],
                    issuer_ruc=ruc[:11] if ruc else None,
                    client_label="API REST",
                    status_code=response.status_code,
                    latency_ms=int((time.monotonic() - t0) * 1000),
                )
            )
            await session.commit()
    except Exception:
        pass
    return response


app.include_router(v1_router)
app.include_router(billing_router)
app.include_router(mcp_router)
app.include_router(oauth_mcp_router)
app.include_router(docs_portal_router)
app.include_router(public_portal_router)
app.include_router(admin_ui_router)

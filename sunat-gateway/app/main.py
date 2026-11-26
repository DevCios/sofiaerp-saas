# -*- coding: utf-8 -*-
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin_ui import router as admin_ui_router
from app.api.public_portal import router as public_portal_router
from app.api.v1.routes import router as v1_router
from app.core.config import get_settings
from app.core.database import Base, async_engine
import app.models  # noqa: F401 - registra todos los modelos en Base.metadata

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Internal-Service-Key"],
)

app.include_router(v1_router)
app.include_router(public_portal_router)
app.include_router(admin_ui_router)

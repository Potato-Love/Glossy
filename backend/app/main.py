from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    auth,
    contacts,
    documents,
    health,
    history,
    images,
    strategy_preferences,
    term_suggestions,
    terms,
    translations,
    teams,
)
from app.core.config import get_settings
from app.auth import enforce_team_scope
from app.db import database


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await database.connect()
    try:
        yield
    finally:
        await database.disconnect()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Backend API for the Glossy team translation MVP.",
        lifespan=lifespan,
    )

    allow_credentials = settings.cors_origins != ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router, prefix=settings.api_v1_prefix)
    app.include_router(teams.router, prefix=settings.api_v1_prefix)
    protected = [Depends(enforce_team_scope)]
    app.include_router(terms.router, prefix=settings.api_v1_prefix, dependencies=protected)
    app.include_router(term_suggestions.router, prefix=settings.api_v1_prefix, dependencies=protected)
    app.include_router(contacts.router, prefix=settings.api_v1_prefix, dependencies=protected)
    app.include_router(history.router, prefix=settings.api_v1_prefix, dependencies=protected)
    app.include_router(translations.router, prefix=settings.api_v1_prefix, dependencies=protected)
    app.include_router(documents.router, prefix=settings.api_v1_prefix, dependencies=protected)
    app.include_router(images.router, prefix=settings.api_v1_prefix, dependencies=protected)
    app.include_router(strategy_preferences.router, prefix=settings.api_v1_prefix, dependencies=protected)
    app.include_router(strategy_preferences.preview_router, prefix=settings.api_v1_prefix, dependencies=protected)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "health": "/health",
            "docs": "/docs",
        }

    return app


app = create_app()

"""FastAPI application for AFGA."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import get_settings
from ..core.logging_config import setup_logging
from ..core.observability import Observability
from .routes import router


# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    logger.info("Starting Adaptive Finance Governance Agent (AFGA)")
    logger.info("Initializing agents and services...")
    yield
    # Shutdown
    logger.info("Shutting down AFGA")
    # Flush Langfuse events if configured
    settings = get_settings()
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        try:
            obs = Observability()
            obs.flush()
            logger.info("Langfuse events flushed on shutdown")
        except Exception as e:
            logger.warning(f"Failed to flush Langfuse on shutdown: {e}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Adaptive Finance Governance Agent (AFGA)",
        version="0.1.0",
        description=(
            "Multi-agent AI system for automated finance compliance with adaptive learning. "
            "Features TAA, PAA, and EMA agents communicating via A2A/MCP protocol."
        ),
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict to specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(router, prefix="/api/v1")

    return app


app = create_app()


# Root endpoint
@app.get("/")
def read_root():
    """Root endpoint with API information."""
    return {
        "name": "Adaptive Finance Governance Agent (AFGA)",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": "/api/v1/health",
            "transactions": "/api/v1/transactions",
            "kpis": "/api/v1/kpis",
            "memory": "/api/v1/memory",
        }
    }


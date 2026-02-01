"""Main FastAPI application for Multi-Agent Collaboration Platform."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .config import settings
from .db.database import init_db
from .personas.loader import get_persona_loader
from .api.routes import sessions, personas, analytics, config
from .api.websocket import chat_handler

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Multi-Agent Collaboration Platform...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Load personas
    loader = get_persona_loader()
    personas_count = len(loader.load_all())
    domains_count = len(loader.get_all_domains())
    logger.info(f"Loaded {personas_count} personas across {domains_count} domains")

    yield

    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Multi-Agent Collaboration Platform",
    description="A platform for collaborative AI agent discussions with 265 expert personas",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include routers
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(personas.router, prefix="/api/personas", tags=["personas"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(config.router, prefix="/api/config", tags=["config"])

# WebSocket endpoint
app.include_router(chat_handler.router, prefix="/ws", tags=["websocket"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Multi-Agent Collaboration Platform",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    loader = get_persona_loader()
    return {
        "status": "healthy",
        "personas_loaded": len(loader.get_all_personas()),
        "domains_available": len(loader.get_all_domains()),
    }


def start():
    """Start the server."""
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    start()

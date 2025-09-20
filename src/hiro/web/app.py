"""FastAPI application for hiro web interface."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from hiro.core.config.settings import get_settings
from hiro.db import auto_migrate_database
from hiro.web.routers import api, missions, targets

logger = logging.getLogger(__name__)

# Get paths
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Manage application lifecycle."""
    logger.info("Starting hiro web interface...")

    # Auto-migrate database if configured
    try:
        settings = get_settings()
        if settings.database.url:
            logger.info("Checking database schema...")
            success = await auto_migrate_database(settings.database)
            if not success:
                logger.warning("Database auto-migration failed, but continuing startup")
        else:
            logger.info("Database not configured, skipping auto-migration")
    except Exception as e:
        logger.warning(f"Database auto-migration error: {e}, continuing startup")

    yield
    logger.info("Shutting down hiro web interface...")


# Create FastAPI app
app = FastAPI(
    title="Hiro Web Interface",
    description="Web UI for managing targets and viewing HTTP requests",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware for API access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001", "http://127.0.0.1:8001"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "HX-Request", "HX-Trigger"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Setup templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Include routers
app.include_router(targets.router, prefix="/targets", tags=["targets"])
app.include_router(missions.router, prefix="/missions", tags=["missions"])
app.include_router(api.router, prefix="/api", tags=["api"])


@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect to targets dashboard."""
    return HTMLResponse(content='<meta http-equiv="refresh" content="0; url=/targets">')


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "hiro-web"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

"""API endpoints for HTMX interactions."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from hiro.db.database import get_db
from hiro.db.models import RiskLevel, TargetStatus
from hiro.web.services.target_service import TargetService

router = APIRouter()


class TargetUpdate(BaseModel):
    """Target update request."""

    status: TargetStatus | None = None
    risk_level: RiskLevel | None = None
    title: str | None = Field(None, max_length=255)
    port: int | None = Field(None, ge=1, le=65535)


class ContextUpdate(BaseModel):
    """Context update request."""

    user_context: str | None = Field(None, max_length=10000)
    agent_context: str | None = Field(None, max_length=10000)


@router.get("/targets")
async def list_targets(
    request: Request,
    status: TargetStatus | None = None,
    risk: RiskLevel | None = None,
    search: str | None = Query(None, max_length=100),
    format: str | None = Query(None, pattern="^(json|html)$"),
    db: AsyncSession = Depends(get_db),
):
    """Get targets list as JSON or HTML."""
    service = TargetService(db)
    targets = await service.list_targets(status=status, risk=risk, search=search)

    # Return HTML if requested (for HTMX)
    if format == "html":
        from pathlib import Path

        from fastapi.templating import Jinja2Templates

        templates_dir = Path(__file__).parent.parent / "templates"
        templates = Jinja2Templates(directory=str(templates_dir))
        return templates.TemplateResponse(
            request=request,
            name="components/target_list.html",
            context={"targets": targets},
        )

    return {"targets": targets}


@router.get("/targets/{target_id}")
async def get_target(target_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get target details."""
    service = TargetService(db)
    target = await service.get_target(target_id)

    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    return target


@router.patch("/targets/{target_id}")
async def update_target(
    target_id: UUID,
    update: TargetUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Update target attributes."""
    service = TargetService(db)
    target = await service.update_target(
        target_id, update.model_dump(exclude_unset=True)
    )

    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    # Check if request wants HTML response (from HTMX)
    if request.headers.get("HX-Request"):
        from pathlib import Path

        from fastapi.templating import Jinja2Templates

        templates_dir = Path(__file__).parent.parent / "templates"
        templates = Jinja2Templates(directory=str(templates_dir))

        # Determine which template to return based on the context
        referrer = request.headers.get("Referer", "")
        if "/targets/" in referrer and referrer.count("/") >= 4:
            # This is from the target detail page
            return templates.TemplateResponse(
                request=request,
                name="components/target_header.html",
                context={"target": target},
            )
        else:
            # This is from the target list page
            return templates.TemplateResponse(
                request=request,
                name="components/target_card.html",
                context={"target": target},
            )

    return target


@router.post("/targets/{target_id}/context")
async def update_context(
    target_id: UUID, update: ContextUpdate, db: AsyncSession = Depends(get_db)
):
    """Update target context."""
    service = TargetService(db)
    context = await service.update_context(
        target_id,
        user_context=update.user_context,
        agent_context=update.agent_context,
    )

    if not context:
        raise HTTPException(status_code=404, detail="Target not found")

    return {"success": True, "version": context.version}


@router.get("/targets/{target_id}/requests")
async def get_target_requests(
    target_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Get HTTP requests for a target."""
    service = TargetService(db)
    requests = await service.get_target_requests(target_id, limit=limit)
    return {"requests": requests}


@router.get("/targets/{target_id}/context/history")
async def get_context_history(
    target_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get context version history for a target."""
    service = TargetService(db)
    history = await service.get_context_history(target_id)

    # Convert to a simple format for JSON response
    history_data = [
        {
            "version": ctx.version,
            "created_at": ctx.created_at.isoformat(),
            "created_by": ctx.created_by,
            "change_type": ctx.change_type if ctx.change_type else None,
            "change_summary": ctx.change_summary,
            "is_major_version": ctx.is_major_version,
            "tokens_count": ctx.tokens_count,
        }
        for ctx in history
    ]

    return {"history": history_data}


@router.get("/targets/{target_id}/context/{version}")
async def get_context_version(
    target_id: UUID,
    version: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific context version for a target."""
    service = TargetService(db)
    context = await service.get_context_by_version(target_id, version)

    if not context:
        raise HTTPException(status_code=404, detail="Context version not found")

    return {
        "version": context.version,
        "user_context": context.user_context,
        "agent_context": context.agent_context,
        "created_at": context.created_at.isoformat(),
        "created_by": context.created_by,
        "change_type": context.change_type if context.change_type else None,
        "change_summary": context.change_summary,
        "is_major_version": context.is_major_version,
        "tokens_count": context.tokens_count,
    }

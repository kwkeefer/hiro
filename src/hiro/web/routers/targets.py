"""Target management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from hiro.db.database import get_db
from hiro.db.models import RiskLevel, TargetStatus
from hiro.web.services.target_service import TargetService

router = APIRouter()
templates = Jinja2Templates(directory="src/hiro/web/templates")


@router.get("/", response_class=HTMLResponse)
async def list_targets(
    request: Request,
    status: TargetStatus | None = None,
    risk: RiskLevel | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Display target dashboard."""
    service = TargetService(db)
    targets = await service.list_targets(status=status, risk=risk, search=search)

    return templates.TemplateResponse(
        request=request,
        name="targets.html",
        context={
            "targets": targets,
            "current_status": status,
            "current_risk": risk,
            "search_query": search,
        },
    )


@router.get("/{target_id}", response_class=HTMLResponse)
async def view_target(
    request: Request,
    target_id: UUID,
    tab: str = "overview",
    db: AsyncSession = Depends(get_db),
):
    """Display target detail view."""
    service = TargetService(db)
    target = await service.get_target(target_id)

    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    # Get related data based on tab
    context = None
    requests = []

    if tab == "context":
        context = await service.get_target_context(target_id)
    elif tab == "requests":
        requests = await service.get_target_requests(target_id)

    return templates.TemplateResponse(
        request=request,
        name="target.html",
        context={
            "target": target,
            "current_tab": tab,
            "context": context,
            "requests": requests,
        },
    )

"""Mission management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from hiro.db.database import get_db
from hiro.db.models import SessionStatus
from hiro.db.repositories import (
    MissionRepository,
    TargetRepository,
)
from hiro.db.schemas import MissionActionCreate, MissionCreate
from hiro.web.services.mission_service import MissionService

router = APIRouter()
templates = Jinja2Templates(directory="src/hiro/web/templates")


@router.get("/", response_class=HTMLResponse)
async def list_missions(
    request: Request,
    mission_type: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Display mission dashboard."""
    service = MissionService(db)
    missions = await service.list_missions(mission_type=mission_type, search=search)

    return templates.TemplateResponse(
        request=request,
        name="missions/list.html",
        context={
            "missions": missions,
            "current_type": mission_type,
            "search_query": search,
        },
    )


@router.get("/create", response_class=HTMLResponse)
async def create_mission_form(
    request: Request,
    target_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Display mission creation form."""
    target_repo = TargetRepository(db)
    targets = await target_repo.list_all()

    # If target_id provided, pre-select it
    selected_target = None
    if target_id:
        for target in targets:
            if target.id == target_id:
                selected_target = target
                break

    return templates.TemplateResponse(
        request=request,
        name="missions/create.html",
        context={
            "targets": targets,
            "selected_target": selected_target,
        },
    )


@router.post("/create")
async def create_mission(
    target_id: UUID = Form(...),
    name: str = Form(...),
    mission_type: str = Form("general"),
    goal: str = Form(...),
    hypothesis: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Create a new mission."""
    try:
        service = MissionService(db)

        mission_data = MissionCreate(
            target_id=target_id,
            name=name,
            description=goal,
            mission_type=mission_type,
            goal=goal,
            hypothesis=hypothesis,
            status=SessionStatus.ACTIVE,
        )

        mission = await service.create_mission(mission_data)
        await db.commit()

        return RedirectResponse(
            url=f"/missions/{mission.id}",
            status_code=303,  # See Other - proper redirect after POST
        )
    except Exception as e:
        # Log the error for debugging
        import traceback

        print(f"Error creating mission: {str(e)}")
        print(traceback.format_exc())
        raise


@router.get("/{mission_id}", response_class=HTMLResponse)
async def view_mission(
    request: Request,
    mission_id: UUID,
    tab: str = "overview",
    db: AsyncSession = Depends(get_db),
):
    """Display mission detail view."""
    service = MissionService(db)

    try:
        mission = await service.get_mission_detail(mission_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Mission not found") from e

    # Get associated data based on tab
    context = {
        "mission": mission,
        "tab": tab,
    }

    if tab == "actions":
        actions = await service.get_mission_actions(mission_id)
        context["actions"] = actions
    elif tab == "requests":
        requests = await service.get_mission_requests(mission_id)
        context["requests"] = requests
    elif tab == "patterns":
        patterns = await service.get_success_patterns(mission_id)
        context["patterns"] = patterns

    return templates.TemplateResponse(
        request=request,
        name="missions/detail.html",
        context=context,
    )


@router.get("/{mission_id}/record-action", response_class=HTMLResponse)
async def record_action_form(
    request: Request,
    mission_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Display action recording form."""
    mission_repo = MissionRepository(db)
    mission = await mission_repo.get(mission_id)

    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    return templates.TemplateResponse(
        request=request,
        name="missions/record_action.html",
        context={
            "mission": mission,
        },
    )


@router.post("/{mission_id}/record-action")
async def record_action(
    mission_id: UUID,
    action_type: str = Form(...),
    technique: str = Form(...),
    payload: str | None = Form(None),
    result: str | None = Form(None),
    success: bool = Form(False),
    learning: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Record a new action for the mission."""
    service = MissionService(db)

    action_data = MissionActionCreate(
        mission_id=mission_id,
        action_type=action_type,
        technique=technique,
        payload=payload,
        result=result,
        success=success,
        learning=learning,
        metadata=None,
    )

    await service.record_action(action_data)
    await db.commit()

    return RedirectResponse(
        url=f"/missions/{mission_id}?tab=actions",
        status_code=303,
    )


@router.post("/{mission_id}/complete")
async def complete_mission(
    mission_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Mark mission as completed."""
    service = MissionService(db)
    await service.complete_mission(mission_id)
    await db.commit()

    return RedirectResponse(
        url=f"/missions/{mission_id}",
        status_code=303,
    )


@router.delete("/{mission_id}")
async def delete_mission(
    mission_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a mission."""
    service = MissionService(db)
    await service.delete_mission(mission_id)
    await db.commit()

    return {"status": "deleted"}

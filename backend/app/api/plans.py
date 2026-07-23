from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import Settings, get_settings
from app.models.plan import Plan
from app.models.user import User
from app.schemas.plan import PlanCreate, PlanGenerate, PlanSummary
from app.services.ai_client import AiProviderError, OpenAICompatibleClient
from app.services.ai_context import build_bounded_ai_context_data
from app.services.plan_service import AiPlanGenerator, DeterministicPlanGenerator, PlanGenerator, PlanService

router = APIRouter(prefix="/api/plans", tags=["plans"])


def get_plan_generator(settings: Settings = Depends(get_settings)) -> PlanGenerator:
    if settings.ai_base_url and settings.ai_api_key and settings.ai_model:
        return AiPlanGenerator(ai_client=OpenAICompatibleClient(settings=settings, timeout_seconds=10.0))
    return DeterministicPlanGenerator()


def _response(plan: Plan) -> PlanSummary:
    return PlanSummary.from_orm_plan(plan)


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")


@router.post("", response_model=PlanSummary, status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: PlanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlanSummary:
    return _response(PlanService().create_plan(db, user_id=current_user.id, payload=payload))


@router.post("/generate", response_model=PlanSummary, status_code=status.HTTP_201_CREATED)
def generate_plan(
    payload: PlanGenerate,
    generator: PlanGenerator = Depends(get_plan_generator),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlanSummary:
    context = build_bounded_ai_context_data(
        db,
        user_id=current_user.id,
        message="Generate a safe 7-day fitness and nutrition plan",
        today=payload.start_date,
    )
    try:
        plan = PlanService(generator=generator).generate_plan(
            db,
            user_id=current_user.id,
            start_date=payload.start_date,
            title=payload.title,
            context=context,
        )
    except AiProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="AI provider is unavailable"
        ) from exc
    return _response(plan)


@router.get("/current", response_model=PlanSummary)
def get_current_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlanSummary:
    plan = PlanService().get_current_plan(db, user_id=current_user.id)
    if plan is None:
        raise _not_found()
    return _response(plan)


@router.post("/{plan_id}/days/{day}/postpone", response_model=PlanSummary)
def postpone_plan_day(
    plan_id: int,
    day: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlanSummary:
    try:
        plan = PlanService().postpone_training(db, user_id=current_user.id, plan_id=plan_id, day=day)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if plan is None:
        raise _not_found()
    return _response(plan)


@router.get("/{plan_id}", response_model=PlanSummary)
def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlanSummary:
    plan = PlanService().get_plan(db, user_id=current_user.id, plan_id=plan_id)
    if plan is None:
        raise _not_found()
    return _response(plan)


@router.post("/{plan_id}/activate", response_model=PlanSummary)
def activate_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlanSummary:
    plan = PlanService().activate_plan(db, user_id=current_user.id, plan_id=plan_id)
    if plan is None:
        raise _not_found()
    return _response(plan)


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.goal import Goal
from app.models.profile import Profile
from app.models.record import BodyMetric
from app.models.user import User
from app.api.time_utils import get_user_timezone, to_utc_naive, utc_naive_to_timezone
from app.schemas.profile import (
    BodyMetricCreate,
    BodyMetricResponse,
    GoalResponse,
    GoalUpsert,
    ProfileResponse,
    ProfileUpsert,
)

router = APIRouter(tags=["profile"])


def _body_metric_response(metric: BodyMetric, user_timezone) -> BodyMetricResponse:
    return BodyMetricResponse(
        id=metric.id,
        user_id=metric.user_id,
        weight_kg=metric.weight_kg,
        body_fat_percent=metric.body_fat_percent,
        waist_cm=metric.waist_cm,
        chest_cm=metric.chest_cm,
        hip_cm=metric.hip_cm,
        notes=metric.notes,
        logged_at=utc_naive_to_timezone(metric.logged_at, user_timezone),
        created_at=utc_naive_to_timezone(metric.created_at, user_timezone),
        updated_at=utc_naive_to_timezone(metric.updated_at, user_timezone),
    )



@router.get("/api/profile", response_model=ProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    profile = db.scalar(select(Profile).where(Profile.user_id == current_user.id))
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@router.put("/api/profile", response_model=ProfileResponse)
def upsert_profile(
    payload: ProfileUpsert,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Profile:
    profile = db.scalar(select(Profile).where(Profile.user_id == current_user.id))
    values = payload.model_dump()
    if profile is None:
        profile = Profile(user_id=current_user.id, **values)
        db.add(profile)
    else:
        for field, value in values.items():
            setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile


@router.put("/api/profile/goal", response_model=GoalResponse)
def upsert_active_goal(
    payload: GoalUpsert,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Goal:
    active_goals = list(
        db.scalars(
            select(Goal)
            .where(Goal.user_id == current_user.id, Goal.is_active.is_(True))
            .order_by(Goal.updated_at.desc(), Goal.id.desc())
        )
    )
    active_goal = active_goals[0] if active_goals else None
    values = payload.model_dump()
    if active_goal is None:
        active_goal = Goal(user_id=current_user.id, is_active=True, **values)
        db.add(active_goal)
    else:
        for field, value in values.items():
            setattr(active_goal, field, value)
        active_goal.is_active = True

    for stale_goal in active_goals[1:]:
        stale_goal.is_active = False

    db.commit()
    db.refresh(active_goal)
    return active_goal


@router.post(
    "/api/body-metrics",
    response_model=BodyMetricResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_body_metric(
    payload: BodyMetricCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BodyMetricResponse:
    user_timezone = get_user_timezone(db, current_user.id)
    metric = BodyMetric(
        user_id=current_user.id,
        **{**payload.model_dump(), "logged_at": to_utc_naive(payload.logged_at)},
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return _body_metric_response(metric, user_timezone)


@router.get("/api/body-metrics", response_model=list[BodyMetricResponse])
def list_body_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BodyMetricResponse]:
    user_timezone = get_user_timezone(db, current_user.id)
    metrics = list(
        db.scalars(
            select(BodyMetric)
            .where(BodyMetric.user_id == current_user.id)
            .order_by(BodyMetric.logged_at.desc(), BodyMetric.id.desc())
        )
    )
    return [_body_metric_response(metric, user_timezone) for metric in metrics]

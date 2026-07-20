from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.goal import Goal
from app.models.profile import Profile
from app.models.record import BodyMetric
from app.models.user import User
from app.schemas.profile import (
    BodyMetricCreate,
    BodyMetricResponse,
    GoalResponse,
    GoalUpsert,
    ProfileResponse,
    ProfileUpsert,
)

router = APIRouter(tags=["profile"])


def to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


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
    active_goal = db.scalar(
        select(Goal).where(Goal.user_id == current_user.id, Goal.is_active.is_(True)).limit(1)
    )
    values = payload.model_dump()
    if active_goal is None:
        active_goal = Goal(user_id=current_user.id, is_active=True, **values)
        db.add(active_goal)
    else:
        for field, value in values.items():
            setattr(active_goal, field, value)
        active_goal.is_active = True

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
) -> BodyMetric:
    metric = BodyMetric(
        user_id=current_user.id,
        **{**payload.model_dump(), "logged_at": to_utc_naive(payload.logged_at)},
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


@router.get("/api/body-metrics", response_model=list[BodyMetricResponse])
def list_body_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BodyMetric]:
    return list(
        db.scalars(
            select(BodyMetric)
            .where(BodyMetric.user_id == current_user.id)
            .order_by(BodyMetric.logged_at.desc(), BodyMetric.id.desc())
        )
    )

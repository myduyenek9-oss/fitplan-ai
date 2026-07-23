from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.time_utils import get_user_timezone, to_utc_storage, utc_storage_to_timezone
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


def _profile_timezone(profile: Profile) -> ZoneInfo:
    if profile.timezone is None:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(profile.timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _profile_response(profile: Profile) -> ProfileResponse:
    user_timezone = _profile_timezone(profile)
    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        sex=profile.sex,
        birth_date=profile.birth_date,
        height_cm=profile.height_cm,
        timezone=profile.timezone,
        created_at=utc_storage_to_timezone(profile.created_at, user_timezone),
        updated_at=utc_storage_to_timezone(profile.updated_at, user_timezone),
    )


def _goal_response(goal: Goal, user_timezone: ZoneInfo) -> GoalResponse:
    return GoalResponse(
        id=goal.id,
        user_id=goal.user_id,
        goal_type=goal.goal_type,
        daily_calories=goal.daily_calories,
        protein_g=goal.protein_g,
        carb_g=goal.carb_g,
        fat_g=goal.fat_g,
        activity_level=goal.activity_level,
        target_weight_kg=goal.target_weight_kg,
        target_date=goal.target_date,
        is_active=goal.is_active,
        created_at=utc_storage_to_timezone(goal.created_at, user_timezone),
        updated_at=utc_storage_to_timezone(goal.updated_at, user_timezone),
    )


def _body_metric_response(metric: BodyMetric, user_timezone: ZoneInfo) -> BodyMetricResponse:
    return BodyMetricResponse(
        id=metric.id,
        user_id=metric.user_id,
        weight_kg=metric.weight_kg,
        body_fat_percent=metric.body_fat_percent,
        waist_cm=metric.waist_cm,
        chest_cm=metric.chest_cm,
        hip_cm=metric.hip_cm,
        notes=metric.notes,
        logged_at=utc_storage_to_timezone(metric.logged_at, user_timezone),
        created_at=utc_storage_to_timezone(metric.created_at, user_timezone),
        updated_at=utc_storage_to_timezone(metric.updated_at, user_timezone),
    )



@router.get("/api/profile", response_model=ProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    profile = db.scalar(select(Profile).where(Profile.user_id == current_user.id))
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return _profile_response(profile)


@router.put("/api/profile", response_model=ProfileResponse)
def upsert_profile(
    payload: ProfileUpsert,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
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
    return _profile_response(profile)


@router.get("/api/profile/goal", response_model=GoalResponse)
def get_active_goal(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalResponse:
    active_goal = db.scalar(
        select(Goal)
        .where(Goal.user_id == current_user.id, Goal.is_active.is_(True))
        .order_by(Goal.updated_at.desc(), Goal.id.desc())
        .limit(1)
    )
    if active_goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active goal not found")
    return _goal_response(active_goal, get_user_timezone(db, current_user.id))


@router.put("/api/profile/goal", response_model=GoalResponse)
def upsert_active_goal(
    payload: GoalUpsert,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalResponse:
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
    user_timezone = get_user_timezone(db, current_user.id)
    return _goal_response(active_goal, user_timezone)


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
        **{**payload.model_dump(), "logged_at": to_utc_storage(payload.logged_at)},
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

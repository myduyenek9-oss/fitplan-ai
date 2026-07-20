from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.plan import Plan, PlanDay
from app.models.user import User
from app.schemas.plan import MealPlan, PlanCreate, PlanDayCreate, WorkoutPlan
from app.services.plan_service import DeterministicPlanGenerator, PlanService


def _session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return TestingSessionLocal()


def _user(db):
    user = User(id=1, username="owner", password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _days(start: date, calorie_target: float = 1800) -> list[PlanDayCreate]:
    return [
        PlanDayCreate(
            date=start + timedelta(days=offset),
            calorie_target=calorie_target + offset,
            meals=[
                MealPlan(
                    name=f"Day {offset + 1} breakfast",
                    meal_type="breakfast",
                    calories=500,
                    protein_g=30,
                    carb_g=55,
                    fat_g=12,
                )
            ],
            training_instruction=WorkoutPlan(
                kind="workout" if offset % 2 == 0 else "rest",
                title="Strength" if offset % 2 == 0 else "Rest day",
                instructions="Do the scheduled session" if offset % 2 == 0 else "Recover and walk lightly",
                duration_minutes=45 if offset % 2 == 0 else None,
            ),
        )
        for offset in range(7)
    ]


def test_generated_plan_has_exactly_seven_consecutive_dated_days_with_required_content():
    db = _session()
    user = _user(db)
    service = PlanService(generator=DeterministicPlanGenerator())

    plan = service.generate_plan(db, user_id=user.id, start_date=date(2026, 7, 20))

    assert plan.is_active is True
    assert len(plan.days) == 7
    assert [day.date for day in plan.days] == [date(2026, 7, 20) + timedelta(days=i) for i in range(7)]
    for day in plan.days:
        assert day.calorie_target > 0
        assert len(day.meals) >= 1
        assert day.training_instruction.instructions
        assert day.training_instruction.kind in {"workout", "rest"}


def test_creating_new_plan_activates_it_and_preserves_readable_inactive_history():
    db = _session()
    user = _user(db)
    service = PlanService(generator=DeterministicPlanGenerator())

    first = service.create_plan(
        db,
        user_id=user.id,
        payload=PlanCreate(title="First", days=_days(date(2026, 7, 20))),
    )
    second = service.create_plan(
        db,
        user_id=user.id,
        payload=PlanCreate(title="Second", days=_days(date(2026, 7, 27), 1900)),
    )

    assert second.is_active is True
    assert service.get_current_plan(db, user_id=user.id).id == second.id

    stored_first = service.get_plan(db, user_id=user.id, plan_id=first.id)
    assert stored_first is not None
    assert stored_first.is_active is False
    assert len(stored_first.days) == 7

    all_plans = list(db.scalars(select(Plan).where(Plan.user_id == user.id)))
    assert {plan.id for plan in all_plans} == {first.id, second.id}
    assert db.scalar(select(PlanDay).where(PlanDay.plan_id == first.id)) is not None


def test_activate_plan_deactivates_previous_plan_and_enforces_user_scope():
    db = _session()
    user = _user(db)
    service = PlanService(generator=DeterministicPlanGenerator())

    first = service.create_plan(
        db,
        user_id=user.id,
        payload=PlanCreate(title="First", days=_days(date(2026, 7, 20))),
    )
    second = service.create_plan(
        db,
        user_id=user.id,
        payload=PlanCreate(title="Second", days=_days(date(2026, 7, 27))),
    )

    reactivated = service.activate_plan(db, user_id=user.id, plan_id=first.id)

    assert reactivated is not None
    assert reactivated.id == first.id
    assert service.get_plan(db, user_id=user.id, plan_id=first.id).is_active is True
    assert service.get_plan(db, user_id=user.id, plan_id=second.id).is_active is False
    assert service.get_plan(db, user_id=user.id, plan_id=999999) is None


@pytest.mark.parametrize(
    "days",
    [
        _days(date(2026, 7, 20))[:6],
        _days(date(2026, 7, 20)) + [_days(date(2026, 8, 1))[0]],
        [*_days(date(2026, 7, 20))[:3], *_days(date(2026, 7, 20))[4:]],
    ],
)
def test_plan_create_validates_exactly_seven_consecutive_days(days):
    with pytest.raises(ValueError):
        PlanCreate(title="Invalid", days=days)

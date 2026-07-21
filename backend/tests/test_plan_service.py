from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import PlanConflictError
from app.db.base import Base
from app.models.plan import Plan, PlanDay
from app.models.user import User
from app.schemas.plan import MealPlan, PlanCreate, PlanDay as PlanDaySchema, PlanDayCreate, WorkoutPlan
from sqlalchemy.exc import IntegrityError

import app.db.session  # noqa: F401 - registers SQLite connection hooks
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


@pytest.mark.parametrize("value", ["Infinity", "NaN"])
def test_plan_float_schemas_reject_non_finite_values(value):
    with pytest.raises(ValueError):
        MealPlan(
            name="Meal",
            calories=value,
            protein_g=30,
            carb_g=50,
            fat_g=10,
        )
    with pytest.raises(ValueError):
        WorkoutPlan(
            kind="workout",
            title="Workout",
            instructions="Train",
            duration_minutes=value,
        )
    with pytest.raises(ValueError):
        PlanDaySchema(
            date=date(2026, 7, 20),
            calorie_target=value,
            meals=[MealPlan(name="Meal", calories=500, protein_g=30, carb_g=50, fat_g=10)],
            training_instruction=WorkoutPlan(
                kind="workout", title="Workout", instructions="Train", duration_minutes=30
            ),
        )


def test_create_plan_conflict_rolls_back_and_preserves_previous_active_plan(monkeypatch):
    db = _session()
    user = _user(db)
    service = PlanService(generator=DeterministicPlanGenerator())
    first = service.create_plan(
        db,
        user_id=user.id,
        payload=PlanCreate(title="First", days=_days(date(2026, 7, 20))),
    )

    def fail_commit():
        raise IntegrityError(
            "active plan conflict",
            {},
            Exception("UNIQUE constraint failed: plans.user_id"),
        )

    monkeypatch.setattr(db, "commit", fail_commit)
    with pytest.raises(PlanConflictError):
        service.create_plan(
            db,
            user_id=user.id,
            payload=PlanCreate(title="Second", days=_days(date(2026, 7, 27))),
        )

    monkeypatch.undo()
    current = service.get_current_plan(db, user_id=user.id)
    assert current is not None
    assert current.id == first.id
    assert current.is_active is True


def test_sqlite_foreign_keys_are_enabled_and_plan_rows_cascade_with_user_delete():
    db = _session()
    user = _user(db)
    service = PlanService(generator=DeterministicPlanGenerator())
    plan = service.create_plan(
        db,
        user_id=user.id,
        payload=PlanCreate(title="First", days=_days(date(2026, 7, 20))),
    )

    assert db.scalar(text("PRAGMA foreign_keys")) == 1
    plan_id = plan.id
    db.delete(user)
    db.commit()

    assert db.get(Plan, plan_id) is None
    assert db.scalar(select(PlanDay.id).where(PlanDay.plan_id == plan_id)) is None


def test_activate_plan_conflict_rolls_back_and_preserves_current_active_plan(monkeypatch):
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

    def fail_commit():
        raise IntegrityError(
            "active plan conflict",
            {},
            Exception("UNIQUE constraint failed: plans.user_id"),
        )

    monkeypatch.setattr(db, "commit", fail_commit)
    with pytest.raises(PlanConflictError):
        service.activate_plan(db, user_id=user.id, plan_id=first.id)

    monkeypatch.undo()
    assert service.get_plan(db, user_id=user.id, plan_id=first.id).is_active is False
    assert service.get_plan(db, user_id=user.id, plan_id=second.id).is_active is True

def test_postgresql_active_plan_constraint_name_is_recognized():
    original = SimpleNamespace(
        diag=SimpleNamespace(constraint_name="uq_plans_one_active_per_user")
    )
    error = IntegrityError("duplicate key value", {}, original)

    assert PlanService._is_active_plan_conflict(error) is True


def test_create_plan_non_active_integrity_error_is_not_mapped_to_plan_conflict(monkeypatch):
    db = _session()
    user = _user(db)
    service = PlanService(generator=DeterministicPlanGenerator())

    service.create_plan(
        db,
        user_id=user.id,
        payload=PlanCreate(title="First", days=_days(date(2026, 7, 20))),
    )

    def fail_commit():
        raise IntegrityError(
            "plan day conflict",
            {},
            Exception("UNIQUE constraint failed: plan_days.plan_id, plan_days.date"),
        )

    monkeypatch.setattr(db, "commit", fail_commit)
    with pytest.raises(IntegrityError):
        service.create_plan(
            db,
            user_id=user.id,
            payload=PlanCreate(title="Second", days=_days(date(2026, 7, 27))),
        )


def test_activate_plan_non_active_integrity_error_is_not_mapped_to_plan_conflict(monkeypatch):
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

    def fail_commit():
        raise IntegrityError(
            "plan day conflict",
            {},
            Exception("UNIQUE constraint failed: plan_days.plan_id, plan_days.date"),
        )

    monkeypatch.setattr(db, "commit", fail_commit)
    with pytest.raises(IntegrityError):
        service.activate_plan(db, user_id=user.id, plan_id=first.id)

    monkeypatch.undo()
    assert service.get_plan(db, user_id=user.id, plan_id=first.id).is_active is False
    assert service.get_plan(db, user_id=user.id, plan_id=second.id).is_active is True

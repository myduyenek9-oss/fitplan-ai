from datetime import date, timedelta
from abc import ABC, abstractmethod

from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import PlanConflictError, PlanIntegrityError
from app.models.plan import Plan, PlanDay
from app.schemas.plan import PlanCreate, PlanDay as PlanDaySchema


class PlanGenerator(ABC):
    @abstractmethod
    def generate(self, *, start_date: date) -> list[PlanDaySchema]:
        """Generate a validated seven-day plan starting on start_date."""


class DeterministicPlanGenerator(PlanGenerator):
    def generate(self, *, start_date: date) -> list[PlanDaySchema]:
        days: list[PlanDaySchema] = []
        for offset in range(7):
            day_date = start_date + timedelta(days=offset)
            is_rest = offset == 6
            days.append(
                PlanDaySchema(
                    date=day_date,
                    calorie_target=1800 + (offset % 3) * 50,
                    meals=[
                        {
                            "name": f"Balanced meal {offset + 1}",
                            "meal_type": "lunch",
                            "calories": 600,
                            "protein_g": 35,
                            "carb_g": 65,
                            "fat_g": 18,
                        }
                    ],
                    training_instruction={
                        "kind": "rest" if is_rest else "workout",
                        "title": "Recovery day" if is_rest else "Full-body strength",
                        "instructions": "Rest, stretch, and take an easy walk" if is_rest else "Complete a moderate strength session",
                        "duration_minutes": None if is_rest else 40,
                    },
                )
            )
        return days


class PlanService:
    _ACTIVE_PLAN_CONSTRAINT = "uq_plans_one_active_per_user"
    _SQLITE_ACTIVE_PLAN_UNIQUE_MESSAGE = "unique constraint failed: plans.user_id"

    def __init__(self, generator: PlanGenerator | None = None) -> None:
        self.generator = generator or DeterministicPlanGenerator()

    def create_plan(self, db: Session, *, user_id: int, payload: PlanCreate) -> Plan:
        validated_payload = self._validate_payload(payload)
        plan = Plan(
            user_id=user_id,
            title=validated_payload.title,
            start_date=validated_payload.days[0].date,
            end_date=validated_payload.days[-1].date,
            is_active=True,
            days=[
                PlanDay(
                    date=day.date,
                    calorie_target=day.calorie_target,
                    meals_json=[meal.model_dump(mode="json") for meal in day.meals],
                    training_instruction_json=day.training_instruction.model_dump(mode="json"),
                )
                for day in validated_payload.days
            ],
        )
        try:
            self._deactivate_user_plans(db, user_id=user_id)
            db.add(plan)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            if self._is_active_plan_conflict(exc):
                raise PlanConflictError from exc
            raise
        return self._load_plan(db, plan.id)

    def generate_plan(self, db: Session, *, user_id: int, start_date: date, title: str = "7-day plan") -> Plan:
        try:
            generated_days = self.generator.generate(start_date=start_date)
            payload = PlanCreate(title=title, days=generated_days)
        except (ValidationError, TypeError, ValueError) as exc:
            raise PlanIntegrityError from exc
        return self.create_plan(db, user_id=user_id, payload=payload)

    def get_current_plan(self, db: Session, *, user_id: int) -> Plan | None:
        return db.scalar(
            select(Plan)
            .options(selectinload(Plan.days))
            .where(Plan.user_id == user_id, Plan.is_active.is_(True))
            .order_by(Plan.updated_at.desc(), Plan.id.desc())
        )

    def get_plan(self, db: Session, *, user_id: int, plan_id: int) -> Plan | None:
        return db.scalar(
            select(Plan)
            .options(selectinload(Plan.days))
            .where(Plan.id == plan_id, Plan.user_id == user_id)
        )

    def activate_plan(self, db: Session, *, user_id: int, plan_id: int) -> Plan | None:
        plan = self.get_plan(db, user_id=user_id, plan_id=plan_id)
        if plan is None:
            return None
        try:
            self._deactivate_user_plans(db, user_id=user_id)
            plan.is_active = True
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            if self._is_active_plan_conflict(exc):
                raise PlanConflictError from exc
            raise
        return self._load_plan(db, plan.id)


    @classmethod
    def _is_active_plan_conflict(cls, exc: IntegrityError) -> bool:
        orig = exc.orig
        diagnostic = getattr(orig, "diag", None)
        constraint_name = getattr(orig, "constraint_name", None) or getattr(
            diagnostic, "constraint_name", None
        )
        if constraint_name == cls._ACTIVE_PLAN_CONSTRAINT:
            return True

        error_text = " ".join(str(value).lower() for value in (exc, orig))
        return (
            cls._ACTIVE_PLAN_CONSTRAINT.lower() in error_text
            or cls._SQLITE_ACTIVE_PLAN_UNIQUE_MESSAGE in error_text
        )

    @staticmethod
    def _validate_payload(payload: PlanCreate) -> PlanCreate:
        try:
            return PlanCreate.model_validate(payload.model_dump(mode="json"))
        except (ValidationError, TypeError, ValueError) as exc:
            raise PlanIntegrityError from exc

    @staticmethod
    def _deactivate_user_plans(db: Session, *, user_id: int) -> None:
        db.execute(
            update(Plan)
            .where(Plan.user_id == user_id, Plan.is_active.is_(True))
            .values(is_active=False)
        )
        db.flush()

    @staticmethod
    def _load_plan(db: Session, plan_id: int) -> Plan:
        return db.scalar(
            select(Plan)
            .options(selectinload(Plan.days))
            .where(Plan.id == plan_id)
        )

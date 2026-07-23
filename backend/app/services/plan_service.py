from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Mapping
import asyncio
import json

from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import PlanConflictError, PlanIntegrityError
from app.models.plan import Plan, PlanDay
from app.schemas.plan import MealPlan, PlanCreate, PlanDay as PlanDaySchema, WorkoutPlan
from app.services.ai_client import AiClient, AiProviderError
from app.services.ai_prompts import PLAN_GENERATION_SYSTEM_PROMPT
from app.services.ai_schemas import PlanGenerationResult


class PlanGenerator(ABC):
    @abstractmethod
    def generate(
        self, *, start_date: date, context: Mapping[str, Any] | None = None
    ) -> list[PlanDaySchema]:
        """Generate a validated seven-day plan starting on start_date."""


class DeterministicPlanGenerator(PlanGenerator):
    def generate(self, *, start_date: date, context: Mapping[str, Any] | None = None) -> list[PlanDaySchema]:
        from app.services.plan_templates import detailed_plan_days

        return detailed_plan_days(start_date, context)


class AiPlanGenerator(PlanGenerator):
    def __init__(self, *, ai_client: AiClient) -> None:
        self.ai_client = ai_client

    def generate(
        self, *, start_date: date, context: Mapping[str, Any] | None = None
    ) -> list[PlanDaySchema]:
        user_prompt = json.dumps(
            {
                "start_date": start_date.isoformat(),
                "days": 7,
                "constraints": [
                    "moderate calorie targets only",
                    "balanced meals",
                    "safe workout or rest instructions",
                ],
                "context": context or {},
            },
            ensure_ascii=False,
        )
        try:
            raw_result = _run_async_chat_json(
                self.ai_client.chat_json(system=PLAN_GENERATION_SYSTEM_PROMPT, user=user_prompt)
            )
            parsed = PlanGenerationResult.model_validate(raw_result)
            _validate_detailed_days(parsed.days)
            return parsed.days
        except (AiProviderError, ValidationError, TypeError, ValueError):
            # An unavailable or malformed provider response should never leave the user without a usable week.
            return DeterministicPlanGenerator().generate(start_date=start_date, context=context)


def _validate_detailed_days(days: list[PlanDaySchema]) -> None:
    if len(days) != 7 or any(len(day.meals) < 4 for day in days):
        raise ValueError("generated plan must contain four meals per day")
    if any(not meal.foods or len(meal.foods) < 3 for day in days for meal in day.meals):
        raise ValueError("generated meals must contain concrete foods")
    if any(
        day.training_instruction.kind == "workout"
        and len(day.training_instruction.exercises) < 5
        for day in days
    ):
        raise ValueError("generated workouts must contain concrete exercises")


def _run_async_chat_json(awaitable):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    if loop.is_running():
        raise RuntimeError("AiPlanGenerator cannot run inside an active event loop")
    return loop.run_until_complete(awaitable)


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

    def generate_plan(
        self,
        db: Session,
        *,
        user_id: int,
        start_date: date,
        title: str = "7-day plan",
        context: Mapping[str, Any] | None = None,
    ) -> Plan:
        try:
            generated_days = self.generator.generate(start_date=start_date, context=context)
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


    def postpone_training(self, db: Session, *, user_id: int, plan_id: int, day: date) -> Plan | None:
        plan = self.get_plan(db, user_id=user_id, plan_id=plan_id)
        if plan is None:
            return None
        ordered_days = sorted(plan.days, key=lambda item: item.date)
        target = next((item for item in ordered_days if item.date == day), None)
        if target is None:
            raise ValueError("plan day not found")
        if target.training_instruction.kind != "workout":
            raise ValueError("only workout days can be postponed")
        recovery_index = next(
            (index for index in range(ordered_days.index(target) + 1, len(ordered_days))
             if ordered_days[index].training_instruction.kind == "rest"),
            None,
        )
        if recovery_index is None:
            raise ValueError("no recovery day available")
        target_index = ordered_days.index(target)
        training_payloads = [item.training_instruction_json for item in ordered_days[target_index:recovery_index]]
        for index in range(recovery_index, target_index, -1):
            ordered_days[index].training_instruction_json = training_payloads[index - target_index - 1]
        target.training_instruction_json = WorkoutPlan(
            kind="rest",
            title="\u8f7b\u6d3b\u52a8\u4e0e\u6062\u590d",
            instructions="\u5b89\u6392\u6b65\u884c\u3001\u8f7b\u677e\u9a91\u8f66\u6216\u745c\u4f3d 20\u201330 \u5206\u949f\u3002",
            duration_minutes=25,
            split="\u6062\u590d\u4e0e\u6d3b\u52a8\u5ea6",
            focus="\u6062\u590d\u4e0b\u80a2\u548c\u80a9\u80cc\uff0c\u4fdd\u6301\u65e5\u5e38\u6d3b\u52a8\u91cf\u3002",
            exercises=[],
            cooldown="\u665a\u95f4\u505a\u9acb\u5c48\u808c\u548c\u80f8\u808c\u62c9\u4f38\u3002",
        ).model_dump(mode="json")
        db.commit()
        return self._load_plan(db, plan.id)


    def replace_meal(
        self,
        db: Session,
        *,
        user_id: int,
        plan_id: int,
        day: date,
        meal_type: str,
        replacement: MealPlan,
    ) -> tuple[Plan, MealPlan] | None:
        """Replace exactly one meal and leave every other plan item untouched."""
        plan = self.get_plan(db, user_id=user_id, plan_id=plan_id)
        if plan is None:
            return None
        target_day = next((item for item in plan.days if item.date == day), None)
        if target_day is None:
            raise ValueError("plan day not found")

        meals = [MealPlan.model_validate(item) for item in target_day.meals_json]
        meal_index = next(
            (index for index, meal in enumerate(meals) if meal.meal_type == meal_type),
            None,
        )
        if meal_index is None:
            raise ValueError("meal not found")
        previous = meals[meal_index]
        replacement = replacement.model_copy(update={"meal_type": meal_type})
        meals[meal_index] = replacement
        target_day.meals_json = [meal.model_dump(mode="json") for meal in meals]
        db.commit()
        return self._load_plan(db, plan.id), previous


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

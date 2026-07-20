"""Calorie preview API routes."""

from fastapi import APIRouter, HTTPException, status

from app.schemas.calorie import CaloriePreviewRequest, CalorieTargets
from app.services.calorie import CalorieCalculationError, calculate_targets

router = APIRouter(prefix="/api/calorie", tags=["calorie"])


@router.post("/preview", response_model=CalorieTargets)
def preview_calorie_targets(payload: CaloriePreviewRequest) -> CalorieTargets:
    try:
        return calculate_targets(
            age=payload.age,
            sex=payload.sex,
            weight_kg=payload.weight_kg,
            height_cm=payload.height_cm,
            activity_level=payload.activity_level,
            goal=payload.goal,
        )
    except CalorieCalculationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

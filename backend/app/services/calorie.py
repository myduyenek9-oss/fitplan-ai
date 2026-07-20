"""Deterministic calorie and macronutrient calculations."""

from math import floor

from app.schemas.calorie import CalorieTargets

ACTIVITY_MULTIPLIERS: dict[str, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

MIN_AGE = 18
MAX_AGE = 100
MIN_HEIGHT_CM = 100.0
MAX_HEIGHT_CM = 230.0
MIN_WEIGHT_KG = 30.0
MAX_WEIGHT_KG = 250.0
FAT_LOSS_DEFICIT_KCAL = 500
FAT_LOSS_MAX_DEFICIT_RATIO = 0.20
MUSCLE_GAIN_SURPLUS_KCAL = 300
MALE_MIN_CALORIES = 1500
FEMALE_MIN_CALORIES = 1200
MAINTENANCE_PROTEIN_G_PER_KG = 1.8
MUSCLE_GAIN_PROTEIN_G_PER_KG = 2.0
FAT_CALORIE_RATIO = 0.25
KCAL_PER_GRAM_PROTEIN = 4
KCAL_PER_GRAM_CARBS = 4
KCAL_PER_GRAM_FAT = 9
UNSAFE_FAT_LOSS_MESSAGE = (
    "当前维持热量低于安全减脂下限，"
    "不建议生成减脂热量目标，"
    "可选择 maintenance 或咨询专业人士"
)


class CalorieCalculationError(ValueError):
    """Raised when calorie targets cannot be generated safely."""


def _round_nearest_int(value: float) -> int:
    return floor(value + 0.5)


def _validate_adult_inputs(age: int, weight_kg: float, height_cm: float) -> None:
    if not MIN_AGE <= age <= MAX_AGE:
        raise CalorieCalculationError(f"age must be between {MIN_AGE} and {MAX_AGE}")
    if not MIN_WEIGHT_KG <= weight_kg <= MAX_WEIGHT_KG:
        raise CalorieCalculationError(
            f"weight_kg must be between {MIN_WEIGHT_KG:g} and {MAX_WEIGHT_KG:g}"
        )
    if not MIN_HEIGHT_CM <= height_cm <= MAX_HEIGHT_CM:
        raise CalorieCalculationError(
            f"height_cm must be between {MIN_HEIGHT_CM:g} and {MAX_HEIGHT_CM:g}"
        )


def calculate_bmr(age: int, sex: str, weight_kg: float, height_cm: float) -> int:
    """Calculate BMR with the Mifflin-St Jeor equation."""
    _validate_adult_inputs(age=age, weight_kg=weight_kg, height_cm=height_cm)

    normalized_sex = sex.strip().lower()
    if normalized_sex == "male":
        sex_adjustment = 5
    elif normalized_sex == "female":
        sex_adjustment = -161
    else:
        raise CalorieCalculationError("sex must be one of: male, female")

    bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + sex_adjustment
    return _round_nearest_int(bmr)


def calculate_tdee(bmr: int, activity_level: str) -> int:
    """Calculate total daily energy expenditure from BMR and activity."""
    if bmr <= 0:
        raise CalorieCalculationError("bmr must be greater than 0")

    normalized_activity_level = activity_level.strip().lower()
    try:
        multiplier = ACTIVITY_MULTIPLIERS[normalized_activity_level]
    except KeyError as exc:
        raise CalorieCalculationError("activity_level must be supported") from exc

    return _round_nearest_int(bmr * multiplier)


def calculate_targets(
    *,
    age: int,
    sex: str,
    weight_kg: float,
    height_cm: float,
    activity_level: str,
    goal: str,
) -> CalorieTargets:
    """Calculate daily calorie and macro targets for the requested goal."""
    normalized_sex = sex.strip().lower()
    normalized_goal = goal.strip().lower()

    bmr = calculate_bmr(age=age, sex=normalized_sex, weight_kg=weight_kg, height_cm=height_cm)
    tdee = calculate_tdee(bmr=bmr, activity_level=activity_level)

    if normalized_goal == "fat_loss":
        safety_floor = MALE_MIN_CALORIES if normalized_sex == "male" else FEMALE_MIN_CALORIES
        if safety_floor >= tdee:
            raise CalorieCalculationError(UNSAFE_FAT_LOSS_MESSAGE)

        max_ratio_deficit = _round_nearest_int(tdee * FAT_LOSS_MAX_DEFICIT_RATIO)
        deficit = min(FAT_LOSS_DEFICIT_KCAL, max_ratio_deficit)
        daily_calories = max(tdee - deficit, safety_floor)
        protein_per_kg = MAINTENANCE_PROTEIN_G_PER_KG
    elif normalized_goal == "maintenance":
        daily_calories = tdee
        protein_per_kg = MAINTENANCE_PROTEIN_G_PER_KG
    elif normalized_goal == "muscle_gain":
        daily_calories = tdee + MUSCLE_GAIN_SURPLUS_KCAL
        protein_per_kg = MUSCLE_GAIN_PROTEIN_G_PER_KG
    else:
        raise CalorieCalculationError("goal must be one of: fat_loss, maintenance, muscle_gain")

    protein_g = _round_nearest_int(weight_kg * protein_per_kg)
    fat_g = _round_nearest_int((daily_calories * FAT_CALORIE_RATIO) / KCAL_PER_GRAM_FAT)
    carb_calories = daily_calories - (protein_g * KCAL_PER_GRAM_PROTEIN) - (
        fat_g * KCAL_PER_GRAM_FAT
    )
    carb_g = max(0, _round_nearest_int(carb_calories / KCAL_PER_GRAM_CARBS))

    return CalorieTargets(
        bmr=bmr,
        tdee=tdee,
        daily_calories=daily_calories,
        protein_g=protein_g,
        carb_g=carb_g,
        fat_g=fat_g,
    )

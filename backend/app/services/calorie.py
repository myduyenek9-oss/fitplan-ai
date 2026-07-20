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


def _round_nearest_int(value: float) -> int:
    return floor(value + 0.5)


def calculate_bmr(age: int, sex: str, weight_kg: float, height_cm: float) -> int:
    """Calculate BMR with the Mifflin-St Jeor equation."""
    normalized_sex = sex.strip().lower()
    if normalized_sex == "male":
        sex_adjustment = 5
    elif normalized_sex == "female":
        sex_adjustment = -161
    else:
        raise ValueError("sex must be one of: male, female")

    bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + sex_adjustment
    return _round_nearest_int(bmr)


def calculate_tdee(bmr: int, activity_level: str) -> int:
    """Calculate total daily energy expenditure from BMR and activity."""
    normalized_activity_level = activity_level.strip().lower()
    try:
        multiplier = ACTIVITY_MULTIPLIERS[normalized_activity_level]
    except KeyError as exc:
        raise ValueError("activity_level must be supported") from exc

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
        max_ratio_deficit = _round_nearest_int(tdee * FAT_LOSS_MAX_DEFICIT_RATIO)
        deficit = min(FAT_LOSS_DEFICIT_KCAL, max_ratio_deficit)
        safety_floor = MALE_MIN_CALORIES if normalized_sex == "male" else FEMALE_MIN_CALORIES
        daily_calories = max(tdee - deficit, safety_floor)
        protein_per_kg = MAINTENANCE_PROTEIN_G_PER_KG
    elif normalized_goal == "maintenance":
        daily_calories = tdee
        protein_per_kg = MAINTENANCE_PROTEIN_G_PER_KG
    elif normalized_goal == "muscle_gain":
        daily_calories = tdee + MUSCLE_GAIN_SURPLUS_KCAL
        protein_per_kg = MUSCLE_GAIN_PROTEIN_G_PER_KG
    else:
        raise ValueError("goal must be one of: fat_loss, maintenance, muscle_gain")

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

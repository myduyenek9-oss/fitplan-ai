import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.calorie import calculate_bmr, calculate_targets, calculate_tdee


@pytest.mark.parametrize(
    ("age", "sex", "weight_kg", "height_cm", "expected_bmr"),
    [
        (30, "male", 80.0, 180.0, 1780),
        (30, "female", 60.0, 164.0, 1314),
    ],
)
def test_calculate_bmr_uses_mifflin_st_jeor_fixtures(
    age: int,
    sex: str,
    weight_kg: float,
    height_cm: float,
    expected_bmr: int,
) -> None:
    assert calculate_bmr(age=age, sex=sex, weight_kg=weight_kg, height_cm=height_cm) == expected_bmr


@pytest.mark.parametrize(
    ("activity_level", "expected_tdee"),
    [
        ("sedentary", 1920),
        ("light", 2200),
        ("moderate", 2480),
        ("active", 2760),
        ("very_active", 3040),
    ],
)
def test_calculate_tdee_applies_supported_activity_multipliers(
    activity_level: str,
    expected_tdee: int,
) -> None:
    assert calculate_tdee(bmr=1600, activity_level=activity_level) == expected_tdee


def test_calculate_tdee_rejects_unknown_activity_level() -> None:
    with pytest.raises(ValueError, match="activity_level"):
        calculate_tdee(bmr=1600, activity_level="weekend_warrior")


def test_fat_loss_target_is_below_tdee_with_macros() -> None:
    targets = calculate_targets(
        age=30,
        sex="male",
        weight_kg=80.0,
        height_cm=180.0,
        activity_level="moderate",
        goal="fat_loss",
    )

    assert targets.bmr == 1780
    assert targets.tdee == 2759
    assert targets.daily_calories == 2259
    assert targets.daily_calories < targets.tdee
    assert targets.protein_g == 144
    assert targets.fat_g == 63
    assert targets.carb_g == 279


def test_fat_loss_target_respects_female_safety_floor() -> None:
    targets = calculate_targets(
        age=40,
        sex="female",
        weight_kg=50.0,
        height_cm=160.0,
        activity_level="sedentary",
        goal="fat_loss",
    )

    assert targets.bmr == 1139
    assert targets.tdee == 1367
    assert targets.daily_calories == 1200


def test_muscle_gain_target_is_above_tdee_and_uses_higher_protein() -> None:
    targets = calculate_targets(
        age=30,
        sex="male",
        weight_kg=80.0,
        height_cm=180.0,
        activity_level="moderate",
        goal="muscle_gain",
    )

    assert targets.tdee == 2759
    assert targets.daily_calories == 3059
    assert targets.daily_calories > targets.tdee
    assert targets.protein_g == 160
    assert targets.fat_g == 85
    assert targets.carb_g == 414


def test_maintenance_target_equals_tdee() -> None:
    targets = calculate_targets(
        age=30,
        sex="male",
        weight_kg=80.0,
        height_cm=180.0,
        activity_level="moderate",
        goal="maintenance",
    )

    assert targets.daily_calories == targets.tdee == 2759


def test_calculate_targets_rejects_unknown_goal() -> None:
    with pytest.raises(ValueError, match="goal"):
        calculate_targets(
            age=30,
            sex="male",
            weight_kg=80.0,
            height_cm=180.0,
            activity_level="moderate",
            goal="recomposition",
        )


def test_preview_endpoint_returns_calorie_targets_without_auth() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/calorie/preview",
        json={
            "age": 30,
            "sex": "male",
            "weight_kg": 80.0,
            "height_cm": 180.0,
            "activity_level": "moderate",
            "goal": "fat_loss",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "bmr": 1780,
        "tdee": 2759,
        "daily_calories": 2259,
        "protein_g": 144,
        "carb_g": 279,
        "fat_g": 63,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("age", 0),
        ("sex", "unknown"),
        ("weight_kg", 0),
        ("height_cm", 0),
        ("activity_level", "weekend_warrior"),
        ("goal", "recomposition"),
    ],
)
def test_preview_endpoint_validates_request_fields(field: str, value: object) -> None:
    client = TestClient(app)
    payload: dict[str, object] = {
        "age": 30,
        "sex": "male",
        "weight_kg": 80.0,
        "height_cm": 180.0,
        "activity_level": "moderate",
        "goal": "fat_loss",
    }
    payload[field] = value

    response = client.post("/api/calorie/preview", json=payload)

    assert response.status_code == 422

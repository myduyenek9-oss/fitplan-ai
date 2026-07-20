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


def test_fat_loss_target_respects_male_safety_floor_without_exceeding_tdee() -> None:
    targets = calculate_targets(
        age=60,
        sex="male",
        weight_kg=60.0,
        height_cm=165.0,
        activity_level="sedentary",
        goal="fat_loss",
    )

    assert targets.bmr == 1336
    assert targets.tdee == 1603
    assert targets.daily_calories == 1500
    assert targets.daily_calories < targets.tdee


def test_fat_loss_rejects_when_tdee_is_below_safety_floor() -> None:
    with pytest.raises(ValueError, match="当前维持热量低于安全减脂下限"):
        calculate_targets(
            age=80,
            sex="female",
            weight_kg=40.0,
            height_cm=145.0,
            activity_level="sedentary",
            goal="fat_loss",
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"age": 120, "sex": "male", "weight_kg": 80.0, "height_cm": 180.0},
        {"age": 30, "sex": "male", "weight_kg": 1.0, "height_cm": 180.0},
        {"age": 30, "sex": "male", "weight_kg": 80.0, "height_cm": 1.0},
    ],
)
def test_calculate_bmr_rejects_unrealistic_adult_inputs(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="age|weight_kg|height_cm"):
        calculate_bmr(**kwargs)


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
        ("age", 120),
        ("sex", "unknown"),
        ("weight_kg", 0),
        ("weight_kg", 1),
        ("height_cm", 0),
        ("height_cm", 1),
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

def test_preview_endpoint_rejects_fat_loss_when_tdee_is_below_safety_floor() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/calorie/preview",
        json={
            "age": 80,
            "sex": "female",
            "weight_kg": 40.0,
            "height_cm": 145.0,
            "activity_level": "sedentary",
            "goal": "fat_loss",
        },
    )

    assert response.status_code == 422
    assert "当前维持热量低于安全减脂下限" in response.json()["detail"]


def test_preview_endpoint_normalizes_choice_fields() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/calorie/preview",
        json={
            "age": 30,
            "sex": " Male ",
            "weight_kg": 80.0,
            "height_cm": 180.0,
            "activity_level": " Moderate ",
            "goal": " Fat_Loss ",
        },
    )

    assert response.status_code == 200
    assert response.json()["daily_calories"] == 2259

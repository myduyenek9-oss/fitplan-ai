from app.services.record_detection import (
    looks_like_completed_exercise,
    looks_like_mixed_completed_records,
)


def test_mixed_record_detector_supports_chinese_duration_and_completed_action():
    assert looks_like_mixed_completed_records(
        "刚刚吃了两个烧烤 慢跑了十分钟"
    )
    assert looks_like_completed_exercise("刚刚慢跑了十分钟")


def test_mixed_record_detector_does_not_save_planned_exercise():
    assert not looks_like_mixed_completed_records(
        "刚刚吃了两个烧烤，下午想慢跑十分钟"
    )

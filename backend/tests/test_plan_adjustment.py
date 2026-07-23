from datetime import date

from app.services.plan_adjustment import detect_postpone_training_request


TODAY = date(2026, 7, 22)


def test_detects_clear_relative_training_postponement_commands():
    assert detect_postpone_training_request(
        "\u628a\u6211\u660e\u5929\u7684\u8bad\u7ec3\u8ba1\u5212\u5ef6\u8fdf\u4e00\u5929",
        TODAY,
    ) == date(2026, 7, 23)
    assert detect_postpone_training_request(
        "\u660e\u5929\u6709\u4e8b\uff0c\u8bad\u7ec3\u5f80\u540e\u632a\u4e00\u5929",
        TODAY,
    ) == date(2026, 7, 23)
    assert detect_postpone_training_request(
        "\u628a\u540e\u5929\u7684\u5065\u8eab\u5b89\u6392\u987a\u5ef6",
        TODAY,
    ) == date(2026, 7, 24)
    assert detect_postpone_training_request(
        "\u6211\u660e\u5929\u4e0d\u60f3\u7ec3 \u4f60\u5e2e\u6211\u5ef6\u8fdf\u4e00\u5929",
        TODAY,
    ) == date(2026, 7, 23)


def test_detects_explicit_calendar_dates():
    assert detect_postpone_training_request(
        "\u628a2026-07-25\u7684\u8bad\u7ec3\u5ef6\u540e\u4e00\u5929",
        TODAY,
    ) == date(2026, 7, 25)
    assert detect_postpone_training_request(
        "\u628a7\u670826\u65e5\u7684\u8bad\u7ec3\u987a\u5ef6",
        TODAY,
    ) == date(2026, 7, 26)


def test_rejects_hypothetical_negated_or_ambiguous_messages():
    assert detect_postpone_training_request(
        "\u5982\u679c\u660e\u5929\u8bad\u7ec3\u63a8\u8fdf\u4f1a\u600e\u4e48\u6837\uff1f",
        TODAY,
    ) is None
    assert detect_postpone_training_request(
        "\u4e0d\u8981\u63a8\u8fdf\u660e\u5929\u8bad\u7ec3",
        TODAY,
    ) is None
    assert detect_postpone_training_request(
        "\u628a\u660e\u5929\u7684\u5b89\u6392\u5ef6\u8fdf\u4e00\u5929",
        TODAY,
    ) is None

from __future__ import annotations

import re
from datetime import date, timedelta

_ACTION_TERMS = (
    "\u63a8\u8fdf",
    "\u5ef6\u8fdf",
    "\u5ef6\u540e",
    "\u987a\u5ef6",
    "\u5f80\u540e\u632a",
    "\u5f80\u540e\u79fb",
    "\u632a\u5230\u540e\u4e00\u5929",
    "\u6539\u5230\u540e\u4e00\u5929",
)
_TRAINING_TERMS = ("\u8bad\u7ec3", "\u5065\u8eab", "\u8fd0\u52a8\u8ba1\u5212", "\u8bad\u7ec3\u8ba1\u5212", "\u7ec3")
_NEGATION_TERMS = (
    "\u4e0d\u8981",
    "\u522b",
    "\u4e0d\u7528",
    "\u5148\u4e0d",
    "\u6682\u65f6\u4e0d",
    "\u53d6\u6d88",
)
_MEAL_REPLACEMENT_TERMS = (
    "\u6362\u4e00\u4e0b",
    "\u6362\u4e00\u4efd",
    "\u6362\u4e2a",
    "\u6362\u6210",
    "\u66ff\u6362",
    "\u6539\u6210",
    "\u91cd\u65b0\u5b89\u6392",
    "\u91cd\u65b0\u6362",
    "\u8c03\u6574\u4e00\u4e0b",
)
_MEAL_ALIASES = (
    ("breakfast", ("\u65e9\u9910", "\u65e9\u996d", "\u65e9\u4e0a\u7684")),
    ("lunch", ("\u5348\u9910", "\u5348\u996d", "\u4e2d\u9910", "\u4e2d\u5348\u7684")),
    ("dinner", ("\u665a\u9910", "\u665a\u996d", "\u665a\u4e0a\u7684", "\u4eca\u665a")),
    ("snack", ("\u52a0\u9910", "\u96f6\u98df", "\u4e0b\u5348\u8336")),
)
_HYPOTHETICAL_TERMS = (
    "\u5982\u679c",
    "\u5047\u5982",
    "\u4f1a\u600e\u4e48\u6837",
    "\u4f1a\u600e\u6837",
    "\u80fd\u4e0d\u80fd",
    "\u53ef\u4e0d\u53ef\u4ee5",
    "\u662f\u5426",
)


def detect_postpone_training_request(message: str, today: date) -> date | None:
    """Return the workout date only for a clear one-day postponement command."""
    normalized = re.sub(r"\s+", "", message.strip())
    if not normalized:
        return None
    if any(term in normalized for term in _NEGATION_TERMS):
        return None
    if any(term in normalized for term in _HYPOTHETICAL_TERMS):
        return None
    if not any(term in normalized for term in _ACTION_TERMS):
        return None
    if not any(term in normalized for term in _TRAINING_TERMS):
        return None
    return _extract_requested_date(normalized, today)


def _extract_requested_date(message: str, today: date) -> date | None:
    iso_match = re.search(r"(?<!\d)(\d{4})[-/.\u5e74](\d{1,2})[-/.\u6708](\d{1,2})\u65e5?", message)
    if iso_match:
        try:
            return date(*(int(value) for value in iso_match.groups()))
        except ValueError:
            return None

    month_day_match = re.search(r"(?<!\d)(\d{1,2})\u6708(\d{1,2})\u65e5", message)
    if month_day_match:
        try:
            return date(today.year, int(month_day_match.group(1)), int(month_day_match.group(2)))
        except ValueError:
            return None

    relative_dates = (
        ("\u5927\u540e\u5929", 3),
        ("\u540e\u5929", 2),
        ("\u660e\u665a", 1),
        ("\u660e\u5929", 1),
        ("\u4eca\u665a", 0),
        ("\u4eca\u5929", 0),
    )
    for term, offset in relative_dates:
        if term in message:
            return today + timedelta(days=offset)
    return None


def detect_meal_replacement_request(message: str, today: date) -> tuple[date, str] | None:
    """Detect an explicit request to replace one meal without regenerating the week."""
    normalized = re.sub(r"\s+", "", message.strip())
    if not normalized or not any(term in normalized for term in _MEAL_REPLACEMENT_TERMS):
        return None
    if any(term in normalized for term in ("\u4e0d\u8981\u6362", "\u522b\u6362", "\u4e0d\u7528\u6362", "\u4e0d\u9700\u8981\u6362")):
        return None

    meal_type = next(
        (meal for meal, aliases in _MEAL_ALIASES if any(alias in normalized for alias in aliases)),
        None,
    )
    if meal_type is None:
        return None

    requested_date = _extract_requested_date(normalized, today)
    return requested_date or today, meal_type

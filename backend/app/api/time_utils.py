from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.profile import Profile


def validate_timezone_name(value: str) -> str:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("timezone must be a valid IANA timezone") from exc
    return value


def ensure_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must include a timezone offset")
    return value


def to_utc_naive(value: datetime) -> datetime:
    ensure_timezone_aware(value)
    return value.astimezone(UTC).replace(tzinfo=None)


def get_user_timezone(db: Session, user_id: int) -> ZoneInfo:
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    if profile is None or profile.timezone is None:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(profile.timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def utc_naive_to_timezone(value: datetime, timezone: ZoneInfo) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        utc_value = value.replace(tzinfo=UTC)
    else:
        utc_value = value.astimezone(UTC)
    return utc_value.astimezone(timezone)


def local_date_to_utc_naive_bounds(day: date, timezone: ZoneInfo) -> tuple[datetime, datetime]:
    local_start = datetime.combine(day, time.min, tzinfo=timezone)
    local_end = local_start + timedelta(days=1)
    return (
        local_start.astimezone(UTC).replace(tzinfo=None),
        local_end.astimezone(UTC).replace(tzinfo=None),
    )

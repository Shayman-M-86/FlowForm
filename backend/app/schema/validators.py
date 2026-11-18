from datetime import UTC, date, datetime

from pydantic import AwareDatetime


def normalise_email(value: object) -> object:
    if not isinstance(value, str):
        return value

    return value.strip().lower()


def validate_future_datetime_utc(value: AwareDatetime) -> AwareDatetime:
    value_utc = value.astimezone(UTC)

    if value_utc <= datetime.now(UTC):
        raise ValueError("expires_at must be a future datetime.")

    return value_utc


def parse_calendar_date(value: object) -> date:
    """Accept a calendar date or its exact YYYY-MM-DD wire representation."""
    if type(value) is date:
        return value
    if isinstance(value, str):
        parsed = date.fromisoformat(value)
        if parsed.isoformat() == value:
            return parsed
    raise ValueError("calendar dates must use YYYY-MM-DD")

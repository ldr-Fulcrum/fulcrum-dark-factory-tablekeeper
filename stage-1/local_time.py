"""Resolve wall time by round trip; always select the first repeated instant."""
import re
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from errors import fail, string

UTC = timezone.utc
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


@lru_cache(maxsize=512)
def zone(name: str):
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        fail()


def calendar_day(value: str):
    string(value)
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        fail()
    try:
        return date.fromisoformat(value)
    except ValueError:
        fail()


def local_datetime(value):
    string(value)
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}", value):
        fail()
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        fail()


def minutes(value):
    string(value)
    if not re.fullmatch(r"[0-9]{2}:[0-9]{2}", value):
        fail()
    hour, minute = map(int, value.split(":"))
    if hour > 23 or minute > 59:
        fail()
    return hour * 60 + minute


def resolve(local: datetime, tz: ZoneInfo):
    candidates = []
    for fold in (0, 1):
        try:
            instant = local.replace(tzinfo=tz, fold=fold).astimezone(UTC)
            if instant.astimezone(tz).replace(tzinfo=None) == local:
                candidates.append(instant)
        except (OverflowError, ValueError):
            continue
    return min(candidates) if candidates else None


def closing_instant(local: datetime, tz: ZoneInfo):
    # A closing time in a gap denotes the transition, not gap-time + offset.
    for _ in range(2881):
        instant = resolve(local, tz)
        if instant is not None:
            return instant
        try:
            local += timedelta(minutes=1)
        except OverflowError:
            fail()
    fail()


@lru_cache(maxsize=1024)
def slot_grid(timezone_name: str, year: int, month: int, day: int, opening: int, closing: int, step: int, duration: int):
    """Bookable slots of one opening window, independent of bookings.

    Returns (starts_at_local, start, end, starts_at) tuples with UTC instants.
    Depends only on immutable restaurant configuration values and the date, so it
    is memoized; any failure raises and is not cached.
    """
    tz = zone(timezone_name)
    close = closing_instant(datetime(year, month, day, closing // 60, closing % 60), tz)
    slots = []
    for wall in range(opening, closing, step):
        local = datetime(year, month, day, wall // 60, wall % 60)
        start = resolve(local, tz)
        if start is None:
            continue
        try:
            end = start + timedelta(minutes=duration)
        except OverflowError:
            continue
        if end > close:
            continue
        # iso() of both ends is kept for its range validation.
        starts_at = iso(start, tz)
        iso(end, tz)
        slots.append((local.isoformat(timespec="minutes"), start, end, starts_at))
    return tuple(slots)


def iso(instant: datetime, tz=UTC):
    try:
        return instant.astimezone(tz).isoformat(timespec="seconds")
    except (OverflowError, ValueError):
        fail()


TIMESTAMP_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2}(?::[0-9]{2})?)")


@lru_cache(maxsize=65536)
def _parsed_timestamp(value: str):
    # Stored timestamps are immutable strings, so their parsed UTC instant is
    # memoized; datetimes are immutable and safe to share between threads.
    # Invalid input raises and is therefore never cached.
    if not TIMESTAMP_PATTERN.fullmatch(value):
        fail()
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.astimezone(UTC)
    except (ValueError, OverflowError):
        fail()


def timestamp(value):
    string(value)
    return _parsed_timestamp(value)


def interval(restaurant: dict, table_id: str, start_local: str, party: int):
    table = next((t for t in restaurant["tables"] if t["id"] == table_id), None)
    if table is None:
        fail(404, "not_found")
    local = local_datetime(start_local)
    tz = zone(restaurant["timezone"])
    start = resolve(local, tz)
    if start is None:
        fail(422, "invalid_local_time")
    hours = next((h for h in restaurant["opening_hours"] if h["weekday"] == WEEKDAYS[local.weekday()]), None)
    if hours is None:
        fail(422, "outside_opening_hours")
    opening, closing = minutes(hours["opens"]), minutes(hours["closes"])
    wall = local.hour * 60 + local.minute
    close_local = local.replace(hour=closing // 60, minute=closing % 60)
    close = closing_instant(close_local, tz)
    duration_seconds = restaurant["reservation_duration_minutes"] * 60
    if wall < opening or wall >= closing or duration_seconds > (close - start).total_seconds():
        fail(422, "outside_opening_hours")
    if (wall - opening) % restaurant["slot_minutes"]:
        fail(422, "not_on_slot_grid")
    if party > table["capacity"]:
        fail(422, "party_exceeds_capacity")
    end = start + timedelta(seconds=duration_seconds)
    iso(end, tz)
    return start, end

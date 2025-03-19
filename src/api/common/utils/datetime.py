from datetime import datetime, timezone


def get_current_datetime() -> datetime:
    """Return current UTC datetime with timezone info."""
    # First create a UTC datetime
    dt = datetime.now(timezone.utc)
    # Ensure microseconds are stripped for consistency in tests
    dt = dt.replace(microsecond=0)
    # Double-check timezone info is present
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

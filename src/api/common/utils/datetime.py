from datetime import date, datetime, timezone, timedelta
from typing import Optional


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


def get_date(date_str: str | None) -> Optional[date]:
    return None if date_str is None else date.fromisoformat(date_str[:10])


def get_month_boundaries(target_month: date) -> tuple[date, date]:
    """
    Get the start and end dates for a given month.
    
    Args:
        target_month: The month to get boundaries for
        
    Returns:
        Tuple of (month_start, month_end) dates
    """
    month_start = target_month.replace(day=1)
    if target_month.month == 12:
        month_end = date(target_month.year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(target_month.year,
                         target_month.month + 1, 1) - timedelta(days=1)
    return month_start, month_end


def get_month_start(target_month: date) -> date:
    """Get the first day of the given month."""
    return target_month.replace(day=1)


def get_month_end(target_month: date) -> date:
    """Get the last day of the given month."""
    if target_month.month == 12:
        return date(target_month.year + 1, 1, 1) - timedelta(days=1)
    else:
        return date(target_month.year,
                   target_month.month + 1, 1) - timedelta(days=1)

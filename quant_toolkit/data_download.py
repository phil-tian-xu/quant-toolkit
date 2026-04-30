from .constants import PACKAGE_PREFIX
from datetime import date, datetime

import Quantlib as ql


def get_calendar(
    exchange,
    start_date="1900-01-01",
    end_date="2100-01-01",
    calendar_type=str,
):
    """Get valid trading days for a supported exchange calendar.

    Args:
        exchange (str): Exchange identifier.
        start_date (str, date, or datetime): Start date of the calendar range. Defaults to 1900-01-01.
        end_date (str, date, or datetime): End date of the calendar range. Defaults to 2100-01-01.
        calendar_type (type): Output date type. Must be str, date, or datetime. Defaults to str.
    
    Returns:
        list: Trading days between start_date and end_date, inclusive.

    Raises:
        ValueError: If exchange is unsupported or start_date is after end_date.
        TypeError: If date inputs or calendar_type are invalid.
    """

    cal = _get_quantlib_calendar(exchange)
    start_py = _to_py_date(start_date)
    end_py = _to_py_date(end_date)

    if start_py > end_py:
        raise ValueError(f"{PACKAGE_PREFIX} start_date must be earlier than or equal to end_date.")

    if calendar_type not in {str, date, datetime}:
        raise TypeError(f"{PACKAGE_PREFIX} calendar_type must be one of: str, date, datetime.")
    
    start_ql = ql.Date(start_py.day, start_py.month, start_py.year)
    end_ql = ql.Date(end_py.day, end_py.month, end_py.year)
    trading_days = []
    current_day = start_ql
    one_day = ql.Period(1, ql.Days)

    while current_day <= end_ql:
        if cal.isBusinessDay(current_day):
            day_str = current_day.ISO()
            if calendar_type is str:
                trading_days.append(day_str)
            elif calendar_type is date:
                trading_days.append(date.fromisoformat(day_str))
            else:
                trading_days.append(datetime.fromisoformat(day_str))

        current_day = current_day + one_day
    
    return trading_days


def _get_quantlib_calendar(exchange):
    """Return the QuantLib calendar for a supported exchange.

    Args:
        exchange (str): Exchange identifier.

    Returns:
        QuantLib calendar: Calendar object used to check business days.
    
    Raises:
        TypeError: If exchange is not a string.
        ValueError: If exchange is unsupported.
    """
    if not isinstance(exchange, str):
        raise TypeError(f"{PACKAGE_PREFIX} exchange must be a string.")
    
    exchange = exchange.upper().strip()
    calendar_map = {
        "NYSE": ql.UnitedStates(ql.UnitedStates.NYSE),
        "US": ql.UnitedStates(ql.UnitedStates.NYSE),
        "HK": ql.HongKong(ql.HongKong.HKEx),
        "HKEX": ql.HongKong(ql.HongKong.HKEx),
        "UK": ql.UnitedKingdom(ql.UnitedKingdom.Exchange),
        "LSE": ql.UnitedKingdom(ql.UnitedKingdom.Exchange),
        "JP": ql.Japan(),
        "TSE": ql.Japan(),
        "JAPAN": ql.Japan(),
    }
    
    if exchange not in calendar_map:
        supported = ", ".join(calendar_map.keys())
        raise ValueError(
            f"{PACKAGE_PREFIX} Unsupported exchange: {exchange}. Supported exchanges: {supported}."
        )
    return calendar_map[exchange]


def _to_py_date(value):
    """Convert a date-like value to a Python date.

    Args:
        value (str, date, or datetime): Date-like input.

    Returns:
        date: Converted Python date.

    Raises:
        TypeError: If value is not str, date, or datetime.
    """
    if isinstance(value, datetime):
        return value.date()
    elif isinstance(value, date):
        return value
    elif isinstance(value, str):
        return datetime.fromisoformat(value).date()
    else:
        raise TypeError(f"{PACKAGE_PREFIX} Date input must be str, date, or datetime.")


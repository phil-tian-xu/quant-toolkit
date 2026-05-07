from datetime import date, datetime

import pytest
from quant_toolkit.data_download import get_calendar


def test_get_calendar_basic_nyse():
    calendar = get_calendar(
        start_date="2024-01-01",
        end_date="2024-01-10",
        exchange="NYSE",
    )

    assert isinstance(calendar, list)
    assert len(calendar) > 0


def test_get_calendar_output_date_type():
    calendar = get_calendar(
        start_date="2024-01-01",
        end_date="2024-01-10",
        exchange="NYSE",
        calendar_type=date,
    )

    assert isinstance(calendar[0], date)


def test_get_calendar_output_datetime_type():
    calendar = get_calendar(
        start_date="2024-01-01",
        end_date="2024-01-10",
        exchange="NYSE",
        calendar_type=datetime,
    )

    assert isinstance(calendar[0], datetime)


def test_get_calendar_invalid_exchange():
    with pytest.raises(ValueError):
        get_calendar(
            start_date="2024-01-01",
            end_date="2024-01-10",
            exchange="INVALID",
        )


def test_get_calendar_invalid_date_order():
    with pytest.raises(ValueError):
        get_calendar(
            start_date="2024-01-10",
            end_date="2024-01-01",
            exchange="NYSE",
        )


def test_get_calendar_invalid_calendar_type():
    with pytest.raises(TypeError):
        get_calendar(
            start_date="2024-01-01",
            end_date="2024-01-10",
            exchange="NYSE",
            calendar_type=list,
        )


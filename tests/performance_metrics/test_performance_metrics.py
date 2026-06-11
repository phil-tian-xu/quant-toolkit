import pandas as pd
import pytest

from quant_toolkit.performance_metrics import (
    calculate_performance_metrics,
    _to_dataframe,
    _resolve_standard_annualized_factor,
)


def test_to_dataframe_series():
    """Basic helper func check 1
    """
    series = pd.Series([100, 110, 121], name="A")
    df = _to_dataframe(series)

    assert isinstance(df, pd.DataFrame)
    assert df.shape == (3, 1)
    assert list(df.columns) == ["A"]
    

def test_to_dataframe_invalid_input():
    """Basic helper func check 2
    """
    with pytest.raises(TypeError):
        _to_dataframe([100, 110, 121])


def test_resolve_standard_annualized_factor_default_daily():
    """Basic helper func check 3
    """
    factor = _resolve_standard_annualized_factor(
        frequency="D",
        annualized_factor="default",
    )

    assert factor == 252


def test_resolve_standard_annualized_factor_invalid_frequency():
    """Basic helper func check 4
    """
    with pytest.raises(ValueError):
        _resolve_standard_annualized_factor(
            frequency="X",
            annualized_factor="default",
        )


def test_calculate_performance_metrics_basic_positive_return():
    """Main function checks 1
    """
    data = pd.DataFrame({"A": [100, 110, 121]}, index=["2024-01-03", "2024-01-04", "2024-01-05"])

    metrics = calculate_performance_metrics(data)

    assert metrics.loc["A", "Total Return"] > 0
    assert metrics.loc["A", "Max Drawdown"] == 0


def test_calculate_performance_metrics_empty_input():
    data = pd.DataFrame()

    with pytest.raises(ValueError):
        calculate_performance_metrics(data)



def test_calculate_performance_metrics_single_observation():
    data = pd.DataFrame({
        "A": [100],
    })

    with pytest.raises(ValueError):
        calculate_performance_metrics(data)

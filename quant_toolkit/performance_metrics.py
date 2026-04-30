import pandas as pd
import numpy as np
from datetime import datetime
from .data_download import get_calendar
from .constants import PACKAGE_PREFIX


def calculate_performance_metrics(
    input_data,
    start="1900-01-01",
    end="2100-01-01",
    frequency="D",
    annualized_factor="default",
    exchange=None,
    is_reformat=False,
    rf=0.0
):
    """Calculate standard performance metrics from price or NAV data.

    Args:
        input_data (pd.Series or pd.DataFrame): Price, NAV, or index-level data. 
            Each column represents one asset or strategy.
        start (str): Start Date. 
            Defaults to "1900-01-01".
        end (str): End Date. 
            Defaults to "2100-01-01".
        frequency (str): Data frequency for input data. 
            Supported values are "D", "W", "M", and "Q". 
            Defaults to "D".
        annualized_factor (str, int or float): Annualization method or factor.
            Use "default" to infer from frequency, "actual" to use the actual exchange calendar,
              or a positive number as a custom factor.
            Defaults to "default".
        exchange (str): Exchange identifier used when annualized_factor is "actual". 
            Defaults to None.
        is_reformat (bool): Whether to also return a formatted metrics table.
            Defaults to False.
        rf: Annual risk-free rate. Defaults to 0.0.
            Defaults to 0.0.

    Returns:
        pd.DataFrame or tuple: Performance metrics table. 
            If is_reformat is True, returns both the raw metrics table and the formatted metrics table.
    """
    _validate_performance_metric_inputs()
    data = _to_dataframe(input_data)
    data = _slice_by_date(data, start, end)

    if annualized_factor == "actual":
        calc_data, annual_factor = _prepare_actual_calendar_data(data, exchange)
    else:
        calc_data = data
        annual_factor = _resolve_standard_annualized_factor(
        frequency=frequency,
        annualized_factor=annualized_factor,
    )

    metrics = _compute_performance_metrics(
        input_data=calc_data,
        annualized_factor=annual_factor,
        rf=rf,
    )

    if is_reformat:
        formatted = _format_performance_metrics(metrics)
        return metrics, formatted
    return metrics


def _validate_performance_metric_inputs():
    """Validate inputs for performance metric calculation.

    This function is reserved for basic validation of user-facing arguments
    passed into calculate_performance_metrics.
    """
    pass


def _to_dataframe(input_data) -> pd.DataFrame:
    """Convert input data to DataFrame.
    
    Args:
        input_data (pd.Series or pd.DataFrame): Price, NAV, or index-level data.

    Returns:
        pd.DataFrame: Input data converted to DataFrame format.

    """
    if isinstance(input_data, pd.Series):
        return input_data.to_frame()
    elif isinstance(input_data, pd.DataFrame):
        return input_data.copy()
    else:
        raise TypeError(f"{PACKAGE_PREFIX} input_data must be a pandas Series or DataFrame.")


def _slice_by_date(input_data, start, end):
    """Slice input data between start and end dates.

    Args:
        input_data (pd.DataFrame): DataFrame with a date-like index.
        start (str): Start date for slicing.
        end (str): End date for slicing.

    Returns:
        pd.DataFrame: Data sliced between start and end.
        
    """
    return input_data.loc[start:end].copy()

def _prepare_actual_calendar_data(input_data, exchange):
    """Align input data to the actual trading calendar of the given exchange.

    Logic:
    1. Get the trading calendar between the first and last date in input_data.
    2. Keep only dates that belong to the trading calendar.
    3. Reindex to the full trading calendar.
    4. Forward fill missing values.
    5. Return the aligned data and the average annual trading days.

    Args:
        input_data (pd.DataFrame): Price, NAV, or index-level data with a date-like index.
        exchange (str): Exchange identifier used to retrieve the trading calendar.
    
    Returns:
        (pd.DataFrame, int or float): Calendar-aligned data and estimated average annual trading days.

    """
    if not exchange:
        raise ValueError(f"{PACKAGE_PREFIX} exchange must be provided when annualized_factor='actual'.")
    if input_data.empty:
        raise ValueError(f"{PACKAGE_PREFIX} input_data is empty.")
    
    start_date = input_data.index[0]
    end_date = input_data.index[-1]
    average_annual_trading_days, trading_calendar = _get_annual_trading_days(
        start_date,
        end_date,
        exchange,
    )
    calc_data = input_data[input_data.index.isin(trading_calendar)].copy()
    calc_data = calc_data.reindex(trading_calendar).ffill()

    return calc_data, average_annual_trading_days


def _get_annual_trading_days(start_date, end_date, exchange):
    """Get the trading calendar and estimate average annual trading days.

    Logic:
        1. Retrieve the full trading calendar for the specified exchange between start_date and end_date.
        2. Check that valid trading days exist.
        3. Estimate the average annual trading days based on the total number of trading days divided by the calendar year span.
    
    Args:
        start_date (str or datetime): Start date for calendar retrieval.
        end_date (str or datetime): End date for calendar retrieval.
        exchange (str): Exchange identifier used by get_calendar.

    Returns:
        (average_annual_trading_days, trading_calendar)
            - average_annual_trading_days (int or float): Estimated average trading days per year.
            - trading_calendar (list): Full list of trading dates.
    """
    trading_calendar = get_calendar(
        start_date=start_date,
        end_date=end_date,
        exchange=exchange,
        calendar_type=datetime,
    )

    if len(trading_calendar) == 0:
        raise ValueError(f"{PACKAGE_PREFIX} No trading days found for the given date range and exchange.")
    
    start_year = trading_calendar[0].year
    end_year = trading_calendar[-1].year
    year_count = end_year - start_year + 1
    average_annual_trading_days = len(trading_calendar) / year_count
    return average_annual_trading_days, trading_calendar


def _resolve_standard_annualized_factor(frequency, annualized_factor):
    """Resolve the annualized factor for standard calculation modes.

    Args:
        frequency (str): Data frequency. Supported values are "D", "W", "M", and "Q".
        annualized_factor (str, int, or float): Either "default" or a positive numeric annualization factor.

    Returns:
        int or float: Annualized factor used for performance metric calculation.
    
    Raises:
        ValueError: If annualized_factor is invalid or frequency is unsupported.
    """
    if isinstance(annualized_factor, (int, float)):
        if annualized_factor <= 0:
            raise ValueError(f"{PACKAGE_PREFIX} annualized_factor must be positive.")
        return annualized_factor
    
    if annualized_factor != "default":
        raise ValueError(
            f"{PACKAGE_PREFIX} annualized_factor must be a positive number, 'default', or 'actual'."
        )
    
    frequency = frequency.upper().strip()
    frequency_map = {
        "D": 252,
        "W": 365.25 / 7,
        "M": 12,
        "Q": 4,
    }

    if frequency not in frequency_map:
        supported = ", ".join(frequency_map.keys())
        raise ValueError(
            f"{PACKAGE_PREFIX} Unsupported frequency: {frequency}. Supported frequencies: {supported}."
        )

    return frequency_map[frequency]
    

def _compute_performance_metrics(input_data, annualized_factor, rf=0.0):
    """Compute standard performance metrics from price or NAV series.

    Args:
        input_data (pd.DataFrame): Price, NAV, or index-level data. Each column represents one asset or strategy.
        annualized_factor (int or float): Number of periods per year used for annualization.
        rf (float): Annual risk-free rate. Defaults to 0.0.
    
    Returns:
        pandas.DataFrame: Performance metrics with assets as rows and metrics as columns.
    
    Raises:
        ValueError: If input_data is empty or contains fewer than two rows.
    """
    if input_data.empty:
        raise ValueError(f"{PACKAGE_PREFIX} input_data is empty.")
    
    if input_data.shape[0] < 2:
        raise ValueError(f"{PACKAGE_PREFIX} input_data must contain at least two observations.")
    
    rf_per_period = (1 + rf) ** (1 / annualized_factor) - 1
    returns = input_data.pct_change().dropna(how="all")
    return_mean = returns.mean(axis=0)
    return_std = returns.std(axis=0)
    metrics = pd.DataFrame(index=input_data.columns)

    metrics["Total Return"] = input_data.iloc[-1] / input_data.iloc[0] - 1
    metrics["Geometric Return p.a."] = np.power(
        1 + metrics["Total Return"], 
        (annualized_factor / (input_data.shape[0] - 1)),
        ) - 1
    metrics["Average Return p.a."] = return_mean * annualized_factor
    metrics["Volatility p.a."] = return_std * np.sqrt(annualized_factor)
    metrics["Downside Volatility p.a."] = np.sqrt(
        (np.minimum(returns - rf_per_period, 0.0) ** 2).mean(axis=0)
        ) * np.sqrt(annualized_factor)
    metrics["Max Drawdown"] = (input_data.div(input_data.cummax()) - 1).min()
    
    metrics["Sharpe Ratio"] = (return_mean - rf_per_period) / return_std * np.sqrt(annualized_factor)
    metrics["Sortino Ratio"] = (return_mean - rf_per_period) / (np.sqrt((np.minimum(returns - rf_per_period, 0.0) ** 2).mean(axis=0))) * np.sqrt(annualized_factor)
    metrics["Calmar Ratio"] = - (metrics["Geometric Return p.a."] - rf) / metrics["Max Drawdown"]

    metrics["Skewness"] = returns.skew()
    metrics["Kurtosis"] = returns.kurt()
    return metrics

def _format_performance_metrics(metrics):
    """Format the performance metrics table for presentation.

    Args:
        metrics (pd.DataFrame): Raw performance metrics table.
    
    Returns:
        pd.DataFrame: Formatted performance metrics table.
    """

    return



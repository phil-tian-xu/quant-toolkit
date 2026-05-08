# quant-toolkit

`quant-toolkit` is a lightweight Python package for reusable quantitative finance utilities.

It is designed as a shared utility layer for quantitative research and engineering projects. Instead of rewriting common analytics in each repository, users can import standardized tools for performance analysis, risk statistics, trading calendars, and other reusable workflows.

This package is in early v1 development. The current focus is on performance metrics and exchange trading calendar utilities.

## Installation

Install directly from GitHub:

```bash
pip install git+https://github.com/phil-tian-xu/quant-toolkit.git
```

If you use SSH for GitHub:

```bash
pip install git+ssh://git@github.com/phil-tian-xu/quant-toolkit.git
```

For local development:

```bash
git clone git@github.com:phil-tian-xu/quant-toolkit.git
cd quant-toolkit
pip install -e .
```

## Main Features

### Performance Metrics

`quant-toolkit` provides a standard performance metrics function for price, NAV, or index-level time series.

| Metric | Description |
| --- | --- |
| Total Return | Cumulative return over the full input period |
| Geometric Return p.a. | Annualized compound return |
| Average Return p.a. | Annualized arithmetic average return |
| Volatility p.a. | Annualized return volatility |
| Downside Volatility p.a. | Annualized downside volatility relative to the risk-free rate |
| Max Drawdown | Largest peak-to-trough decline |
| Sharpe Ratio | Risk-adjusted return using total volatility |
| Sortino Ratio | Risk-adjusted return using downside volatility |
| Calmar Ratio | Annualized return relative to max drawdown |
| Skewness | Skewness of periodic returns |
| Kurtosis | Kurtosis of periodic returns |

Example:

```python
import pandas as pd

from quant_toolkit.performance_metrics import calculate_performance_metrics

data = pd.DataFrame(
    {
        "Strategy A": [100, 102, 101, 105, 108],
        "Strategy B": [100, 99, 101, 103, 104],
    },
    index=pd.to_datetime([
        "2024-01-02",
        "2024-01-03",
        "2024-01-04",
        "2024-01-05",
        "2024-01-08",
    ]),
)

metrics = calculate_performance_metrics(data)
print(metrics)
```

The function supports standard annualization modes:

```python
calculate_performance_metrics(data, frequency="D")
calculate_performance_metrics(data, frequency="W")
calculate_performance_metrics(data, frequency="M")
calculate_performance_metrics(data, frequency="Q")
```

It also supports custom annualization factors and exchange-calendar-based annualization:

```python
calculate_performance_metrics(data, annualized_factor=252)

calculate_performance_metrics(
    data,
    annualized_factor="actual",
    exchange="NYSE",
)
```

### Data Download - Trading Calendars

The package includes a small calendar utility built on `QuantLib`.

```python
from quant_toolkit.data_download import get_calendar

calendar = get_calendar(
    exchange="NYSE",
    start_date="2024-01-01",
    end_date="2024-01-10",
)
```

Supported output types:

```python
from datetime import date, datetime

get_calendar("NYSE", "2024-01-01", "2024-01-10", calendar_type=str)
get_calendar("NYSE", "2024-01-01", "2024-01-10", calendar_type=date)
get_calendar("NYSE", "2024-01-01", "2024-01-10", calendar_type=datetime)
```

Currently supported exchange aliases include:

| Country / Region | Exchange | Supported Codes |
| --- | --- | --- |
| United States | New York Stock Exchange | `NYSE`, `US` |
| Hong Kong | Hong Kong Exchange | `HK`, `HKEX` |
| United Kingdom | London Stock Exchange | `UK`, `LSE` |
| Japan | Tokyo Stock Exchange | `JP`, `TSE`, `JAPAN` |

## Development Schedule

Updated: 8 May 2026

### Near-Term Development
The near-term goal is to make the v1 utility layer more complete and reliable:
- strengthen input validation and edge-case handling
- improve formatted outputs for user-facing reports
- expand test coverage around performance and calendar utilities
- polish public APIs and documentation

### Long-Term Development
Longer term, `quant-toolkit` may expand into a broader collection of reusable quant utilities:

- data download
- risk analysis modules

## License

License information has not been finalized yet.

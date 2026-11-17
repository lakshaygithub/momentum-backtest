"""Download daily adjusted closing prices and turn them into month-end prices.

Adjusted close includes dividends, so returns computed from it are total returns.
Downloads are cached in data/ (not committed) so reruns use the same numbers.
"""

import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    "?period1=946684800&period2={end}&interval=1d&events=div%2Csplit"
)


def _download(symbol: str) -> pd.Series:
    request = urllib.request.Request(
        URL.format(symbol=symbol, end=int(time.time())),
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)["chart"]["result"][0]
    dates = pd.to_datetime(result["timestamp"], unit="s").normalize()
    closes = result["indicators"]["adjclose"][0]["adjclose"]
    return pd.Series(closes, index=dates, name=symbol).dropna()


def load_daily(symbols: list[str], refresh: bool = False) -> pd.DataFrame:
    """Daily adjusted closes, one column per symbol, only dates where all exist."""
    CACHE_DIR.mkdir(exist_ok=True)
    columns = []
    for symbol in symbols:
        path = CACHE_DIR / f"{symbol}.csv"
        if refresh or not path.exists():
            _download(symbol).rename_axis("date").to_csv(path)
        columns.append(pd.read_csv(path, index_col="date", parse_dates=True)[symbol])
    return pd.concat(columns, axis=1).dropna()


def to_monthly(daily: pd.DataFrame, end: str) -> pd.DataFrame:
    """Last price of each month, up to and including the month of `end`.

    `end` should be the last *complete* month, so a half-finished month
    never sneaks into the results.
    """
    monthly = daily.resample("ME").last()
    return monthly.loc[:end]

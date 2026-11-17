"""Performance numbers for a series of monthly returns."""

import math

import numpy as np
import pandas as pd

MONTHS_PER_YEAR = 12


def growth(returns: pd.Series) -> pd.Series:
    """Value of $1 invested at the start."""
    return (1 + returns).cumprod()


def drawdown(returns: pd.Series) -> pd.Series:
    """How far below its previous peak the portfolio is at each month (0 = at a peak)."""
    value = growth(returns)
    peak = np.maximum(value.cummax(), 1.0)  # the starting $1 counts as a peak
    return value / peak - 1


def sharpe(returns: pd.Series) -> float:
    """Annualised Sharpe ratio with a 0% risk-free rate (same for every strategy)."""
    std = returns.std(ddof=1)
    if std == 0 or math.isnan(std):
        return float("nan")
    return returns.mean() / std * math.sqrt(MONTHS_PER_YEAR)


def summarize(returns: pd.Series) -> dict[str, float]:
    years = len(returns) / MONTHS_PER_YEAR
    return {
        "cagr": growth(returns).iloc[-1] ** (1 / years) - 1,
        "volatility": returns.std(ddof=1) * math.sqrt(MONTHS_PER_YEAR),
        "sharpe": sharpe(returns),
        "max_drawdown": drawdown(returns).min(),
        "worst_month": returns.min(),
    }


def bootstrap_sharpe_difference(
    a: pd.Series, b: pd.Series, block: int = 12, samples: int = 5000, seed: int = 1
) -> dict[str, float]:
    """Is strategy a's Sharpe really higher than b's, or could it be luck?

    Resamples history in blocks of `block` months (blocks keep streaks and
    crashes together), using the same months for both series so they stay
    paired. Returns how often a beats b, and a 90% range for the difference.
    """
    paired = np.column_stack([a.to_numpy(), b.to_numpy()])
    n = len(paired)
    rng = np.random.default_rng(seed)
    differences = np.empty(samples)
    for i in range(samples):
        starts = rng.integers(0, n, size=math.ceil(n / block))
        index = (starts[:, None] + np.arange(block)).ravel()[:n] % n  # wraps around the end
        sample = paired[index]
        sharpe_a = sample[:, 0].mean() / sample[:, 0].std(ddof=1)
        sharpe_b = sample[:, 1].mean() / sample[:, 1].std(ddof=1)
        differences[i] = (sharpe_a - sharpe_b) * math.sqrt(MONTHS_PER_YEAR)
    return {
        "share_a_wins": float((differences > 0).mean()),
        "low_5pct": float(np.percentile(differences, 5)),
        "high_95pct": float(np.percentile(differences, 95)),
    }

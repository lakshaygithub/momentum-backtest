"""Walk-forward testing: pick the lookback using only the past, then trade the next year.

For each test year Y:
  1. score every candidate lookback on returns *before* year Y (Sharpe ratio)
  2. hold the best one's positions during year Y
Stitching the test years together gives an out-of-sample record: no month's
result was used to choose the settings that produced it.
"""

import pandas as pd

from .metrics import sharpe
from .strategy import holdings, momentum_weights, net_returns


def choose_lookback(train_returns: dict[int, pd.Series]) -> int:
    """Highest Sharpe on the training data. Ties go to the shorter lookback."""
    common = pd.concat(train_returns, axis=1).dropna()
    scores = {lookback: sharpe(common[lookback]) for lookback in sorted(train_returns)}
    return max(scores, key=lambda lookback: scores[lookback])


def walk_forward(
    prices: pd.DataFrame, lookbacks: list[int], first_test_year: int, cost_bps: float
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (monthly results for the test years, which lookback each year used)."""
    held = {lb: holdings(momentum_weights(prices, lb)) for lb in lookbacks}
    asset_returns = prices.pct_change()
    results = {lb: net_returns(asset_returns, held[lb], cost_bps)["net"] for lb in lookbacks}

    last_year = prices.index[-1].year
    stitched, choices = [], []
    for year in range(first_test_year, last_year + 1):
        train = {lb: r[r.index.year < year] for lb, r in results.items()}
        best = choose_lookback(train)
        stitched.append(held[best][held[best].index.year == year])
        choices.append({"year": year, "lookback": best, "train_months": len(pd.concat(train, axis=1).dropna())})

    # Costs are computed on the stitched holdings, so switching lookback is charged too.
    out_of_sample = net_returns(asset_returns, pd.concat(stitched), cost_bps)
    return out_of_sample, pd.DataFrame(choices).set_index("year")

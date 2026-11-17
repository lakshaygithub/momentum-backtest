"""Target weights and the backtest itself. Everything works on month-end prices.

Timing rule (the one that prevents look-ahead bias):
  weights[t] are decided at the close of month t using prices up to t only,
  and they earn the returns of month t + 1.
"""

import pandas as pd


def momentum_weights(prices: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Time-series momentum: hold an asset only while it has gone up.

    Each asset gets a fixed slot of 1/N of the portfolio. If the asset's return
    over the last `lookback` months is positive, the slot holds the asset;
    otherwise the slot sits in cash (earning 0%, which is conservative).
    """
    past_return = prices / prices.shift(lookback) - 1
    weights = (past_return > 0).astype(float) / prices.shape[1]
    return weights.where(past_return.notna())  # no decision until enough history


def equal_weights(prices: pd.DataFrame) -> pd.DataFrame:
    """Baseline: always hold every asset at 1/N, no timing."""
    return pd.DataFrame(1 / prices.shape[1], index=prices.index, columns=prices.columns)


def net_returns(asset_returns: pd.DataFrame, held: pd.DataFrame, cost_bps: float) -> pd.DataFrame:
    """Monthly portfolio returns after trading costs.

    held[t] is what the portfolio holds during month t. Turnover is how much of
    the portfolio changed hands going into month t (buying in at the start
    counts too). Cost = turnover x cost_bps.

    Simplification: within a month the weights are treated as fixed, and only
    changes in target weights are charged (not the small trades needed to undo
    price drift). This flatters the always-invested baseline slightly, not the
    strategy.
    """
    gross = (held * asset_returns.loc[held.index]).sum(axis=1)
    turnover = held.diff().abs().sum(axis=1)
    turnover.iloc[0] = held.iloc[0].abs().sum()
    cost = turnover * cost_bps / 10_000
    return pd.DataFrame({"gross": gross, "turnover": turnover, "cost": cost, "net": gross - cost})


def holdings(weights: pd.DataFrame) -> pd.DataFrame:
    """Shift decisions forward one month: decided at t, held during t + 1."""
    return weights.shift(1).dropna(how="any")


def run_backtest(prices: pd.DataFrame, weights: pd.DataFrame, cost_bps: float) -> pd.DataFrame:
    return net_returns(prices.pct_change(), holdings(weights), cost_bps)

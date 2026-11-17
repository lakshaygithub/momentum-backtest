import math

import numpy as np
import pandas as pd
import pytest

from backtest.metrics import bootstrap_sharpe_difference, drawdown, sharpe, summarize
from backtest.strategy import equal_weights, holdings, momentum_weights, run_backtest
from backtest.walkforward import walk_forward


def fake_prices(months: int = 120, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    index = pd.date_range("2000-01-31", periods=months, freq="ME")
    returns = rng.normal(0.005, 0.04, size=(months, 3))
    return pd.DataFrame(100 * np.cumprod(1 + returns, axis=0), index=index, columns=["A", "B", "C"])


# --- no look-ahead -------------------------------------------------------------

def test_weights_do_not_change_when_the_future_changes():
    prices = fake_prices()
    changed = prices.copy()
    changed.iloc[60:] *= 3  # rewrite everything from month 60 on
    original = momentum_weights(prices, 6).iloc[:60]
    after_change = momentum_weights(changed, 6).iloc[:60]
    pd.testing.assert_frame_equal(original, after_change)


def test_positions_are_held_the_month_after_they_are_decided():
    prices = fake_prices()
    weights = momentum_weights(prices, 3)
    held = holdings(weights)
    month = held.index[10]
    previous = weights.index[weights.index.get_loc(month) - 1]
    pd.testing.assert_series_equal(held.loc[month], weights.loc[previous], check_names=False)


def test_walk_forward_choice_ignores_the_test_year():
    prices = fake_prices(180)
    _, choices = walk_forward(prices, [1, 3, 6, 12], first_test_year=2008, cost_bps=0)
    cut = prices.loc[:"2010-12-31"]  # remove every price from 2011 onwards
    _, choices_cut = walk_forward(cut, [1, 3, 6, 12], first_test_year=2008, cost_bps=0)
    pd.testing.assert_series_equal(choices.loc[2008:2010, "lookback"], choices_cut["lookback"])


# --- strategy and costs ----------------------------------------------------------

def test_momentum_holds_only_assets_that_went_up():
    index = pd.date_range("2000-01-31", periods=4, freq="ME")
    prices = pd.DataFrame({"Up": [1, 2, 3, 4], "Down": [4, 3, 2, 1]}, index=index, dtype=float)
    weights = momentum_weights(prices, 1)
    assert weights.iloc[-1].to_dict() == {"Up": 0.5, "Down": 0.0}
    assert weights.iloc[0].isna().all()  # not enough history yet


def test_costs_equal_turnover_times_rate():
    prices = fake_prices()
    weights = momentum_weights(prices, 3)
    free = run_backtest(prices, weights, cost_bps=0)
    costly = run_backtest(prices, weights, cost_bps=25)
    assert (costly["net"] <= free["net"] + 1e-15).all()
    expected = free["net"] - free["turnover"] * 25 / 10_000
    pd.testing.assert_series_equal(costly["net"], expected, check_names=False)


def test_equal_weight_only_pays_to_buy_in():
    result = run_backtest(fake_prices(), equal_weights(fake_prices()), cost_bps=10)
    assert result["turnover"].iloc[0] == pytest.approx(1.0)
    assert (result["turnover"].iloc[1:] == 0).all()


def test_backtest_return_matches_hand_calculation():
    index = pd.date_range("2000-01-31", periods=3, freq="ME")
    prices = pd.DataFrame({"A": [100.0, 110.0, 99.0], "B": [100.0, 100.0, 120.0]}, index=index)
    result = run_backtest(prices, equal_weights(prices), cost_bps=0)
    assert result["net"].tolist() == pytest.approx([0.5 * 0.10 + 0.5 * 0.0, 0.5 * -0.10 + 0.5 * 0.20])


# --- metrics ----------------------------------------------------------------------

def test_metrics_on_a_steady_series():
    returns = pd.Series([0.01] * 24)
    m = summarize(returns)
    assert m["cagr"] == pytest.approx(1.01**12 - 1)
    assert m["max_drawdown"] == 0
    assert m["volatility"] == pytest.approx(0, abs=1e-12)


def test_drawdown_counts_a_loss_from_the_start():
    returns = pd.Series([-0.5, 1.0, -0.25])  # $1 -> 0.5 -> 1.0 -> 0.75
    assert drawdown(returns).tolist() == pytest.approx([-0.5, 0.0, -0.25])


def test_sharpe_is_annualised():
    returns = pd.Series([0.02, 0.0, 0.02, 0.0])
    assert sharpe(returns) == pytest.approx(0.01 / returns.std(ddof=1) * math.sqrt(12))


def test_bootstrap_is_reproducible_and_sensible():
    rng = np.random.default_rng(3)
    good = pd.Series(rng.normal(0.02, 0.03, 240))
    bad = pd.Series(rng.normal(-0.01, 0.03, 240))
    first = bootstrap_sharpe_difference(good, bad, samples=500, seed=7)
    assert first == bootstrap_sharpe_difference(good, bad, samples=500, seed=7)
    assert first["share_a_wins"] > 0.99
    assert first["low_5pct"] > 0

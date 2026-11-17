"""Run the full study and write results/summary.md plus charts.

    python -m backtest.run              # uses cached prices in data/
    python -m backtest.run --refresh    # downloads fresh prices first
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from .data import load_daily, to_monthly  # noqa: E402
from .metrics import bootstrap_sharpe_difference, drawdown, growth, sharpe, summarize  # noqa: E402
from .strategy import equal_weights, holdings, momentum_weights, net_returns  # noqa: E402
from .walkforward import walk_forward  # noqa: E402

SYMBOLS = ["SPY", "EFA", "IEF", "GLD"]  # US stocks, international stocks, US bonds, gold
LOOKBACKS = [1, 3, 6, 9, 12]
RESULTS = Path(__file__).resolve().parent.parent / "results"


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def table(rows: dict[str, dict[str, float]]) -> str:
    lines = [
        "| Strategy | CAGR | Volatility | Sharpe | Max drawdown | Worst month |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, m in rows.items():
        lines.append(
            f"| {name} | {pct(m['cagr'])} | {pct(m['volatility'])} | {m['sharpe']:.2f} | "
            f"{pct(m['max_drawdown'])} | {pct(m['worst_month'])} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--end", default="2026-10-31", help="last complete month to include")
    parser.add_argument("--first-test-year", type=int, default=2010)
    parser.add_argument("--cost-bps", type=float, default=10)
    args = parser.parse_args()

    prices = to_monthly(load_daily(SYMBOLS, refresh=args.refresh), args.end)
    asset_returns = prices.pct_change()

    wf, choices = walk_forward(prices, LOOKBACKS, args.first_test_year, args.cost_bps)
    period = wf.index

    def on_period(weights: pd.DataFrame) -> pd.DataFrame:
        return net_returns(asset_returns, holdings(weights).loc[period], args.cost_bps)

    fixed12 = on_period(momentum_weights(prices, 12))
    equal = on_period(equal_weights(prices))
    spy_only = pd.DataFrame(0.0, index=prices.index, columns=prices.columns).assign(SPY=1.0)
    spy = on_period(spy_only)
    # Fairness check: momentum spends time in cash, so it is less risky by construction.
    # Scale equal weight down to the same volatility (rest in cash) and compare again.
    # Uses volatilities from the test period, so it is a comparison, not a tradable strategy.
    scale = wf["net"].std() / equal["net"].std()
    equal_scaled = on_period(equal_weights(prices) * scale)

    # Cheating on purpose: the lookback that looks best on the test years themselves.
    hindsight = {lb: on_period(momentum_weights(prices, lb))["net"] for lb in LOOKBACKS}
    hindsight_best = max(hindsight, key=lambda lb: sharpe(hindsight[lb]))

    curves = {
        "Momentum, walk-forward (honest)": wf["net"],
        "Momentum, fixed 12-month": fixed12["net"],
        f"Momentum, best lookback in hindsight ({hindsight_best}m)": hindsight[hindsight_best],
        "Equal weight, same 4 ETFs": equal["net"],
        f"Equal weight at the same risk ({scale:.0%} invested)": equal_scaled["net"],
        "SPY buy and hold": spy["net"],
    }
    rows = {name: summarize(r) for name, r in curves.items()}

    cost_rows = {}
    for bps in [0, 10, 25, 50]:
        r, _ = walk_forward(prices, LOOKBACKS, args.first_test_year, bps)
        cost_rows[bps] = summarize(r["net"])

    vs_equal = bootstrap_sharpe_difference(wf["net"], equal["net"])
    vs_spy = bootstrap_sharpe_difference(wf["net"], spy["net"])
    trades_per_year = wf["turnover"].sum() / (len(wf) / 12)

    first, last = period[0].strftime("%b %Y"), period[-1].strftime("%b %Y")
    md = [
        "# Results",
        "",
        f"Test period: {first} to {last} ({len(period)} months), monthly rebalancing, "
        f"{args.cost_bps:g} bps cost per unit of turnover. Total returns (dividends included).",
        "",
        table(rows),
        "",
        f"Walk-forward turnover: {trades_per_year:.2f}x the portfolio per year.",
        "",
        "## Lookback chosen each year (walk-forward)",
        "",
        "| Year | Lookback (months) | Training months |",
        "| --- | ---: | ---: |",
        *[f"| {y} | {c.lookback} | {c.train_months} |" for y, c in choices.iterrows()],
        "",
        "## Sensitivity to trading costs (walk-forward)",
        "",
        "| Cost (bps) | CAGR | Sharpe | Max drawdown |",
        "| ---: | ---: | ---: | ---: |",
        *[
            f"| {bps} | {pct(m['cagr'])} | {m['sharpe']:.2f} | {pct(m['max_drawdown'])} |"
            for bps, m in cost_rows.items()
        ],
        "",
        "## Is the Sharpe difference real? (block bootstrap, 12-month blocks, 5,000 samples)",
        "",
        "| Walk-forward vs | Share of samples it wins | 90% range of Sharpe difference |",
        "| --- | ---: | ---: |",
        f"| Equal weight | {pct(vs_equal['share_a_wins'])} | {vs_equal['low_5pct']:+.2f} to {vs_equal['high_95pct']:+.2f} |",
        f"| SPY | {pct(vs_spy['share_a_wins'])} | {vs_spy['low_5pct']:+.2f} to {vs_spy['high_95pct']:+.2f} |",
        "",
    ]
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "summary.md").write_text("\n".join(md))
    print("\n".join(md))

    fig, (top, bottom) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, height_ratios=[2, 1])
    for name, r in curves.items():
        if "hindsight" in name:
            continue
        top.plot(growth(r), label=name)
        bottom.plot(drawdown(r) * 100, label=name)
    top.set_yscale("log")
    top.set_ylabel("Growth of $1 (log scale)")
    top.legend(fontsize=8)
    top.set_title(f"Out-of-sample test, {first} to {last}, after {args.cost_bps:g} bps costs")
    bottom.set_ylabel("Drawdown (%)")
    fig.tight_layout()
    fig.savefig(RESULTS / "growth_and_drawdown.png", dpi=120)


if __name__ == "__main__":
    main()
